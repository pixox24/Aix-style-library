#!/usr/bin/env python3
"""Build the README title and galleries from real library resources."""
from pathlib import Path
import json

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill/aix-style-library"
OUT = ROOT / "assets/readme"
STYLE_IDS = ("Aix0001", "Aix0012", "Aix0003", "Aix0111", "Aix0006")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    version = json.loads((SKILL / "library.json").read_text())["library_version"]
    title = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-labelledby="title desc">
  <title id="title">Aix Style Library</title>
  <desc id="desc">Find the look. Keep the intent. A visual style library, preview {version}.</desc>
  <rect width="1200" height="280" rx="16" fill="#0a0b0d"/>
  <g font-family="Arial, Helvetica, sans-serif">
    <rect x="40" y="32" width="10" height="10" rx="2" fill="#ccff33"/>
    <text x="64" y="44" fill="#b8c0b6" font-size="18" letter-spacing="3">VISUAL STYLE INDEX</text>
    <text x="40" y="175" fill="#ccff33" font-size="136" font-weight="700" letter-spacing="-7">Aix</text>
    <text x="285" y="127" fill="#f3f5f2" font-size="62" font-weight="700" letter-spacing="-2">Style Library</text>
    <text x="287" y="178" fill="#bec3bd" font-size="28">Find the look. Keep the intent.</text>
    <line x1="40" y1="219" x2="1160" y2="219" stroke="#30352e"/>
    <text x="40" y="255" fill="#b8c0b6" font-size="18" letter-spacing="2">LOOK UP / EXPLORE / CREATE</text>
    <text x="1160" y="255" fill="#ccff33" font-size="18" text-anchor="end">{version} · PREVIEW</text>
  </g>
  <g fill="none" stroke="#ccff33" stroke-width="2">
    <rect x="942" y="65" width="78" height="116" rx="5" opacity="0.2"/>
    <rect x="967" y="55" width="78" height="116" rx="5" opacity="0.4"/>
    <rect x="992" y="45" width="78" height="116" rx="5" opacity="0.7"/>
    <rect x="1017" y="35" width="78" height="116" rx="5"/>
  </g>
</svg>
'''
    (OUT / "hero.svg").write_text(title, encoding="utf-8")
    # Each card is an existing published thumbnail; no generated or stock art.
    board = Image.new("RGB", (1200, 376), "#0a0b0d")
    for i, sid in enumerate(STYLE_IDS):
        with Image.open(SKILL / "styles" / sid / "thumbnail.webp") as source:
            card = ImageOps.fit(source.convert("RGB"), (224, 336))
        mask = Image.new("L", card.size)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 223, 335), radius=8, fill=255)
        board.paste(card, (16 + i * 236, 16), mask)
        ImageDraw.Draw(board).line((16 + i * 236, 364, 60 + i * 236, 364), fill="#ccff33", width=2)
    board.save(OUT / "style-spectrum.webp", quality=88, method=6)
    examples = Image.new("RGB", (1200, 608), "#0a0b0d")
    for i, sample in enumerate(("01", "03", "05")):
        source_path = ROOT / "evaluation/results/0.2.0/images" / f"Aix0006-{sample}.png"
        with Image.open(source_path) as source:
            card = ImageOps.fit(source.convert("RGB"), (384, 576))
        examples.paste(card, (8 + i * 400, 16))
    examples.save(OUT / "cross-subject.webp", quality=88, method=6)
    print("Built hero.svg, style-spectrum.webp and cross-subject.webp")


if __name__ == "__main__":
    main()
