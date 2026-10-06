"""账号与会话。

密码用标准库的 pbkdf2_hmac（不引 passlib），落库格式自带参数，升级轮数不用洗库：
    pbkdf2_sha256$<rounds>$<salt_hex>$<hash_hex>
"""
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from backend.models.user import User, SessionToken

PBKDF2_ROUNDS = 260_000
TOKEN_TTL_DAYS = 30
COOKIE_NAME = "strag_session"

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD_LEN = 6


class AuthError(Exception):
    """认证/注册失败，message 直接可以给用户看。"""


def hash_password(password: str, rounds: int = PBKDF2_ROUNDS) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), rounds)
    return f"pbkdf2_sha256${rounds}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds_s, salt, want = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), int(rounds_s))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), want)


def _validate(username: str, password: str) -> None:
    if not USERNAME_RE.match(username or ""):
        raise AuthError("用户名只能是 3-32 位的字母、数字、下划线、点或短横线")
    if len(password or "") < MIN_PASSWORD_LEN:
        raise AuthError(f"密码至少 {MIN_PASSWORD_LEN} 位")


def register(db: Session, username: str, password: str,
             invite_code: str = "", expect_invite: str = "") -> User:
    _validate(username, password)
    if expect_invite and invite_code.strip() != expect_invite:
        raise AuthError("邀请码不对")
    if db.query(User).filter(User.username == username).first():
        raise AuthError("这个用户名已经被注册了")

    # 首个注册者 = 管理员（本地第一次用、或公网第一个注册的人）
    is_first = db.query(User).count() == 0
    user = User(username=username, password_hash=hash_password(password), is_admin=is_first)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, username: str, password: str) -> Tuple[User, str, datetime]:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码不对")
    if not user.is_active:
        raise AuthError("这个账号已被停用")

    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(days=TOKEN_TTL_DAYS)
    db.add(SessionToken(token=token, user_id=user.id, expires_at=expires))
    db.commit()
    return user, token, expires


def resolve_token(db: Session, token: Optional[str]) -> Optional[User]:
    """令牌 → 用户；过期或无效一律返回 None（过期行顺手删掉）。"""
    if not token:
        return None
    row = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.now():
        db.delete(row)
        db.commit()
        return None
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        return None
    return user


def logout(db: Session, token: Optional[str]) -> None:
    if not token:
        return
    row = db.query(SessionToken).filter(SessionToken.token == token).first()
    if row:
        db.delete(row)
        db.commit()


def change_password(db: Session, user: User, old: str, new: str) -> None:
    """改密码并踢掉所有旧会话（别人拿到旧令牌也没用了）。"""
    if not verify_password(old, user.password_hash):
        raise AuthError("原密码不对")
    if len(new or "") < MIN_PASSWORD_LEN:
        raise AuthError(f"新密码至少 {MIN_PASSWORD_LEN} 位")
    user.password_hash = hash_password(new)
    db.query(SessionToken).filter(SessionToken.user_id == user.id).delete()
    db.commit()


def cookie_secure() -> bool:
    """HTTPS 部署时置 COOKIE_SECURE=1；本地 http 下必须 False，否则浏览器不存 Cookie。"""
    return os.environ.get("COOKIE_SECURE", "0") not in ("0", "", "false", "False")
