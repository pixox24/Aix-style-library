#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 0.2.0 流水线脚本适配为本批次 0.3.0 版本（仅改路径/范围/字体，逻辑不动）。"""
from pathlib import Path

BASE = Path("/Users/huazi/Desktop/aix-style-library-project/evaluation/results")
SRC, DST = BASE / "0.2.0", BASE / "0.3.0"

FILES = ["batch60.py", "review.py", "build_evidence.py", "thumbs.py", "make_sheets.py"]

for name in FILES:
    text = (SRC / name).read_text(encoding="utf-8")
    new = text.replace("0.2.0", "0.3.0")

    if name == "thumbs.py":
        assert "for i in range(1, 11):" in new
        new = new.replace("for i in range(1, 11):", "for i in range(11, 21):")

    if name == "make_sheets.py":
        assert 'range(1, 6)' in new and 'range(6, 11)' in new
        new = new.replace("range(1, 6)", "range(11, 16)").replace("range(6, 11)", "range(16, 21)")
        # macOS 26 无 PingFang.ttc，换 STHeiti（已实测可打开，保留 except 回退）
        new = new.replace('"/System/Library/Fonts/PingFang.ttc"',
                          '"/System/Library/Fonts/STHeiti Light.ttc"')

    (DST / name).write_text(new, encoding="utf-8")
    print(f"[ok] {name}")

print()
print("== 适配结果抽查 ==")
for name in ["thumbs.py", "make_sheets.py"]:
    t = (DST / name).read_text(encoding="utf-8")
    for line in t.splitlines():
        if "range(" in line and "Aix" in line or "for i in range" in line or "STHeiti" in line:
            print(f"{name}: {line.strip()[:110]}")
