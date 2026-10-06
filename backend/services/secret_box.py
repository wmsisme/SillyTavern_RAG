"""对称加密用户存在账号里的 LLM Key（落库前加密、读出时解密）。

**诚实说明这层加密的边界**：
    服务器必须能解出明文才能替用户调平台，所以它防的是「数据库文件被拖走 / 被备份泄露」，
    **不是**「服务器被攻破」。配套的硬约束是：
      · Key 永不回传前端 —— 接口只回 masked 形态（前 6 位 + 后 4 位）；
      · 不写日志、不进异常信息；
      · 密钥来自环境变量 SECRET_KEY；没配就在 backend/.secret_key 生成并持久化
        （.gitignore 已拦），保证重启后还解得开；
      · SECRET_KEY 丢了 = 已存的 Key 全部解不开 —— 那时当成"没配"让用户重填，不要崩。
"""
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from backend.config import BACKEND_DIR

_ENV_VAR = "SECRET_KEY"
_KEY_FILE = BACKEND_DIR / ".secret_key"
_fernet = None


def _load_key() -> bytes:
    env = os.environ.get(_ENV_VAR, "").strip()
    if env:
        return env.encode("ascii")
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text(encoding="ascii").strip().encode("ascii")
    key = Fernet.generate_key()
    _KEY_FILE.write_text(key.decode("ascii"), encoding="ascii")
    try:
        os.chmod(_KEY_FILE, 0o600)
    except OSError:
        pass
    print(f"[secret_box] 已生成密钥文件 {_KEY_FILE}"
          f"（勿提交；公网部署建议改用环境变量 {_ENV_VAR}，并单独备份）")
    return key


def _box() -> Fernet:
    global _fernet
    if _fernet is None:
        try:
            _fernet = Fernet(_load_key())
        except Exception as e:      # 密钥格式不对 → 明确报出来，别静默用明文
            raise RuntimeError(f"{_ENV_VAR} 不是合法的 Fernet 密钥（32 字节 urlsafe base64）: {e}") from e
    return _fernet


def encrypt(plain: str) -> str:
    return _box().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str | None:
    """解不开返回 None（例如换了 SECRET_KEY）—— 调用方按「没配 Key」处理。"""
    if not token:
        return None
    try:
        return _box().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None
