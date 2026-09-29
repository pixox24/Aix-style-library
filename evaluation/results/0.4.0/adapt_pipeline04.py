#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""适配 0.3.0 流水线脚本 → 0.4.0 批次（300 样例 / 50 风格）。"""
from pathlib import Path

BASE = Path("/Users/huazi/Desktop/aix-style-library-project/evaluation/results")
SRC, DST = BASE / "0.3.0", BASE / "0.4.0"
DST.mkdir(parents=True, exist_ok=True)

# batch60.py -> batch300.py
t = (SRC / "batch60.py").read_text(encoding="utf-8")
t = t.replace("0.3.0", "0.4.0")
t = t.replace("60 样例 = 10 风格 × 6", "300 样例 = 50 风格 × 6")
assert '"plan60.json"' in t or 'plan60.json' in t
t = t.replace("plan60.json", "plan300.json")
(DST / "batch300.py").write_text(t, encoding="utf-8")

# review.py / build_evidence.py
for name in ["review.py", "build_evidence.py"]:
    t = (SRC / name).read_text(encoding="utf-8").replace("0.3.0", "0.4.0")
    if name == "build_evidence.py":
        t = t.replace("的 120 张全量视觉验收结论", "的 420 张全量视觉验收结论")
    (DST / name).write_text(t, encoding="utf-8")

# thumbs.py：范围 21–70
t = (SRC / "thumbs.py").read_text(encoding="utf-8").replace("0.3.0", "0.4.0")
assert "for i in range(11, 21):" in t, "thumbs 范围不符"
t = t.replace("for i in range(11, 21):", "for i in range(21, 71):")
(DST / "thumbs.py").write_text(t, encoding="utf-8")

# make_sheets.py：5 张接触表（每张 10 风格）
t = (SRC / "make_sheets.py").read_text(encoding="utf-8").replace("0.3.0", "0.4.0")
old = ('build_sheet(["Aix%04d" % i for i in range(11, 16)], os.path.join(OUT, "contact-sheet-1.png"))\n'
       'build_sheet(["Aix%04d" % i for i in range(16, 21)], os.path.join(OUT, "contact-sheet-2.png"))')
assert old in t, "make_sheets 结尾结构不符"
new = ('for _n, _a in enumerate(range(21, 71, 10), start=1):\n'
       '    build_sheet(["Aix%04d" % i for i in range(_a, _a + 10)], os.path.join(OUT, "contact-sheet-%d.png" % _n))')
t = t.replace(old, new)
(DST / "make_sheets.py").write_text(t, encoding="utf-8")

print("适配完成：batch300.py / review.py / build_evidence.py / thumbs.py / make_sheets.py")
print("抽查：")
for f in ["batch300.py", "thumbs.py", "make_sheets.py"]:
    for ln in (DST / f).read_text(encoding="utf-8").splitlines():
        if "plan300" in ln or "range(21" in ln or "contact-sheet" in ln:
            print(" ", f, "|", ln.strip()[:100])
