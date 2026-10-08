"""反馈附件：上传 / 下载 / 删除。

与卡图的分工：卡图是**用户自己的资产**，附件是**投递给站长的**（他要用它改知识库）。
所以权限规则是：**本人 ＋ 管理员**能看，别人一律 **404**。

⚠️ 下载**不走静态目录**：`/static` 没有挂成静态（见 main.py 的注释），
否则「只有本人和站长能看」就是一句空话。

上传是**两段式**（前端就这么写）：先 POST 到这里拿到 id，再在提交反馈时带上
`attachment_ids` 把附件绑到那条反馈上。这样反馈接口只多一个字段，
不用把两个接口都改成 multipart。

闸门全在 `services/attachment_service.py`（单文件/每次/每 IP 每天/每用户/全局总量）。
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.api.deps import current_user, current_user_optional
from backend.api.ratelimit import client_ip
from backend.models.admin import FeedbackAttachment
from backend.models.database import get_db
from backend.models.user import User
from backend.services import attachment_service

log = logging.getLogger("backend.attachment")
router = APIRouter()

# 硬上限：即便环境变量被配大了，也不允许一次传几十个进来（内存里会同时躺着它们）
MAX_FILES_HARD = 5


def _read_upload(file: UploadFile, limit: int) -> bytes:
    """读「上限 + 1」字节再判断 —— 项目里已有的写法（见 api/tools.py）。

    为什么不直接 `read()`：那样等于先把整个文件收进内存，再决定要不要拒。
    """
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"单个文件不能超过 {limit // 1048576}MB —— 这个更大，换个小的或者压缩一下内容。")
    return data


def _visible_to(row: FeedbackAttachment, user) -> bool:
    """本人或管理员可见。**注意返回 404 而不是 403**（403 会泄露"这条存在"）。"""
    if user is None:
        return False
    if getattr(user, "is_admin", False):
        return True
    return row.user_id is not None and row.user_id == user.id


@router.post("/attachments", status_code=201)
def upload_attachments(files: list[UploadFile] = File(...),
                       request: Request = None,
                       db: Session = Depends(get_db),
                       user: User = Depends(current_user)):
    """上传（**必须登录** —— 匿名上传等于任何人可往站长磁盘写文件）。

    顺序是刻意的：先卡个数与扩展名（不用读内容），再读，最后查配额。
    """
    cfg = attachment_service._cfg()

    if not files:
        raise HTTPException(status_code=400, detail="没有选文件。")
    if len(files) > MAX_FILES_HARD:
        raise HTTPException(status_code=400, detail=f"一次最多传 {MAX_FILES_HARD} 个文件。")
    if len(files) > cfg["max_per_submit"]:
        raise HTTPException(status_code=400,
                            detail=f"一次最多传 {cfg['max_per_submit']} 个文件 —— 分几次传吧。")

    # 扩展名先查：不读内容就能拒掉不该收的东西
    for f in files:
        ext = attachment_service.ext_of(f.filename)
        if ext not in attachment_service.ALLOWED_EXT:
            allowed = "、".join(sorted(e.lstrip(".") for e in attachment_service.ALLOWED_EXT))
            raise HTTPException(
                status_code=400,
                detail=f"不支持这种文件（{ext or '没有扩展名'}）。只收：{allowed}。")

    contents = [(f.filename, _read_upload(f, cfg["max_file"])) for f in files]
    total = sum(len(d) for _, d in contents)

    ip = client_ip(request)
    reason = attachment_service.check_quota(db, user, ip, incoming_bytes=total,
                                            incoming_count=len(contents))
    if reason:
        raise HTTPException(status_code=400, detail=reason)

    saved = [attachment_service.save(db, user, ip, name, data) for name, data in contents]
    log.info("附件上传：%d 个 / %.1fMB / ip=%s / user=%s",
             len(saved), total / 1048576, ip, getattr(user, "username", "?"))
    return {"items": [{"id": r.id, "orig_name": r.orig_name, "size": r.size} for r in saved]}


@router.get("/attachments/{aid}")
def download_attachment(aid: int, request: Request = None,
                        db: Session = Depends(get_db),
                        user: User = Depends(current_user_optional)):
    row = db.get(FeedbackAttachment, aid)
    if row is None or not _visible_to(row, user):
        raise HTTPException(status_code=404, detail="附件不存在")
    path = attachment_service.path_of(row)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="附件不存在")
    return FileResponse(path, media_type=row.content_type or "application/octet-stream",
                        filename=row.orig_name or path.name)


@router.delete("/attachments/{aid}")
def delete_attachment(aid: int, request: Request = None,
                      db: Session = Depends(get_db),
                      user: User = Depends(current_user)):
    """删除。

    ⚠️ **本人只能删"还没绑到反馈上的"**：一旦跟着反馈提交了，那就是**投递给站长的材料**了 ——
    让上传者单方面撤回，站长那边就会看到一条"有附件但点不开"的记录。
    真要撤回，让他再发一条反馈说明（站长能删）。
    """
    row = db.get(FeedbackAttachment, aid)
    if row is None or not _visible_to(row, user):
        raise HTTPException(status_code=404, detail="附件不存在")
    if not getattr(user, "is_admin", False) and row.ref_id is not None:
        raise HTTPException(status_code=400,
                            detail="这份文件已经跟着反馈提交了，撤不回来 —— 可以再发一条反馈说明一下。")
    attachment_service.delete(db, row)
    return {"ok": True}
