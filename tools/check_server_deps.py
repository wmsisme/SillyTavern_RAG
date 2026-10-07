#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查「后端用到的第三方包」与「精简镜像里实际装的包」是否有缺口。

为什么要它：公网版用 `backend/requirements-server.txt`（不含 torch/langchain 等），
和本机开发用的 `backend/requirements.txt` 是**两份清单**。新功能引了个包、只加进完整清单，
本机跑得好好的，**一部署就报错** —— 2026-10-06 的「简繁转换」（opencc）就是这么漏的，
而且是在容器里跑工具箱回归时才暴露。这个脚本把这件事变成一条命令。

用法：
    docker compose up -d                       # 先把容器跑起来
    python tools/check_server_deps.py
    python tools/check_server_deps.py --base-url http://127.0.0.1:8000   # 查任意实例的 /health 也行

退出码：0 = 只有预期内的缺失；1 = 有意料之外的缺口（部署会出问题）。
"""
import argparse
import ast
import pathlib
import subprocess
import sys

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

# 导入名 → pip 包名（不总是同名）
ALIAS = {
    "PIL": "pillow", "opencc": "opencc-python-reimplemented", "yaml": "pyyaml",
    "dotenv": "python-dotenv", "sklearn": "scikit-learn", "cv2": "opencv-python",
    "bs4": "beautifulsoup4", "fitz": "pymupdf", "rank_bm25": "rank-bm25",
    "multipart": "python-multipart",
}

# **预期就是没有**的包：有明确降级路径或只服务离线灌库，写清理由免得下次误判
EXPECTED_MISSING = {
    "torch": "只有 EMBED_PROVIDER=local 用得到；代码里是可选导入",
    "transformers": "同上",
    "langchain_core": "只有「从零就地重建索引」用得到；缺了会报一句能照着做的错",
    "opencc_rust": "可选加速实现，会自动回退到 opencc",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", default="app", help="compose 里的服务名")
    args = ap.parse_args()

    try:
        out = subprocess.run(
            ["docker", "compose", "exec", "-T", args.container, "pip", "list", "--format=freeze"],
            cwd=str(ROOT), capture_output=True, text=True,
            # Windows 控制台默认 GBK，docker 的输出是 UTF-8 —— 不写死编码会直接崩在 reader 线程里
            encoding="utf-8", errors="replace", timeout=180)
    except Exception as e:
        print("拿不到容器内的包列表：", e)
        return 2
    installed = {ln.split("==")[0].strip().lower() for ln in out.stdout.splitlines() if "==" in ln}
    if not installed:
        if out.returncode != 0:
            print(f"docker compose exec 失败（退出码 {out.returncode}）：")
            for line in (out.stderr or "").strip().splitlines()[-3:]:
                print("   ", line)
            print("（常见原因：当前目录不是 compose 项目 / 服务名不对 / 容器没起）")
        else:
            print("容器没在跑？先 docker compose up -d")
        return 2
    print(f"容器内已装 {len(installed)} 个包")

    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    found: dict = {}
    for p in BACKEND.rglob("*.py"):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if "__pycache__" in rel:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module]
            for m in mods:
                top = m.split(".")[0]
                if top in stdlib or top == "backend" or top.startswith("_"):
                    continue
                found.setdefault(top, set()).add(rel)

    unexpected, expected = [], []
    for mod, files in sorted(found.items()):
        pkg = ALIAS.get(mod, mod).lower().replace("_", "-")
        if mod.lower() in installed or pkg in installed:
            continue
        (expected if mod in EXPECTED_MISSING else unexpected).append((mod, pkg, sorted(files)))

    if expected:
        print(f"\n预期内没装的 {len(expected)} 个（都有降级路径，不用管）：")
        for mod, _, _ in expected:
            print(f"  · {mod:<16} —— {EXPECTED_MISSING[mod]}")

    if unexpected:
        print(f"\n❌ 有意料之外的缺口 {len(unexpected)} 个（这一部署出去就会报错）：")
        for mod, pkg, files in unexpected:
            print(f"  · import {mod:<16} → 可能要 pip 包 {pkg}")
            print(f"      用在：{', '.join(files[:4])}{' 等' if len(files) > 4 else ''}")
        print("\n补进 backend/requirements-server.txt 后重建镜像；若确实不需要，加进本脚本的 EXPECTED_MISSING 并写明理由。")
        return 1

    print("\n✅ 没有意料之外的依赖缺口")
    return 0


if __name__ == "__main__":
    sys.exit(main())
