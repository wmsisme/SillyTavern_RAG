"""前端错误上报（POST /api/errors）。

**为什么需要它**：前端崩了，以前只有两条路能知道 —— 用户主动来反馈，或者压根不知道。
这条接口把「浏览器里的那声闷响」变成服务端能查的记录，是「让线上不再瞎」的前端那一半。

**免登录**：未登录用户同样会遇到前端崩，而且他们最没渠道反馈。
正因为开放，这里做三件事防滥用：
  ① **字段全部限长**（pydantic max_length，超了 422 直接不进库）
  ② **走限流**（见 ratelimit.HEAVY_PREFIXES）
  ③ 前端侧还有去重与每会话上限（见 frontend/src/services/errorReporter.ts）

**刻意不收什么**：请求体里根本没有「用户输入内容」这类字段 ——
所以就算前端想传也传不进来。上报的全是浏览器自己产生的技术信息。

**写日志也写库**：日志负责「实时看得见」（配合今天加的慢请求告警一起看），
库负责「事后查得到」（日志会轮转，表不会）。
"""
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.deps import current_user_optional
from backend.api.ratelimit import client_ip
from backend.models.admin import ClientError
from backend.models.database import get_db

log = logging.getLogger("backend.client_error")
router = APIRouter()


class ClientErrorIn(BaseModel):
    kind: str = Field("error", max_length=24)          # error / unhandledrejection
    message: str = Field("", max_length=2000)
    stack: str = Field("", max_length=8000)
    page: str = Field("", max_length=255)              # 出错时所在的前端路由
    source: str = Field("", max_length=255)            # 报错脚本的 URL
    line: int = Field(0, ge=0, le=10_000_000)
    col: int = Field(0, ge=0, le=10_000_000)


@router.post("/errors", status_code=204)
def report_error(payload: ClientErrorIn, request: Request,
                 db: Session = Depends(get_db),
                 user=Depends(current_user_optional)):
    # 日志先写：这样错误是"实时看得见"的（翻日志不用等谁去查数据库）
    log.warning("前端错误 [%s] %s | page=%s | %s:%s",
                payload.kind, payload.message[:300], payload.page,
                payload.source[:120], payload.line)

    row = ClientError(
        ip=client_ip(request)[:64],
        user_id=getattr(user, "id", None),
        username=getattr(user, "username", "") or "",
        kind=payload.kind,
        message=payload.message,
        stack=payload.stack,
        page=payload.page,
        source=payload.source,
        line=payload.line,
        col=payload.col,
        user_agent=(request.headers.get("user-agent", "") or "")[:255],
    )
    db.add(row)
    try:
        db.commit()
    except Exception:           # noqa: BLE001
        # 落库失败**绝不能变成 500**：前端收到 5xx 会以为上报接口本身坏了，
        # 而它在崩溃路径上，没空处理这个 —— 静默吞掉，日志那头已经有线索了。
        db.rollback()
    return None
