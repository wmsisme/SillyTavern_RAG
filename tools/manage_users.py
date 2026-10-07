#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""账号与封禁管理 CLI（本机运维用）。

登录密码是 pbkdf2 哈希存的，**找不回来，只能重置** —— 忘了密码就用这个。

    python tools/manage_users.py --list
    python tools/manage_users.py --reset-password 111              # 交互式输入新密码
    python tools/manage_users.py --reset-password 111 --password 新密码
    python tools/manage_users.py --make-admin 111
    python tools/manage_users.py --ban 456 --reason "共享账号发违规内容"
    python tools/manage_users.py --unban 456
    python tools/manage_users.py --ban-ip 1.2.3.4 --reason "刷站" --days 7
    python tools/manage_users.py --list-ips
    python tools/manage_users.py --unban-ip 1.2.3.4

⚠️ **这个 CLI 是被锁在门外时的兜底**：管理后台的接口都要先登录，
   万一封错人（或把自己封了），从这里解 —— 它直连数据库，不经过 HTTP。
"""
import argparse
import getpass
import sys
from pathlib import Path

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.models.admin import IpBan, QueryLog                   # noqa: E402
from backend.models.database import SessionLocal, init_db          # noqa: E402
from backend.models.user import User, SessionToken                 # noqa: E402
from backend.services import admin_service, auth_service           # noqa: E402


def _find(db, who: str) -> User:
    """按用户名或 id 找人。"""
    user = db.query(User).filter(User.username == who).first()
    if not user and who.isdigit():
        user = db.query(User).filter(User.id == int(who)).first()
    if not user:
        raise SystemExit(f"没找到账号：{who}")
    return user


def main() -> int:
    ap = argparse.ArgumentParser(description="酒馆rag 账号与封禁管理")
    ap.add_argument("--list", action="store_true", help="列出所有账号")
    ap.add_argument("--reset-password", metavar="账号", help="重置密码（用户名或 id）")
    ap.add_argument("--password", help="新密码；不传则交互式输入（更安全，不留命令历史）")
    ap.add_argument("--make-admin", metavar="账号", help="设为管理员")
    ap.add_argument("--deactivate", metavar="账号", help="停用账号（等同于 --ban）")
    ap.add_argument("--ban", metavar="账号", help="封禁账号（踢掉全部在线会话）")
    ap.add_argument("--unban", metavar="账号", help="解封账号")
    ap.add_argument("--reason", default="", help="封禁原因（会显示在管理后台）")
    ap.add_argument("--ban-ip", metavar="IP", help="封禁 IP")
    ap.add_argument("--days", type=int, default=0, help="封禁天数，0 = 永久（默认）")
    ap.add_argument("--list-ips", action="store_true", help="列出 IP 黑名单")
    ap.add_argument("--unban-ip", metavar="IP或ID", help="解除某条 IP 封禁")
    args = ap.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.list:
            rows = db.query(User).order_by(User.id).all()
            if not rows:
                print("还没有任何账号。")
                return 0
            print(f"{'id':>3}  {'用户名':<18} {'管理员':<6} {'状态':<8} {'会话':>4} {'提问':>5}  注册时间 / 封禁原因")
            for u in rows:
                n_sessions = db.query(SessionToken).filter(SessionToken.user_id == u.id).count()
                n_queries = db.query(QueryLog).filter(QueryLog.user_id == u.id).count()
                tail = f"{u.created_at}"
                if not u.is_active:
                    tail = f"封禁原因：{u.ban_reason or '未填'}"
                print(f"{u.id:>3}  {u.username:<18} "
                      f"{'是' if u.is_admin else '否':<6} "
                      f"{'正常' if u.is_active else '已封禁':<8} "
                      f"{n_sessions:>4} {n_queries:>5}  {tail}")
            return 0

        if args.reset_password:
            user = _find(db, args.reset_password)
            pw = args.password or getpass.getpass(
                f"给 {user.username} 设置新密码（至少 {auth_service.MIN_PASSWORD_LEN} 位，别用纯数字）: ")
            # 走和注册 / 改密码**同一套**策略：这个入口是站长的兜底工具，
            # 但不能成为"弱密码的唯一后门"
            try:
                auth_service.check_password_strength(pw)
            except auth_service.AuthError as e:
                raise SystemExit(f"❌ {e}")
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

        who = args.ban or args.deactivate
        if who:
            user = _find(db, who)
            killed = admin_service.ban_user(db, user, reason=args.reason)
            print(f"✅ 已封禁 {user.username}（id={user.id}，原因：{user.ban_reason or '未填'}），"
                  f"踢掉 {killed} 个在线会话。他无法再登录，已登录的也立刻失效。")
            return 0

        if args.unban:
            user = _find(db, args.unban)
            admin_service.unban_user(db, user)
            print(f"✅ 已解封 {user.username}，他可以用原密码重新登录")
            return 0

        if args.ban_ip:
            try:
                row = admin_service.ban_ip(db, args.ban_ip, reason=args.reason,
                                           created_by="cli", days=args.days)
            except ValueError as e:
                raise SystemExit(f"❌ {e}")
            tail = f"{args.days} 天后自动解封" if row.expires_at else "永久"
            print(f"✅ 已封禁 IP {row.ip}（{tail}，原因：{row.reason or '未填'}）")
            return 0

        if args.list_ips:
            rows = db.query(IpBan).order_by(IpBan.id.desc()).all()
            if not rows:
                print("IP 黑名单是空的。")
                return 0
            from datetime import datetime
            now = datetime.now()
            print(f"{'id':>3}  {'IP':<20} {'状态':<8} {'原因':<28} 到期")
            for b in rows:
                expired = bool(b.expires_at and b.expires_at < now)
                print(f"{b.id:>3}  {b.ip:<20} "
                      f"{'已过期' if expired else '封禁中':<8} "
                      f"{(b.reason or '')[:26]:<28} "
                      f"{b.expires_at or '永久'}")
            return 0

        if args.unban_ip:
            key = args.unban_ip
            row = None
            if key.isdigit():
                row = db.query(IpBan).filter(IpBan.id == int(key)).first()
            if not row:
                row = db.query(IpBan).filter(IpBan.ip == admin_service.normalize_ip(key)).first()
            if not row:
                raise SystemExit(f"黑名单里没有：{key}")
            ip = row.ip
            db.delete(row)
            db.commit()
            print(f"✅ 已解封 IP {ip}")
            return 0

        ap.print_help()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
