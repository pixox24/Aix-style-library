#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 0.3.0 十风格总览图（验收用）：2×5 缩略图 + 编号/名称/评审均分。"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/huazi/Desktop/aix-style-library-project")
OUT = ROOT / "evaluation" / "results" / "0.3.0"


def load_font(size):
    for path in ("/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Light.ttc",
                 "/System/Library/Fonts/Supplemental/Songti.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main():
    font_id = load_font(30)
    font_name = load_font(26)
    font_score = load_font(20)

    reviews = json.load(open(OUT / "review_results.json", encoding="utf-8"))
    styles = []
    for i in range(11, 21):
        sid = "Aix%04d" % i
        obj = json.load(open(ROOT / "skill" / "aix-style-library" / "styles" / sid / "style.json",
                             encoding="utf-8"))
        vals = [v["style_score"] for k, v in reviews.items() if k.startswith(sid + "-")]
        mean = sum(vals) / len(vals)
        styles.append((sid, obj["name"], mean))

    cw, ch, label_h = 300, 450, 92
    cols, rows = 5, 2
    margin, gap = 22, 18
    w = margin * 2 + cols * cw + (cols - 1) * gap
    h = margin * 2 + rows * (ch + label_h) + (rows - 1) * gap + 64
    sheet = Image.new("RGB", (w, h), (22, 23, 28))
    d = ImageDraw.Draw(sheet)
    d.text((margin, 16), "Aix 风格库 0.3.0 · 新增 10 风格验收总览（缩略图为真实出图 case 01）",
           font=font_name, fill=(240, 240, 245))

    for idx, (sid, name, mean) in enumerate(styles):
        r, c = divmod(idx, cols)
        x = margin + c * (cw + gap)
        y = margin + 64 + r * (ch + label_h + gap)
        thumb = Image.open(ROOT / "skill" / "aix-style-library" / "styles" / sid / "thumbnail.webp")
        thumb = thumb.convert("RGB").resize((cw, ch), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))
        d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=(70, 72, 84))
        d.text((x + 4, y + ch + 8), sid, font=font_id, fill=(255, 205, 100))
        d.text((x + 4, y + ch + 42), name, font=font_name, fill=(235, 235, 240))
        d.text((x + 4, y + ch + 72), "风格均分 %.2f / 5" % mean, font=font_score, fill=(150, 200, 150))

    path = OUT / "overview_10styles.png"
    sheet.save(path, quality=92)
    print(path, sheet.size)


if __name__ == "__main__":
    main()
