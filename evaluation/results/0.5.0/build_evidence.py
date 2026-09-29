#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 0.5.0 证据记录（每风格 6 样例）与生成记录。

输入：samples_plan.json + review_results.json + gen_manifest_v2.json
输出：
  evaluation/results/0.5.0/{sid}.json                 每风格证据记录
  evaluation/results/0.5.0/generations/{key}.json     每样例生成记录
"""
import hashlib
import json
import os

ROOT = "/Users/huazi/Desktop/aix-style-library-project"
OUT = os.path.join(ROOT, "evaluation", "results", "0.5.0")
STYLES_DIR = os.path.join(ROOT, "skill", "aix-style-library", "styles")
TOOL = "gpt-image-2 via change2pro OpenAI-compatible Images API"


def main():
    plan = json.load(open(os.path.join(OUT, "samples_plan.json"), encoding="utf-8"))["samples"]
    review = json.load(open(os.path.join(OUT, "review_results.json"), encoding="utf-8"))
    manifest = json.load(open(os.path.join(OUT, "gen_manifest_v2.json"), encoding="utf-8"))

    by_style = {}
    for entry in plan:
        by_style.setdefault(entry["style_id"], []).append(entry)

    summary = []
    for sid in sorted(by_style):
        style = json.load(open(os.path.join(STYLES_DIR, sid, "style.json"), encoding="utf-8"))
        samples = []
        missing = []
        for entry in sorted(by_style[sid], key=lambda e: e["case"]):
            key = "%s-%s" % (sid, entry["case"])
            r = review.get(key)
            if not r or "error" in r:
                missing.append(key)
                continue
            prompt = open(os.path.join(OUT, entry["prompt_file"]), encoding="utf-8").read()
            img_rel = entry["image_file"]
            img_abs = os.path.join(OUT, img_rel)
            with open(img_abs, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            gen_rel = "results/0.5.0/generations/%s.json" % key
            gen_rec = {
                "status": "generated",
                "tool": TOOL,
                "prompt": prompt,
                "image_sha256": sha,
                "parameters": {"model": "gpt-image-2", "size": "1024x1536",
                               "n": 1, "endpoint": "/v1/images/generations",
                               "seconds": manifest.get(key, {}).get("seconds")},
            }
            with open(os.path.join(OUT, "generations", key + ".json"), "w", encoding="utf-8") as f:
                json.dump(gen_rec, f, ensure_ascii=False, indent=2)
            samples.append({
                "case_id": key,
                "subject_category": entry["category"],
                "prompt": prompt,
                "image_path": "results/0.5.0/%s" % img_rel,
                "style_score": int(r["style_score"]),
                "content_score": int(r["content_score"]),
                "notes": r["note"],
                "generation_ref": gen_rel,
            })
        if missing or len(samples) < 6:
            print("[skip] %s 缺 %s" % (sid, missing or "样本<6"))
            continue
        style_scores = [s["style_score"] for s in samples]
        content_scores = [s["content_score"] for s in samples]
        cat_means = []
        for cat in ("人物", "物体", "场景"):
            vals = [s["style_score"] for s in samples if s["subject_category"] == cat]
            cat_means.append(sum(vals) / len(vals))
        versatility = max(1, min(5, int(sum(cat_means) / len(cat_means) + 0.5)))
        record = {
            "style_id": sid,
            "style_version": style["version"],
            "tested_tool": style["quality"]["tested_tool"],
            "tested_at": style["quality"]["tested_at"],
            "reviewer": "Aix automated vision review (qwen3.7-plus, single reviewer)",
            "review_mode": "self_blind",
            "evidence_type": "image_model",
            "rights_record": "rights/%s.md" % sid,
            "samples": samples,
            "versatility_score": versatility,
            "limitations": ("自动化单评审：由视觉模型按打乱顺序对真实生成样张逐张评分，"
                            "非独立人工复核；覆盖每风格 6 张（人物/物体/场景各 2），"
                            "不等于正式 v1.0 的 660 张全量视觉验收结论。"),
        }
        with open(os.path.join(OUT, "%s.json" % sid), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        summary.append((sid, sum(style_scores) / len(style_scores), sum(content_scores) / len(content_scores), versatility))

    print("%-9s %-6s %-6s %s" % ("风格", "风格均分", "内容均分", "跨题材"))
    for sid, sm, cm, v in summary:
        print("%-9s %-8.2f %-8.2f %d" % (sid, sm, cm, v))
    print("已写 %d 个风格证据" % len(summary))


if __name__ == "__main__":
    main()
