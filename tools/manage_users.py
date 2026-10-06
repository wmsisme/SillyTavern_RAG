#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""账号管理 CLI（本机运维用）。

登录密码是 pbkdf2 哈希存的，**找不回来，只能重置** —— 忘了密码就用这个。

    python tools/manage_users.py --list
    python tools/manage_users.py --reset-password 111              # 交互式输入新密码
    python tools/manage_users.py --reset-password 111 --password 新密码
    python tools/manage_users.py --make-admin 111
    python tools/manage_users.py --deactivate 456
"""
import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.models.database import SessionLocal, init_db      # noqa: E402
from backend.models.user import User, SessionToken             # noqa: E402
from backend.services import auth_service                      # noqa: E402


def _find(db, who: str) -> User:
    """按用户名或 id 找人。"""
    user = db.query(User).filter(User.username == who).first()
    if not user and who.isdigit():
        user = db.query(User).filter(User.id == int(who)).first()
    if not user:
        raise SystemExit(f"没找到账号：{who}")
    return user


def main() -> int:
    ap = argparse.ArgumentParser(description="酒馆rag 账号管理")
    ap.add_argument("--list", action="store_true", help="列出所有账号")
    ap.add_argument("--reset-password", metavar="账号", help="重置密码（用户名或 id）")
    ap.add_argument("--password", help="新密码；不传则交互式输入（更安全，不留命令历史）")
    ap.add_argument("--make-admin", metavar="账号", help="设为管理员")
    ap.add_argument("--deactivate", metavar="账号", help="停用账号")
    args = ap.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.list:
            rows = db.query(User).order_by(User.id).all()
            if not rows:
                print("还没有任何账号。")
                return 0
            print(f"{'id':>3}  {'用户名':<20} {'管理员':<6} {'状态':<6} 注册时间")
            for u in rows:
                n_sessions = db.query(SessionToken).filter(SessionToken.user_id == u.id).count()
                print(f"{u.id:>3}  {u.username:<20} "
                      f"{'是' if u.is_admin else '否':<6} "
                      f"{'正常' if u.is_active else '已停用':<6} {u.created_at}"
                      f"{f'  会话 {n_sessions} 个' if n_sessions else ''}")
            return 0

        if args.reset_password:
            user = _find(db, args.reset_password)
            pw = args.password or getpass.getpass(f"给 {user.username} 设置新密码（至少 6 位）: ")
            if len(pw) < 6:
                raise SystemExit("密码至少 6 位")
            user.password_hash = auth_service.hash_password(pw)
            # 顺手踢掉所有旧会话：忘记密码的场景下，旧会话可能还留在别的浏览器里
            killed = db.query(SessionToken).filter(SessionToken.user_id == user.id).delete()
            db.commit()
            print(f"✅ 已重置 {user.username}（id={user.id}）的密码，"
                  f"并清掉 {killed} 个旧会话。现在可以用新密码登录了。")
            return 0

        if args.make_admin:
            user = _find(db, args.make_admin)
            user.is_admin = True
            db.commit()
            print(f"✅ {user.username} 现在是管理员了")
            return 0

        if args.deactivate:
            user = _find(db, args.deactivate)
            user.is_active = False
            killed = db.query(SessionToken).filter(SessionToken.user_id == user.id).delete()
            db.commit()
            print(f"✅ 已停用 {user.username}，清掉 {killed} 个会话")
            return 0

        ap.print_help()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
