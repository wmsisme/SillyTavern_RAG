#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语法自检：对一棵（或多棵）源码树里的所有 .py 做 ast.parse。

故意不用 compileall —— 它会在树里到处生成 __pycache__，
而公网版树是要拿去当仓库的，不能被我自己的检查污染。

用法：python tools/check_syntax.py <目录> [<目录> ...]
退出码：有语法错误 = 1
"""
import ast
import pathlib
import sys

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass



def main(dirs: list[str]) -> int:
    bad = 0
    for d in dirs:
        root = pathlib.Path(d)
        if not root.exists():
            print(f"{d}: 目录不存在")
            bad += 1
            continue
        files = sorted(root.rglob("*.py"))
        errs: list[str] = []
        for p in files:
            try:
                ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errs.append(f"{p}:{e.lineno}: {e.msg}")
            except UnicodeDecodeError as e:
                errs.append(f"{p}: 编码错误 {e}")
        flag = "✅" if not errs else "❌"
        print(f"{flag} {d}：{len(files)} 个 .py，语法错误 {len(errs)} 个")
        for e in errs:
            print("   ✗", e)
        bad += len(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["."]))
