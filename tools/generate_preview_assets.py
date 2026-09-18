#!/usr/bin/env python3
"""Generate deterministic preview assets for the Aix preview library.

Development-only helper. It produces:

* styles/Aix*/thumbnail.webp for the shipped preview styles
* evaluation/results/<version>/images/*.png preview samples used by the
  release evidence records.

The images are original procedural compositions. They are honest preview
placeholders: they exercise the pipeline (decodable WebP, stable content hash)
and do not claim to be model outputs of any image generator.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

STYLE_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = STYLE_ROOT / "skill" / "aix-style-library"
EVAL_DIR = STYLE_ROOT / "evaluation"

THUMB_SIZE = (640, 400)
SAMPLE_SIZE = (320, 320)

PALETTES = {
    "Aix0001": {
        "bg_top": (28, 58, 68),
        "bg_bottom": (12, 26, 34),
        "warm": (222, 168, 132),
        "cool": (96, 168, 176),
    },
    "Aix0002": {
        "bg": (246, 240, 226),
        "blobs": [(244, 196, 168), (176, 208, 196), (214, 186, 214), (236, 214, 150)],
        "line": (108, 96, 88),
    },
    "Aix0003": {
        "bg": (242, 238, 228),
        "blocks": [(214, 62, 52), (28, 44, 92), (232, 176, 48), (24, 24, 24)],
    },
}


def _vignette(image: Image.Image, strength: float = 0.55) -> Image.Image:
    width, height = image.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((-width * 0.25, -height * 0.35, width * 1.25, height * 1.35), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(width, height) * 0.12))
    dark = Image.new("RGB", (width, height), (0, 0, 0))
    return Image.composite(image, Image.blend(image, dark, strength), mask)


def make_film(seed: int, size: tuple[int, int]) -> Image.Image:
    palette = PALETTES["Aix0001"]
    rng = random.Random(seed)
    width, height = size
    base = Image.new("RGB", size)
    top, bottom = palette["bg_top"], palette["bg_bottom"]
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        ImageDraw.Draw(base).line([(0, y), (width, y)], fill=color)
    glow = Image.new("L", size, 0)
    ImageDraw.Draw(glow).ellipse(
        (width * 0.30, height * 0.12, width * 0.78, height * 0.78), fill=255
    )
    glow = glow.filter(ImageFilter.GaussianBlur(width * 0.10))
    warm_layer = Image.new("RGB", size, palette["warm"])
    image = Image.composite(warm_layer, base, glow.point(lambda v: int(v * 0.55)))
    cool_layer = Image.new("RGB", size, palette["cool"])
    cool_glow = Image.new("L", size, 0)
    ImageDraw.Draw(cool_glow).ellipse(
        (-width * 0.1, height * 0.45, width * 0.45, height * 1.1), fill=255
    )
    cool_glow = cool_glow.filter(ImageFilter.GaussianBlur(width * 0.12))
    image = Image.composite(cool_layer, image, cool_glow.point(lambda v: int(v * 0.35)))
    noise = Image.effect_noise(size, 14).convert("RGB")
    image = Image.blend(image, noise, 0.10)
    image = _vignette(image, 0.5)
    return image


def make_watercolor(seed: int, size: tuple[int, int]) -> Image.Image:
    palette = PALETTES["Aix0002"]
    rng = random.Random(seed)
    width, height = size
    image = Image.new("RGB", size, palette["bg"])
    layer = Image.new("RGB", size, palette["bg"])
    draw = ImageDraw.Draw(layer)
    for _ in range(14):
        radius = rng.randint(int(min(size) * 0.10), int(min(size) * 0.30))
        cx = rng.randint(0, width)
        cy = rng.randint(0, height)
        color = rng.choice(palette["blobs"])
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(min(size) * 0.055))
    image = Image.blend(image, layer, 0.85)
    lines = Image.new("RGB", size, palette["bg"])
    line_draw = ImageDraw.Draw(lines)
    for _ in range(9):
        points = [
            (rng.randint(0, width), rng.randint(0, height))
            for _ in range(4)
        ]
        line_draw.line(points, fill=palette["line"], width=rng.choice([1, 2, 3]))
    image = Image.blend(image, lines, 0.18)
    paper = Image.effect_noise(size, 10).convert("RGB")
    return Image.blend(image, paper, 0.06)


def make_flat(seed: int, size: tuple[int, int]) -> Image.Image:
    palette = PALETTES["Aix0003"]
    rng = random.Random(seed)
    width, height = size
    image = Image.new("RGB", size, palette["bg"])
    draw = ImageDraw.Draw(image)
    blocks = palette["blocks"]
    draw.rectangle((0, int(height * 0.62), width, height), fill=blocks[1])
    draw.rectangle((int(width * 0.08), int(height * 0.10), int(width * 0.42), int(height * 0.58)),
                   fill=blocks[0])
    draw.ellipse((int(width * 0.50), int(height * 0.14), int(width * 0.82), int(height * 0.46)),
                 fill=blocks[2])
    draw.polygon(
        [(int(width * 0.62), height), (int(width * 0.80), int(height * 0.40)),
         (int(width * 0.98), height)],
        fill=blocks[3],
    )
    draw.line([(0, int(height * 0.62)), (width, int(height * 0.62))], fill=blocks[3], width=6)
    draw.line([(int(width * 0.08), 0), (int(width * 0.08), height)], fill=blocks[3], width=4)
    for _ in range(3):
        x = rng.randint(0, width - 20)
        y = rng.randint(0, height - 20)
        draw.rectangle((x, y, x + 14, y + 14), fill=blocks[3])
    noise = Image.effect_noise(size, 8).convert("RGB")
    return Image.blend(image, noise, 0.05)


MAKERS = {
    "Aix0001": make_film,
    "Aix0002": make_watercolor,
    "Aix0003": make_flat,
}


def write_thumbnail(style_id: str, size=THUMB_SIZE, quality: int = 78) -> Path:
    maker = MAKERS[style_id]
    seed = int(style_id[3:]) * 1000 + 7
    image = maker(seed, size)
    target = SKILL_DIR / "styles" / style_id / "thumbnail.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="WEBP", quality=quality, method=6)
    return target


def write_samples(style_id: str, version: str, count: int = 6) -> list[Path]:
    maker = MAKERS[style_id]
    out_dir = EVAL_DIR / "results" / version / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(1, count + 1):
        seed = int(style_id[3:]) * 1000 + index * 37
        image = maker(seed, SAMPLE_SIZE)
        path = out_dir / ("%s-%02d.png" % (style_id, index))
        image.save(path, format="PNG")
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    for style_id in MAKERS:
        thumb = write_thumbnail(style_id)
        size_kib = thumb.stat().st_size / 1024
        print("thumbnail %s -> %s (%.1f KiB)" % (style_id, thumb.relative_to(STYLE_ROOT), size_kib))
        for path in write_samples(style_id, args.version):
            print("  sample -> %s" % path.relative_to(STYLE_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
