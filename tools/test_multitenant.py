#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多租户隔离性测试（服务层，真跑一个临时 SQLite 库）。

验的是这条产品承诺：「只有本人能看到自己的卡」。
所以每条"看不到"的断言，都配一条"它其实存在"的反证 ——
否则测试可能只是没造出数据，而不是隔离起了作用。

    python tools/test_multitenant.py
"""
import os
import sys
import tempfile
from pathlib import Path

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 必须在 import backend.* 之前设好：config 在导入时就把 DB_PATH 定下来了
_DB = Path(tempfile.mkdtemp(prefix="strag-test-")) / "test.db"
os.environ["DB_PATH"] = str(_DB)

from backend.models.database import SessionLocal, init_db          # noqa: E402
from backend.models.character_card import CharacterCard            # noqa: E402
from backend.models.world_book import WorldBook                    # noqa: E402
from backend.schemas.character_card import (                       # noqa: E402
    CharacterCardCreate, CharacterCardUpdate,
)
from backend.schemas.world_book import WorldBookCreate, WorldBookUpdate  # noqa: E402
from backend.services import auth_service, card_service, worldbook_service  # noqa: E402

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def main() -> int:
    init_db()
    db = SessionLocal()
    print(f"临时库：{_DB}\n")

    print("① 账号：注册 / 首个用户是管理员 / 密码哈希")
    alice = auth_service.register(db, "alice", "pw123456")
    bob = auth_service.register(db, "bob", "pw123456")
    check(alice.is_admin and not bob.is_admin, "第一个注册者是管理员，第二个不是")
    check(auth_service.verify_password("pw123456", alice.password_hash),
          "正确密码能通过校验")
    check(not auth_service.verify_password("wrong-pw", alice.password_hash),
          "错误密码通不过")
    check("pw123456" not in alice.password_hash, "库里存的是哈希，不是明文")
    try:
        auth_service.register(db, "ab", "pw123456")
        check(False, "太短的用户名应当被拒")
    except auth_service.AuthError:
        check(True, "太短的用户名被拒")
    try:
        auth_service.register(db, "alice", "pw123456")
        check(False, "重名应当被拒")
    except auth_service.AuthError:
        check(True, "重名被拒")

    print("② 会话：登录发令牌、无效令牌拿不到用户、退出后失效")
    user, token, _exp = auth_service.login(db, "alice", "pw123456")
    check(auth_service.resolve_token(db, token).id == alice.id, "新令牌能解析出本人")
    check(auth_service.resolve_token(db, "not-a-real-token") is None, "伪造令牌解析为 None")
    auth_service.logout(db, token)
    check(auth_service.resolve_token(db, token) is None, "退出后同一个令牌失效")

    print("③ 角色卡隔离（核心承诺）")
    card = card_service.create_card(db, CharacterCardCreate(name="爱丽丝的卡"), alice.id)
    check(card_service.get_card(db, card.id, alice.id) is not None, "本人能读到自己的卡")
    check(card_service.get_card(db, card.id, bob.id) is None, "别人读同一张卡拿到 None")
    # 反证：这张卡确实在库里 —— 否则上一条"拿到 None"可能只是卡没建成
    raw = db.query(CharacterCard).filter(CharacterCard.id == card.id).first()
    check(raw is not None, "反证：这张卡确实存在于库里（隔离是靠条件过滤，不是没数据）")
    check(card_service.list_cards(db, alice.id).total == 1, "本人的列表里有 1 张")
    check(card_service.list_cards(db, bob.id).total == 0, "别人的列表里 0 张")
    check(card_service.update_card(db, card.id, CharacterCardUpdate(name="偷改"), bob.id) is None,
          "别人改不动这张卡")
    check(db.query(CharacterCard).filter(CharacterCard.id == card.id).first().name == "爱丽丝的卡",
          "反证：名字没被改掉")
    check(card_service.delete_card(db, card.id, bob.id) is False, "别人删不掉这张卡")
    check(db.query(CharacterCard).filter(CharacterCard.id == card.id).first() is not None,
          "反证：卡还在")

    print("④ 世界书隔离")
    wb = worldbook_service.create_worldbook(
        db, WorldBookCreate(name="爱丽丝的世界书", description="d", entries=[]), alice.id)
    check(worldbook_service.get_worldbook(db, wb.id, alice.id) is not None, "本人能读到自己的世界书")
    check(worldbook_service.get_worldbook(db, wb.id, bob.id) is None, "别人读不到")
    check(db.query(WorldBook).filter(WorldBook.id == wb.id).first() is not None,
          "反证：世界书确实在库里")
    check(worldbook_service.list_worldbooks(db, bob.id).total == 0, "别人的列表里 0 本")
    check(worldbook_service.delete_worldbook(db, wb.id, bob.id) is False, "别人删不掉")

    print("⑤ 搜索/筛选也带归属（否则能靠搜索侧信道读出别人的内容）")
    card_service.create_card(db, CharacterCardCreate(name="爱丽丝的隐藏卡"), alice.id)
    check(card_service.list_cards(db, bob.id, search="爱丽丝").total == 0,
          "别人搜关键词搜不到我的卡")
    check(card_service.list_cards(db, alice.id, search="爱丽丝").total >= 1,
          "反证：本人搜得到")

    print("⑥ 改密码会踢掉所有旧会话")
    _u, tok2, _e = auth_service.login(db, "alice", "pw123456")
    auth_service.change_password(db, alice, "pw123456", "newpw1234")
    check(auth_service.resolve_token(db, tok2) is None, "改密码后旧令牌失效")
    _u, tok3, _e = auth_service.login(db, "alice", "newpw1234")
    check(auth_service.resolve_token(db, tok3) is not None, "新密码能登录")

    db.close()
    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：")
        for f in fails:
            print("   ·", f)
        return 1
    print("✅ 多租户隔离测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
