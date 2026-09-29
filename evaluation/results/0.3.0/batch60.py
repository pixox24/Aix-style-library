#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aix 0.3.0 完整验收批量（60 样例 = 10 风格 × 6）。

用法：
  python3 batch60.py prep    # 50 个新样例走 prepare；case 01 复用已有提示词/请求文件
  python3 batch60.py gen     # 生成缺失图片（断点续跑）

产物：requests/ prepare/ prompts/ images/ 采用 {sid}-{case} 命名；samples_plan.json；
      gen_manifest_v2.json（含 sha256/耗时/参数，含复用的 case 01）。
"""
import base64
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
import urllib.request

ROOT = "/Users/huazi/Desktop/aix-style-library-project"
SKILL = os.path.join(ROOT, "skill", "aix-style-library")
OUT = os.path.join(ROOT, "evaluation", "results", "0.3.0")

PLAN = json.load(open(os.path.join(OUT, "plan60.json"), encoding="utf-8"))["samples"]


def load_env():
    env = {}
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"').strip("'")
    return env


def stage_prep():
    py = sys.executable
    plan_out = []
    for entry in PLAN:
        sid, case = entry["style_id"], entry["case"]
        key = "%s-%s" % (sid, case)
        req_path = os.path.join(OUT, "requests", key + ".json")
        prompt_path = os.path.join(OUT, "prompts", key + ".txt")
        if entry.get("reuse"):
            for old, new in [("prompts/%s.txt" % sid, "prompts/%s.txt" % key),
                             ("requests/%s.json" % sid, "requests/%s.json" % key),
                             ("prepare/%s.json" % sid, "prepare/%s.json" % key)]:
                src, dst = os.path.join(OUT, old), os.path.join(OUT, new)
                if os.path.exists(src) and not os.path.exists(dst):
                    with open(src, "rb") as f, open(dst, "wb") as g:
                        g.write(f.read())
            old_req = json.load(open(os.path.join(OUT, "requests", "%s.json" % key), encoding="utf-8"))
            entry["description"] = old_req["intent"]["description"]
            entry["must_preserve"] = old_req["intent"]["must_preserve"]
            plan_out.append({**{k: entry[k] for k in ("style_id", "case", "category")},
                             "reuse": True,
                             "description": entry["description"],
                             "must_preserve": entry["must_preserve"],
                             "prompt_file": "prompts/%s.txt" % key,
                             "image_file": "images/%s.png" % key})
            print("[reuse] %s" % key)
            continue
        req = {
            "api_version": "1.0", "operation": "prepare", "style_id": sid,
            "style_version": None, "mode": "generate", "target": "generic-text-v1",
            "strength": "balanced",
            "intent": {"description": entry["description"], "aspect_ratio": "2:3",
                       "text_literals": [], "must_preserve": entry["must_preserve"]},
            "resolution": {"exclude_features": [], "exclude_avoid": []},
        }
        with open(req_path, "w", encoding="utf-8") as f:
            json.dump(req, f, ensure_ascii=False, indent=2)
        res = subprocess.run([py, os.path.join(SKILL, "scripts", "aix.py"), "prepare", "--input", req_path],
                             capture_output=True, text=True, timeout=60)
        try:
            data = json.loads(res.stdout)
        except Exception:
            print("[FAIL] %s: 无法解析 prepare 输出 rc=%s %s" % (key, res.returncode, res.stderr[:120]))
            continue
        with open(os.path.join(OUT, "prepare", key + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if data.get("status") == "ok":
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(data["data"]["final_prompt"])
            plan_out.append({**{k: entry[k] for k in ("style_id", "case", "category")},
                             "reuse": False,
                             "description": entry["description"],
                             "must_preserve": entry["must_preserve"],
                             "prompt_file": "prompts/%s.txt" % key,
                             "image_file": "images/%s.png" % key})
            print("[OK] %s 特征=%s" % (key, data["data"]["applied_feature_ids"]))
        else:
            print("[ERR] %s: %s %s" % (key, data.get("code"), data.get("message")))
    plan_path = os.path.join(OUT, "samples_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({"samples": plan_out}, f, ensure_ascii=False, indent=2)
    print("prep done: %d/%d" % (len(plan_out), len(PLAN)))


def png_size(raw):
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", raw[16:24])
    return (0, 0)


def gen_one(env, key, prompt):
    out_path = os.path.join(OUT, "images", key + ".png")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100_000:
        print("[skip] %s 已存在" % key)
        return False
    url = env["OPENAI_BASE_URL"].rstrip("/") + "/v1/images/generations"
    payload = json.dumps({"model": env.get("IMAGE_GEN_MODEL", "gpt-image-2"),
                          "prompt": prompt, "size": "1024x1536", "n": 1}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", "Bearer " + env["OPENAI_API_KEY"])
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode())
    item = data["data"][0]
    raw = None
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        rq = urllib.request.Request(item["url"])
        with urllib.request.urlopen(rq, timeout=180) as r2:
            raw = r2.read()
    if not raw:
        raise RuntimeError("响应无图片数据")
    with open(out_path, "wb") as f:
        f.write(raw)
    meta = {k: v for k, v in data.items() if k != "data"}
    meta["data"] = [{k: v for k, v in item.items() if k != "b64_json"}]
    with open(os.path.join(OUT, "images", key + ".meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    width, height = png_size(raw)
    print("[ok] %s %dB %dx%d %.0fs sha=%s" % (key, len(raw), width, height, time.time() - t0,
                                              hashlib.sha256(raw).hexdigest()[:16]))
    return True


def stage_gen():
    env = load_env()
    manifest_path = os.path.join(OUT, "gen_manifest_v2.json")
    manifest = {}
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding="utf-8"))
    old = {}
    old_path = os.path.join(OUT, "gen_manifest.json")
    if os.path.exists(old_path):
        for m in json.load(open(old_path, encoding="utf-8")):
            old[m["style_id"]] = m
    plan = json.load(open(os.path.join(OUT, "samples_plan.json"), encoding="utf-8"))["samples"]
    for entry in plan:
        key = "%s-%s" % (entry["style_id"], entry["case"])
        if key in manifest:
            continue
        prompt = open(os.path.join(OUT, entry["prompt_file"]), encoding="utf-8").read()
        img_path = os.path.join(OUT, "images", key + ".png")
        if not os.path.exists(img_path):
            try:
                gen_one(env, key, prompt)
            except Exception as e:
                print("[FAIL] %s: %s %s" % (key, type(e).__name__, str(e)[:150]))
                time.sleep(2)
                try:
                    gen_one(env, key, prompt)
                    print("[retry-ok] %s" % key)
                except Exception as e2:
                    print("[FAIL2] %s: %s %s" % (key, type(e2).__name__, str(e2)[:150]))
                    continue
        raw = open(img_path, "rb").read()
        entry_rec = {
            "style_id": entry["style_id"], "case": entry["case"], "category": entry["category"],
            "image": entry["image_file"], "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "pixels": "%dx%d" % png_size(raw),
            "model": env.get("IMAGE_GEN_MODEL", "gpt-image-2"), "size_requested": "1024x1536",
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "reused": bool(entry.get("reuse")),
        }
        prev = old.get(entry["style_id"])
        if entry.get("reuse") and prev and prev.get("sha256") == entry_rec["sha256"]:
            entry_rec["seconds"] = prev.get("seconds")
        manifest[key] = entry_rec
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        time.sleep(1)
    print("gen done: manifest %d 条" % len(manifest))


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "prep"
    if stage == "prep":
        stage_prep()
    else:
        stage_gen()
