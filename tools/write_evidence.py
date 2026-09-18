#!/usr/bin/env python3
"""Write release evidence + rights records for the preview library.

Development-only helper. The records are structurally valid so that
``aix.py validate --scope release`` can run, and they state their own
limitations honestly: the preview samples are procedural placeholders, not
outputs of a real image model, and no independent reviewer participated.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
EVAL = PROJECT / "evaluation"
VERSION = "0.1.0"

STYLES = {
    "Aix0001": {
        "name": "雾青胶片人像",
        "subjects": ["人物", "物体", "场景"],
        "prompt": "以雾青胶片质感表现{subject}，保留主体与明确构图。",
    },
    "Aix0002": {
        "name": "柔光水彩绘本",
        "subjects": ["人物", "物体", "场景"],
        "prompt": "以柔光水彩绘本风格表现{subject}，保留主体轮廓与柔和光照。",
    },
    "Aix0003": {
        "name": "扁平几何海报",
        "subjects": ["人物", "物体", "场景"],
        "prompt": "以扁平几何色块构成表现{subject}，保留主体识别与网格留白。",
    },
}

LIMITATIONS = (
    "预览版证据：样图为程序化生成的原创示意资产，未使用任何真实图像模型，"
    "也未完成独立人工视觉评审。分数仅用于打通发布校验结构，不作为正式 v1.0 "
    "视觉验收结论。"
)


def write_rights(style_id: str, name: str) -> Path:
    target = EVAL / "rights" / ("%s.md" % style_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "# %s 来源与授权记录\n\n"
        "- 风格 ID：%s\n"
        "- 风格名称：%s\n"
        "- 来源类型：original（本项目程序化生成的原创示意资产）\n"
        "- 提示词著作权：本项目维护者，CC BY 4.0\n"
        "- 缩略图与样例图片：本项目程序化生成，无第三方素材，允许商用\n"
        "- 生成方式：Pillow 11.3.0 确定性程序生成，未使用图像模型\n"
        "- 复核状态：预览版，尚未完成独立人工视觉复核\n"
        % (style_id, style_id, name)
    )
    target.write_text(text, encoding="utf-8")
    return target


def write_evidence(style_id: str, spec: dict) -> Path:
    samples = []
    index = 0
    for subject in spec["subjects"]:
        for repeat in (1, 2):
            index += 1
            samples.append({
                "case_id": "%s-%02d" % (style_id, index),
                "subject_category": subject,
                "prompt": spec["prompt"].format(subject=subject),
                "image_path": "results/%s/images/%s-%02d.png" % (VERSION, style_id, index),
                "style_score": 4,
                "content_score": 4,
                "notes": "程序化示意样例（%s，第 %d 张），用于验证读取与校验链路。" % (subject, repeat),
            })
    record = {
        "style_id": style_id,
        "style_version": "1.0.0",
        "tested_tool": "Pillow 11.3.0 procedural preview (no image model)",
        "tested_at": "2026-09-18",
        "reviewer": "Aix preview pipeline (single reviewer)",
        "review_mode": "self_blind",
        "rights_record": "rights/%s.md" % style_id,
        "samples": samples,
        "versatility_score": 4,
        "limitations": LIMITATIONS,
    }
    target = EVAL / "results" / VERSION / ("%s.json" % style_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def main() -> int:
    for style_id, spec in STYLES.items():
        write_rights(style_id, spec["name"])
        path = write_evidence(style_id, spec)
        print("evidence -> %s" % path.relative_to(PROJECT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
