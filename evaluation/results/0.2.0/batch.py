#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aix 0.2.0 MVP 批量脚本：prepare + 真实出图（change2pro gpt-image-2）。

用法：
  python3 batch.py prep                                  # 写请求 + 调 aix.py prepare + 收集最终提示词
  python3 batch.py gen [--only Aix0002,Aix0004]          # 调图像工具出图（可断点续跑）

产物（evaluation/results/0.2.0/ 下）：
  requests/<ID>.json    prepare 请求原文
  prepare/<ID>.json     prepare 完整响应
  prompts/<ID>.txt      最终提示词（即实际送去出图的文本）
  images/<ID>-01.png    生成图片
  images/<ID>-01.meta.json  生成响应元数据（去掉 b64）
  gen_manifest.json     生成清单（sha256/耗时/参数）
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = "/Users/huazi/Desktop/aix-style-library-project"
SKILL = os.path.join(ROOT, "skill", "aix-style-library")
OUT = os.path.join(ROOT, "evaluation", "results", "0.2.0")
for _sub in ("requests", "prepare", "prompts", "images", "generations"):
    os.makedirs(os.path.join(OUT, _sub), exist_ok=True)

PLAN = {
    "Aix0001": {"description": "清晨窗前，一位穿米色针织衫的年轻人侧身站在柔光里，侧脸望向窗外", "must_preserve": ["窗前人物", "柔和侧光"], "category": "人物"},
    "Aix0002": {"description": "一只橘猫趴在木窗台上打盹，窗外是长满绿植的小院子，午后柔光", "must_preserve": ["橘猫", "木窗台"], "category": "场景"},
    "Aix0003": {"description": "一组手冲咖啡器具的几何化海报：咖啡壶、杯子和一株盆栽，暖色块与留白", "must_preserve": ["咖啡器具", "几何构图"], "category": "物体"},
    "Aix0004": {"description": "远山、湖面与一叶孤舟，天边一行归鸟", "must_preserve": ["远山", "孤舟"], "category": "场景"},
    "Aix0005": {"description": "窗台上一只陶罐插着野花，旁边放着两颗柠檬，午后侧光", "must_preserve": ["陶罐野花", "柠檬"], "category": "物体"},
    "Aix0006": {"description": "一个背着红色小背包的黏土小人偶站在绿色的小山坡上，远处有一栋小房子", "must_preserve": ["黏土小人偶", "小山坡"], "category": "人物"},
    "Aix0007": {"description": "山谷、湖泊与松树的低多边形风景，天空中是渐变晚霞", "must_preserve": ["山谷湖泊", "松树"], "category": "场景"},
    "Aix0008": {"description": "雨夜街头，一位撑着透明雨伞的行人走过霓虹招牌下，路面湿润反光", "must_preserve": ["撑伞行人", "霓虹招牌"], "category": "人物"},
    "Aix0009": {"description": "悬崖上的小灯塔，塔顶一扇窗亮着暖黄的灯，几只海鸟盘旋", "must_preserve": ["灯塔", "暖黄灯窗"], "category": "场景"},
    "Aix0010": {"description": "一台复古双反相机的丝网印海报构图，背景是起伏的山脉和太阳", "must_preserve": ["复古相机", "山脉与太阳"], "category": "物体"},
}


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
    for sid, spec in PLAN.items():
        req = {
            "api_version": "1.0", "operation": "prepare", "style_id": sid,
            "style_version": None, "mode": "generate", "target": "generic-text-v1",
            "strength": "balanced",
            "intent": {"description": spec["description"], "aspect_ratio": "2:3",
                       "text_literals": [], "must_preserve": spec["must_preserve"]},
            "resolution": {"exclude_features": [], "exclude_avoid": []},
        }
        req_path = os.path.join(OUT, "requests", sid + ".json")
        with open(req_path, "w", encoding="utf-8") as f:
            json.dump(req, f, ensure_ascii=False, indent=2)
        res = subprocess.run([py, os.path.join(SKILL, "scripts", "aix.py"), "prepare", "--input", req_path],
                             capture_output=True, text=True, timeout=60)
        try:
            data = json.loads(res.stdout)
        except Exception:
            print(f"[FAIL] {sid}: 无法解析 prepare 输出 rc={res.returncode} stderr={res.stderr[:200]}")
            continue
        with open(os.path.join(OUT, "prepare", sid + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if data.get("status") == "ok":
            prompt = data["data"]["final_prompt"]
            with open(os.path.join(OUT, "prompts", sid + ".txt"), "w", encoding="utf-8") as f:
                f.write(prompt)
            print(f"[OK] {sid} 特征={data['data']['applied_feature_ids']} prompt={len(prompt)}字")
        else:
            print(f"[ERR] {sid}: {data.get('code')} {data.get('message')}")


def gen_one(env, sid):
    with open(os.path.join(OUT, "prompts", sid + ".txt"), encoding="utf-8") as f:
        prompt = f.read()
    out_path = os.path.join(OUT, "images", sid + "-01.png")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100_000:
        print(f"[skip] {sid} 已存在")
        return None
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
        # 2026-09 起该网关返回资源 URL；URL 可直接下载（无需鉴权，已实测）。
        rq = urllib.request.Request(item["url"])
        with urllib.request.urlopen(rq, timeout=180) as r2:
            raw = r2.read()
    if not raw:
        raise RuntimeError("响应无图片数据: " + json.dumps({k: v for k, v in item.items() if k != "b64_json"})[:200])
    with open(out_path, "wb") as f:
        f.write(raw)
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        import struct
        width, height = struct.unpack(">II", raw[16:24])
    else:
        width = height = 0
    meta = {k: v for k, v in data.items() if k != "data"}
    meta["data"] = [{k: v for k, v in item.items() if k != "b64_json"}]
    with open(os.path.join(OUT, "images", sid + "-01.meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    sha = hashlib.sha256(raw).hexdigest()
    seconds = round(time.time() - t0, 1)
    print(f"[ok] {sid} {len(raw)}B {width}x{height} {seconds}s sha={sha[:16]}")
    return {"style_id": sid, "image": f"images/{sid}-01.png", "sha256": sha,
            "bytes": len(raw), "pixels": f"{width}x{height}", "seconds": seconds,
            "model": env.get("IMAGE_GEN_MODEL", "gpt-image-2"), "size_requested": "1024x1536",
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}


def stage_gen(only=None):
    env = load_env()
    manifest_path = os.path.join(OUT, "gen_manifest.json")
    manifest = []
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path, encoding="utf-8"))
    done = {m["style_id"] for m in manifest}
    for sid in PLAN:
        if only and sid not in only:
            continue
        if sid in done:
            print(f"[skip] {sid} 已记录")
            continue
        rec = None
        try:
            rec = gen_one(env, sid)
        except Exception as e:
            print(f"[FAIL] {sid}: {type(e).__name__} {str(e)[:200]}")
            time.sleep(2)
            try:
                rec = gen_one(env, sid)
                print(f"[retry-ok] {sid}")
            except Exception as e2:
                print(f"[FAIL2] {sid}: {type(e2).__name__} {str(e2)[:200]}")
        if rec:
            manifest.append(rec)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        time.sleep(1)
    print("DONE")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "prep"
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    if stage == "prep":
        stage_prep()
    else:
        stage_gen(only)
