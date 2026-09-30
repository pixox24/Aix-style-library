#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 300 张样例的接触表（每 10 个风格一张图，共 5 张）。

输出：evaluation/results/0.6.0/contact-sheet-1..5.png（Aix0111-Aix0160）
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = "/Users/huazi/Desktop/aix-style-library-project"
OUT = os.path.join(ROOT, "evaluation", "results", "0.6.0")
STYLES_DIR = os.path.join(ROOT, "skill", "aix-style-library", "styles")

CELL_W = 300
CELL_H = 450
LABEL_H = 44
GAP = 10
MARGIN = 16
BG = (24, 26, 30)
FG = (235, 235, 235)
ACCENT = (255, 200, 90)

try:
    FONT = ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc", 26)
    FONT_SMALL = ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc", 20)
except Exception:
    FONT = ImageFont.load_default()
    FONT_SMALL = FONT


def style_name(sid):
    with open(os.path.join(STYLES_DIR, sid, "style.json"), encoding="utf-8") as f:
        obj = json.load(f)
    return obj["name"]


def build_sheet(group, path):
    width = MARGIN * 2 + (CELL_W + GAP) * 6 - GAP
    height = MARGIN * 2 + len(group) * (LABEL_H + CELL_H + GAP) - GAP
    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    y = MARGIN
    for sid in group:
        draw.text((MARGIN, y + 8), "%s · %s" % (sid, style_name(sid)), font=FONT, fill=ACCENT)
        y += LABEL_H
        for case in range(1, 7):
            key = "%s-%02d" % (sid, case)
            p = os.path.join(OUT, "images", key + ".png")
            cell = Image.new("RGB", (CELL_W, CELL_H), (44, 46, 52))
            if os.path.exists(p):
                im = Image.open(p).convert("RGB")
                scale = min(CELL_W / im.width, CELL_H / im.height)
                im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
                cell.paste(im, ((CELL_W - im.width) // 2, (CELL_H - im.height) // 2))
            else:
                d2 = ImageDraw.Draw(cell)
                d2.text((20, CELL_H // 2), "missing", font=FONT_SMALL, fill=(200, 80, 80))
            x = MARGIN + (case - 1) * (CELL_W + GAP)
            sheet.paste(cell, (x, y))
            d2 = ImageDraw.Draw(sheet)
            d2.text((x + 8, y + 8), "%02d" % case, font=FONT_SMALL, fill=(255, 255, 255))
        y += CELL_H + GAP
    sheet.save(path)
    print(path, sheet.size)


for _n, _a in enumerate(range(111, 161, 10), start=1):
    build_sheet(["Aix%04d" % i for i in range(_a, _a + 10)], os.path.join(OUT, "contact-sheet-%d.png" % _n))
