#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 0.4.0 五十风格总览图（验收用）：
两张 5×5 图 —— Aix0021–Aix0045、Aix0046–Aix0070；每格=缩略图（真实出图 case 01）+ 编号/名称/评审均分。
用法：/tmp/aix-dev/bin/python overview_04.py
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/huazi/Desktop/aix-style-library-project")
OUT = ROOT / "evaluation" / "results" / "0.4.0"
STYLES = ROOT / "skill" / "aix-style-library" / "styles"


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
    font_title = load_font(24)

    reviews = json.load(open(OUT / "review_results.json", encoding="utf-8"))

    cw, ch, label_h = 300, 450, 92
    cols, rows = 5, 5
    margin, gap = 22, 18

    for part, start in (("a", 21), ("b", 46)):
        ids = list(range(start, start + 25))
        styles = []
        for i in ids:
            sid = "Aix%04d" % i
            obj = json.load(open(STYLES / sid / "style.json", encoding="utf-8"))
            vals = [v["style_score"] for k, v in reviews.items() if k.startswith(sid + "-") and "style_score" in v]
            mean = sum(vals) / len(vals) if vals else 0.0
            style_vals = vals
            content_vals = [v["content_score"] for k, v in reviews.items()
                            if k.startswith(sid + "-") and "content_score" in v]
            styles.append((sid, obj["name"], mean,
                           sum(content_vals) / len(content_vals) if content_vals else 0.0))

        w = margin * 2 + cols * cw + (cols - 1) * gap
        h = margin * 2 + rows * (ch + label_h) + (rows - 1) * gap + 64
        sheet = Image.new("RGB", (w, h), (22, 23, 28))
        d = ImageDraw.Draw(sheet)
        d.text((margin, 16), "Aix 风格库 0.4.0 · 新增 50 风格总览（%s）· 缩略图为真实出图 case 01" % part.upper(),
               font=font_title, fill=(240, 240, 245))

        for idx, (sid, name, mean, cmean) in enumerate(styles):
            r, c = divmod(idx, cols)
            x = margin + c * (cw + gap)
            y = margin + 64 + r * (ch + label_h + gap)
            thumb = Image.open(STYLES / sid / "thumbnail.webp")
            thumb = thumb.convert("RGB").resize((cw, ch), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (x, y))
            d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=(70, 72, 84))
            d.text((x + 4, y + ch + 8), sid, font=font_id, fill=(255, 205, 100))
            d.text((x + 4, y + ch + 42), name, font=font_name, fill=(235, 235, 240))
            d.text((x + 4, y + ch + 72), "风格 %.2f · 内容 %.2f" % (mean, cmean),
                   font=font_score, fill=(150, 200, 150))

        path = OUT / ("overview_50styles_%s.png" % part)
        sheet.save(path)
        print(path, sheet.size, "styles:", len(styles))


if __name__ == "__main__":
    main()
