#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""备份本站数据（用户数据 + 密钥）。

备什么
------
    data.db     账号 / 角色卡 / 世界书 / 提问记录 / 用户反馈 / 封禁名单
    static/     用户上传的角色卡图片
    .env        含 SECRET_KEY —— **丢了它，用户存在账号里的 LLM Key 全部解不开**

备到哪
------
    默认 `<项目同级目录>\\酒馆rag-backup\\<时间戳>\\`
    留最近 10 份，更老的自动删（`--keep N` 可改）

⚠️ **备份目录里含明文密钥**（.env），别传到网盘 / 代码仓库 / 任何公开的地方。

用法
----
    python tools/backup.py                # 备份一次 + 清理旧份
    python tools/backup.py --keep 30      # 多留几份
    python tools/backup.py --with-index   # 连向量索引一起备（约 60MB；一般不必，它能从文档重建）
    python tools/backup.py --list         # 看现有备份
    python tools/backup.py --dest E:\\bak # 换备份位置（比如另一个盘 —— 更保险）

为什么要用 SQLite 的备份 API 而不是直接拷文件
------------------------------------------
服务正在跑，直接 copy 可能在某个写事务中间抓到一份**不一致**的库（甚至拷到半个页）。
`sqlite3.Connection.backup()` 是官方在线备份：服务照常写入，备份出来的是完整快照。
"""
import argparse
import datetime
import pathlib
import shutil
import sqlite3
import sys

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "backend" / "data.db"
STATIC_DIR = ROOT / "backend" / "static"
ENV_FILE = ROOT / ".env"
INDEX_DIR = ROOT / "RAG" / "chroma_db"
DEFAULT_DEST = ROOT.parent / "酒馆rag-backup"


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} GB"


def sqlite_online_backup(src: pathlib.Path, dst: pathlib.Path) -> None:
    """官方在线备份：服务在写也能拿到一致快照。"""
    src_con = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    try:
        dst_con = sqlite3.connect(str(dst))
        try:
            with dst_con:
                src_con.backup(dst_con)
        finally:
            dst_con.close()
    finally:
        src_con.close()


def dir_size(p: pathlib.Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def do_backup(args) -> int:
    dest_root = pathlib.Path(args.dest)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_root / stamp

    if not DB.exists():
        print(f"❌ 找不到数据库：{DB}")
        return 2

    dest.mkdir(parents=True, exist_ok=True)
    print(f"备份到：{dest}\n")

    # ① 数据库（在线备份）
    db_out = dest / "data.db"
    sqlite_online_backup(DB, db_out)
    print(f"  ✅ data.db          {human(db_out.stat().st_size)}")

    # ② 卡图
    if STATIC_DIR.exists() and any(STATIC_DIR.rglob("*")):
        shutil.copytree(STATIC_DIR, dest / "static")
        print(f"  ✅ static/          {human(dir_size(dest / 'static'))}")
    else:
        print("  － static/          还没有图片，跳过")

    # ③ .env（含 SECRET_KEY）
    if ENV_FILE.exists():
        shutil.copy2(ENV_FILE, dest / ".env")
        print("  ✅ .env             含 SECRET_KEY（丢了用户存的 Key 全解不开）")

    # ④ 向量索引（可选）
    if args.with_index:
        if INDEX_DIR.exists():
            shutil.copytree(INDEX_DIR, dest / "chroma_db")
            print(f"  ✅ chroma_db/       {human(dir_size(dest / 'chroma_db'))}")
        else:
            print("  － chroma_db/       不存在，跳过")

    total = dir_size(dest)
    print(f"\n合计 {human(total)}")

    # 清理旧份
    keep = max(1, args.keep)
    old = sorted([d for d in dest_root.iterdir() if d.is_dir() and d.name[:8].isdigit()],
                 key=lambda d: d.name, reverse=True)
    removed = 0
    for d in old[keep:]:
        shutil.rmtree(d, ignore_errors=True)
        removed += 1
        print(f"  🗑  清掉旧份 {d.name}")
    print(f"\n✅ 备份完成，保留最近 {keep} 份" + (f"（清掉 {removed} 份）" if removed else ""))
    print("\n⚠️  提醒：这个备份目录里有明文密钥，别传到网盘 / 仓库 / 任何公开的地方。")
    print(f"    现在的位置：{dest_root}")
    return 0


def do_list(args) -> int:
    root = pathlib.Path(args.dest)
    if not root.exists():
        print(f"还没有任何备份（找不到 {root}）")
        return 0
    rows = sorted([d for d in root.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True)
    if not rows:
        print("还没有任何备份。")
        return 0
    print(f"备份目录：{root}\n")
    print(f"  {'时间戳':<18} {'大小':>10}  内容")
    for d in rows:
        items = [p.name for p in d.iterdir() if p.name != ".env"]
        has_env = (d / ".env").exists()
        content = "、".join(items + (["密钥"] if has_env else []))
        stamp = d.name
        try:
            t = datetime.datetime.strptime(stamp, "%Y%m%d-%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            t = stamp
        print(f"  {t:<18} {human(dir_size(d)):>10}  {content}")
    print(f"\n共 {len(rows)} 份")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="酒馆rag 数据备份")
    ap.add_argument("--dest", default=str(DEFAULT_DEST), help=f"备份到哪（默认 {DEFAULT_DEST}）")
    ap.add_argument("--keep", type=int, default=10, help="保留最近几份（默认 10）")
    ap.add_argument("--with-index", action="store_true", help="连向量索引一起备（约 60MB）")
    ap.add_argument("--list", action="store_true", help="列出已有备份")
    args = ap.parse_args()
    return do_list(args) if args.list else do_backup(args)


if __name__ == "__main__":
    sys.exit(main())
