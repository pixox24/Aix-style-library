#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 0.3.0 真实出图转换为各风格 thumbnail.webp。

规范：静态 WebP、长边 640px、短边 ≥320px、目标 ≤150 KiB（硬上限 250 KiB）。
用法：/tmp/aix-dev/bin/python thumbs.py
"""
from PIL import Image
import os

ROOT = "/Users/huazi/Desktop/aix-style-library-project"
STYLES = os.path.join(ROOT, "skill", "aix-style-library", "styles")
IMAGES = os.path.join(ROOT, "evaluation", "results", "0.3.0", "images")

for i in range(11, 21):
    sid = f"Aix{i:04d}"
    src = os.path.join(IMAGES, f"{sid}-01.png")
    dst = os.path.join(STYLES, sid, "thumbnail.webp")
    im = Image.open(src).convert("RGB")
    scale = 640 / max(im.size)
    size = (round(im.width * scale), round(im.height * scale))
    im = im.resize(size, Image.Resampling.LANCZOS)
    chosen = None
    for q in (88, 84, 80, 76, 70, 64, 58, 52):
        tmp = dst + ".tmp"
        im.save(tmp, "WEBP", quality=q, method=6)
        n = os.path.getsize(tmp)
        chosen = (q, n)
        if n <= 150 * 1024:
            break
    os.replace(tmp, dst)
    check = Image.open(dst)
    ok = check.format == "WEBP" and max(check.size) == 640 and min(check.size) >= 320 and os.path.getsize(dst) <= 250 * 1024
    print(f"{sid} {size[0]}x{size[1]} q={chosen[0]} {chosen[1] // 1024}KiB {'OK' if ok else 'FAIL'}")
print("thumbs done")
