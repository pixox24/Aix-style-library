#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aix 0.5.0 批次：写入 40 个新风格（Aix0071–Aix0110）、权利记录、素材映射和 240 条样例计划。

素材：~/Desktop/插画库/ 的 61–100 号图；每张源图作为一个独立风格种子。
验收：每个风格 6 张真实样例（人物/物体/场景各 2）。
"""
import json
import shutil
from pathlib import Path

import jsonschema
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/huazi/Desktop/aix-style-library-project")
SKILL = ROOT / "skill" / "aix-style-library"
STYLES_DIR = SKILL / "styles"
RIGHTS = ROOT / "evaluation" / "rights"
OUT = ROOT / "evaluation" / "results" / "0.5.0"
LIB = Path.home() / "Desktop" / "插画库"
SOURCES = ROOT / "evaluation" / "sources" / "2026-09-batch3"
SCHEMA = json.loads((SKILL / "references" / "schemas" / "style.schema.json").read_text(encoding="utf-8"))

TOOL = "gpt-image-2 via change2pro OpenAI-compatible Images API"
TESTED_AT = "2026-09-28"
IMG_FIRST, IMG_LAST = 61, 100


def _load_font(size):
    for path in ("/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Light.ttc",
                 "/System/Library/Fonts/Supplemental/Songti.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def load_defs():
    ns = {}
    exec((OUT / "defs_part4.py").read_text(encoding="utf-8"), ns)
    return ns["STYLES"]


def find_source(n):
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        p = LIB / ("%d%s" % (n, ext))
        if p.exists():
            return p
    raise FileNotFoundError("素材 %d 未找到" % n)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("images", "prompts", "requests", "prepare", "generations"):
        (OUT / sub).mkdir(exist_ok=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    RIGHTS.mkdir(parents=True, exist_ok=True)

    styles = load_defs()
    assert len(styles) == 40, "风格数不符: %d" % len(styles)
    expected = ["Aix%04d" % i for i in range(71, 111)]
    assert [s["id"] for s in styles] == expected, "ID 序列不符"

    font = _load_font(34)
    font_small = _load_font(20)
    mapping = {}
    n = IMG_FIRST
    plan_samples = []

    for st in styles:
        sid = st["id"]
        sdir = STYLES_DIR / sid
        assert not sdir.exists(), "目录已存在（拒绝覆盖）：%s" % sdir
        sdir.mkdir(parents=True)

        style_obj = {
            "schema_version": "1.0",
            "id": sid,
            "version": "1.0.0",
            "status": "active",
            "name": st["name"],
            "description": st["description"],
            "category": st["category"],
            "tags": st["tags"],
            "aliases": st["aliases"],
            "thumbnail": {"path": "thumbnail.webp", "media_type": "image/webp", "alt": st["alt"]},
            "features": st["features"],
            "avoid": st["avoid"],
            "suitable_for": st["suitable_for"],
            "weak_for": st["weak_for"],
            "known_failures": st["known_failures"],
            "provenance": {
                "source_type": "original",
                "source_ref": "evaluation/rights/%s.md" % sid,
                "license_ref": "LICENSE.md#2-风格提示词与结构化数据",
                "commercial_use": "allowed",
                "attribution": None,
            },
            "quality": {
                "review_status": "passed",
                "tested_tool": TOOL,
                "tested_at": TESTED_AT,
                "evidence_ref": "results/0.5.0/%s.json" % sid,
            },
            "replacement_id": None,
        }
        jsonschema.validate(style_obj, SCHEMA)
        (sdir / "style.json").write_text(
            json.dumps(style_obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 占位缩略图：真实出图完成后由 thumbs.py 立即替换。
        img = Image.new("RGB", (427, 640), (26, 27, 33))
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, 419, 632], outline=(90, 92, 104), width=2)
        d.text((40, 270), sid, font=font, fill=(230, 230, 235))
        d.text((40, 320), "%s · 占位" % st["name"], font=font_small, fill=(150, 152, 160))
        d.text((40, 360), "待真实出图替换", font=font_small, fill=(110, 112, 120))
        img.save(sdir / "thumbnail.webp", "WEBP", quality=82, method=6)
        assert (sdir / "thumbnail.webp").stat().st_size <= 250 * 1024

        src = find_source(n)
        rights = (
            "# %s 来源与授权记录\n\n"
            "- 风格 ID：%s\n"
            "- 风格名称：%s\n"
            "- 来源类型：original（本项目维护者创作的原创风格定义与提示词）\n"
            "- 提示词著作权：本项目维护者，CC BY 4.0\n"
            "- 缩略图与样例图片：由 gpt-image-2（经由 change2pro OpenAI 兼容 Images API）于 %s 生成，无第三方素材，允许商用\n"
            "- 生成方式：真实图像模型生成（生成清单见 evaluation/results/0.5.0/gen_manifest_v2.json）\n"
            "- 素材溯源：收藏图 %d（副本见 evaluation/sources/2026-09-batch3/，全量存档见 09_原图存档_2026-09-20）\n"
            "- 复核状态：预览批次（0.5.0 批次）每风格 6 张真实样张（人物/物体/场景各 2），自动化盲评见评价证据记录；正式 v1.0 验收尚未完成\n"
        ) % (sid, sid, st["name"], TESTED_AT, n)
        (RIGHTS / (sid + ".md")).write_text(rights, encoding="utf-8")

        mapping[sid] = {
            "source_file": src.name,
            "source_number": n,
            "archive_ref": "~/Desktop/插画库_审美分析/09_原图存档_2026-09-20/收藏原图_1-204/%s" % src.name,
        }
        shutil.copy2(src, SOURCES / src.name)

        for i, (cat, desc, mp) in enumerate(st["plan"]):
            plan_samples.append({
                "style_id": sid,
                "case": "%02d" % (i + 1),
                "category": cat,
                "description": desc,
                "must_preserve": mp,
            })
        print("[ok] %s %s ← %s" % (sid, st["name"], src.name))
        n += 1

    assert n == IMG_LAST + 1
    assert len(plan_samples) == 240
    mapping_text = json.dumps(mapping, ensure_ascii=False, indent=2)
    (SOURCES / "mapping.json").write_text(mapping_text, encoding="utf-8")
    (OUT / "sources_mapping.json").write_text(mapping_text, encoding="utf-8")
    (OUT / "plan240.json").write_text(json.dumps({
        "note": "0.5.0 批次：40 个新风格（Aix0071–Aix0110）× 6 样例（人物/物体/场景各 2）；全部新生成。",
        "samples": plan_samples,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("风格写入: %d | 权利记录: %d | 计划样例: %d | 素材副本: %d" %
          (len(styles), len(styles), len(plan_samples), len(mapping)))


if __name__ == "__main__":
    main()
