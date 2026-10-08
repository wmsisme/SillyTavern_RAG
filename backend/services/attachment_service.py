"""反馈附件：用户在反馈时投递的文件（技术档案之类）。

达铭 2026-10-08 的原话是「**服务器是我的电脑，放不了那么多东西**」——
所以这个模块一半在存文件，一半在**守闸门**：

    ① 单文件大小        ATTACH_MAX_FILE_MB        默认 20
    ② 每次上传个数      ATTACH_MAX_PER_SUBMIT     默认 3
    ③ 每 IP 每天        ATTACH_MAX_PER_IP_PER_DAY 默认 5     ← 他点名要的
    ④ 每用户累计        ATTACH_MAX_PER_USER       默认 50
    ⑤ **全局总量**      ATTACH_MAX_TOTAL_MB       默认 1024  ← 我加的兜底：
       光限"每 IP 数量"挡不住磁盘被慢慢填满（很多 IP 各传几个就够了）

任何一道超了都**直接拒**，并把原因**原样用人话告诉用户**（别让人猜自己哪里不对）。

安全约定（与卡图同源，都是"用户传上来的东西"）：
  · 存名用 **UUID**，**不用原文件名** —— 原名能构造路径穿越（`../../.env` 那类）
  · 文件落在 `backend/static/attachments/`，而 `/static` **没有挂成静态目录**
    （见 main.py 的注释），所以只能走鉴权端点取
  · 类型**白名单**：md / txt / pdf / docx / json / csv —— 不收可执行文件、不收压缩包
  · 下载只放给**本人与管理员**；别人来取一律 404（不泄露"这条存在"）
"""
import os
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import STATIC_DIR
from backend.models.admin import FeedbackAttachment
from backend.models.user import User

ATTACH_DIR = STATIC_DIR / "attachments"

ALLOWED_EXT = {".md", ".txt", ".pdf", ".docx", ".json", ".csv"}

# 扩展名 -> 给浏览器/前端看的 MIME（下载时用，避免"一律 octet-stream"）
_CT = {
    ".md": "text/markdown", ".txt": "text/plain", ".json": "application/json",
    ".csv": "text/csv", ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _cfg() -> dict:
    return {
        "max_file": int(os.environ.get("ATTACH_MAX_FILE_MB", "20") or 20) * 1024 * 1024,
        "max_per_submit": int(os.environ.get("ATTACH_MAX_PER_SUBMIT", "3") or 3),
        "max_per_ip_day": int(os.environ.get("ATTACH_MAX_PER_IP_PER_DAY", "5") or 5),
        "max_per_user": int(os.environ.get("ATTACH_MAX_PER_USER", "50") or 50),
        "max_total": int(os.environ.get("ATTACH_MAX_TOTAL_MB", "1024") or 1024) * 1024 * 1024,
    }


def _mb(n: int) -> float:
    return n / 1048576


def ext_of(name: str) -> str:
    """取小写扩展名。用 os.path 的 splitext 而不是字符串切分 —— 名字里可能有点。"""
    return Path(name or "").suffix.lower()


def total_bytes(db: Session) -> int:
    from sqlalchemy import func
    return int(db.query(func.coalesce(func.sum(FeedbackAttachment.size), 0)).scalar() or 0)


def total_count(db: Session) -> int:
    return int(db.query(FeedbackAttachment).count())


def usage(db: Session) -> dict:
    """给后台显示用：用了多少、还剩多少、按来源分。"""
    c = _cfg()
    used = total_bytes(db)
    return {
        "count": total_count(db),
        "used_bytes": used,
        "used_mb": round(_mb(used), 2),
        "limit_mb": int(c["max_total"] / 1048576),
        "percent": round(used * 100.0 / c["max_total"], 2) if c["max_total"] else 0,
        "file_limit_mb": int(c["max_file"] / 1048576),
        "per_ip_day": c["max_per_ip_day"],
        "per_user": c["max_per_user"],
    }


def check_quota(db: Session, user: User, ip: str,
                incoming_bytes: int = 0, incoming_count: int = 1) -> str:
    """五道闸门。**返回 None = 放行**；返回字符串 = 拒绝原因（原样给用户看）。

    先查最"贵"的全局总量：它一旦满了，其余几道都不用算了。
    """
    from datetime import date, datetime

    c = _cfg()

    used = total_bytes(db)
    if used + incoming_bytes > c["max_total"]:
        return (f"站长的附件空间满了（已用 {_mb(used):.0f}MB，上限 {_mb(c['max_total']):.0f}MB），"
                "暂时收不了新文件 —— 你可以在反馈里说明情况，站长清理后就能再传。")
    if incoming_bytes > c["max_file"]:
        return f"单个文件不能超过 {_mb(c['max_file']):.0f}MB（这个 {_mb(incoming_bytes):.1f}MB）。"
    if incoming_count > c["max_per_submit"]:
        return f"一次最多传 {c['max_per_submit']} 个文件（这次 {incoming_count} 个）。"

    n_user = db.query(FeedbackAttachment).filter(
        FeedbackAttachment.user_id == user.id).count()
    if n_user + incoming_count > c["max_per_user"]:
        return (f"你累计上传的文件数已达上限（{c['max_per_user']} 个）—— "
                "先跟站长说一声，请他处理一下旧文件。")

    today = datetime.now().date()
    n_ip = db.query(FeedbackAttachment).filter(
        FeedbackAttachment.ip == ip,
        FeedbackAttachment.created_at >= datetime.combine(today, datetime.min.time()),
    ).count()
    if n_ip + incoming_count > c["max_per_ip_day"]:
        return (f"这个网络今天已经传了 {n_ip} 个文件（每天上限 {c['max_per_ip_day']} 个）—— "
                "明天再来，或者让站长先把今天的看完。")

    # 保留 date 的引用，避免 linters 抱怨未使用（这行无害）
    _ = date
    return None


def save(db: Session, user: User, ip: str, filename: str, content: bytes,
         source: str = "feedback", ref_id: int = None) -> FeedbackAttachment:
    """把已经读进内存的文件落盘 + 记账。**调用前请先 check_quota()**。

    为什么把"读文件"留在调用方（api 层）：项目里已有 `_read_upload()`
    那个"读上限+1 字节"的写法（见 api/tools.py），复用它比在这里再造一套好。
    """
    ext = ext_of(filename)
    stored = f"{uuid.uuid4().hex}{ext}"
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    (ATTACH_DIR / stored).write_bytes(content)

    row = FeedbackAttachment(
        ip=ip[:64],
        user_id=getattr(user, "id", None),
        username=getattr(user, "username", "") or "",
        source=source,
        ref_id=ref_id,
        orig_name=(filename or "")[:255],
        stored_name=stored,
        size=len(content),
        content_type=_CT.get(ext, "application/octet-stream"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def path_of(row: FeedbackAttachment) -> Path:
    """物理路径。

    ⚠️ 只用库里的 `stored_name` 拼，**绝不碰 orig_name** —— 那是用户可控的字符串，
    拿它拼路径就是路径穿越。
    """
    return ATTACH_DIR / Path(row.stored_name).name


def delete(db: Session, row: FeedbackAttachment) -> bool:
    """删记录 + 删文件。文件删不掉也把记录删掉（否则会留下永远点不开的条目）。"""
    try:
        p = path_of(row)
        if p.is_file():
            p.unlink()
    except OSError:
        pass            # 磁盘上的残留不该阻止记账清理
    db.delete(row)
    db.commit()
    return True


def list_for(db: Session, source: str, ref_id: int) -> list:
    """取某个反馈下面挂的附件（后台与前端都用它）。"""
    return (db.query(FeedbackAttachment)
            .filter(FeedbackAttachment.source == source, FeedbackAttachment.ref_id == ref_id)
            .order_by(FeedbackAttachment.id)
            .all())


def briefs_for(db: Session, source: str, ref_id: int) -> list:
    """给后台列表用的精简信息（**不含磁盘存名** —— 列表页不需要知道那个）。

    返回 dict 而不是 ORM 对象：pydantic 的 `AttachmentBrief` 直接就能吃。
    """
    return [{"id": a.id, "orig_name": a.orig_name or "", "size": a.size or 0}
            for a in list_for(db, source, ref_id)]


def bind(db: Session, user, ids: list, source: str, ref_id: int) -> int:
    """把一批「刚上传、还没绑定」的附件绑到某条反馈上。返回实际绑定条数。

    只绑**自己的**、且 `ref_id` 还是空的那些：
      · 别人的附件 —— 凭什么绑到我的反馈上
      · 已经绑过的 —— 一条附件只属于一条反馈（否则后台会出现"同一份文件挂在两处"）

    `user` 为 None（匿名评价）时直接返回 0：**匿名不能带附件**（上传就要求登录）。
    """
    if user is None or not ids:
        return 0
    n = 0
    for aid in list(ids)[:10]:          # 上限保护：没人会一次绑几十个
        row = db.get(FeedbackAttachment, aid)
        if row is None or row.ref_id is not None or row.user_id != user.id:
            continue
        row.ref_id = ref_id
        row.source = source
        n += 1
    if n:
        db.commit()
    return n
