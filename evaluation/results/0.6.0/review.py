#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aix 0.6.0 样例视觉评审：用 qwen3.7-plus（百炼/dashscope 兼容接口）逐张评分。

用法：
  python3 review.py --keys Aix0004-01          # 单张（测试）
  python3 review.py                            # 全部未评审样例（断点续跑）

输出：review_results.json  {key: {style_score, content_score, note, reviewed_at, model}}
评审顺序打乱（固定种子），属自动化单评审，limitations 在证据记录中如实声明。
"""
import argparse
import base64
import io
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = "/Users/huazi/Desktop/aix-style-library-project"
OUT = os.path.join(ROOT, "evaluation", "results", "0.6.0")
STYLES_DIR = os.path.join(ROOT, "skill", "aix-style-library", "styles")
RESULT_PATH = os.path.join(OUT, "review_results.json")
MODEL = "qwen3.7-plus"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_lock = threading.Lock()


def load_env():
    env = {}
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"').strip("'")
    return env


def style_brief(sid):
    with open(os.path.join(STYLES_DIR, sid, "style.json"), encoding="utf-8") as f:
        obj = json.load(f)
    feats = "；".join(item["text"] for item in obj["features"])
    return obj["name"], feats


def make_question(entry):
    name, feats = style_brief(entry["style_id"])
    must = "；".join(entry.get("must_preserve") or [])
    return (
        "你是严格的图像评审员，正在为图片风格库执行验收评分。评审基调：从严。\n"
        "默认给 4 分；只有逐项核对后找不到任何可见瑕疵时才给 5 分；"
        "发现下列任一问题必须扣分并在 note 中说明：伪文字/乱码文字或印章、结构或解剖错误、"
        "必须保留元素缺失或变形、风格核心特征偏弱或串味。\n"
        "【风格名称】%s\n【风格核心特征】%s\n"
        "【生成要求·画面内容】%s\n【必须保留】%s\n"
        "【评分标准】style_score（风格一致性）：5=核心视觉特征稳定清楚且无可见瑕疵；"
        "4=主要特征可见、存在轻微瑕疵或偏差；3=部分核心特征可见；1=与定义明显不符。"
        "content_score（内容保留）：5=主体和明确要求完整保留且无可见瑕疵；"
        "4=主体正确、存在轻微偏差；3=主体对但重要要求有偏差；1=主体或关键要求错误。\n"
        "请仔细观察图片（尤其检查是否出现乱码文字、结构错误、元素缺失），"
        "只输出一行 JSON（不要代码块）："
        "{\"style_score\": <1-5整数>, \"content_score\": <1-5整数>, \"note\": \"<关键依据；如有瑕疵必须指出。中文，40字内>\"}"
        % (name, feats, entry["description"], must or "（无）")
    )


def image_data_url(path, max_edge=768):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    scale = max_edge / max(im.size)
    if scale < 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def call_model(env, question, data_url, with_thinking=True):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
        "max_tokens": 900,
        "temperature": 0.2,
    }
    if with_thinking:
        body["enable_thinking"] = True
        body["thinking_budget"] = 8192
    req = urllib.request.Request(BASE_URL + "/chat/completions",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", "Bearer " + env["BAILIAN_API_KEY"])
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=150) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"].get("content") or ""


def parse_scores(text):
    m = re.search(r"\{[^{}]*\"style_score\"[^{}]*\}", text)
    if not m:
        raise ValueError("未找到 JSON: %s" % text[:120])
    obj = json.loads(m.group(0))
    style = int(obj["style_score"])
    content = int(obj["content_score"])
    if not (1 <= style <= 5 and 1 <= content <= 5):
        raise ValueError("分数越界")
    note = str(obj.get("note", "")).strip()[:200]
    return style, content, note


def review_one(env, entry):
    key = "%s-%s" % (entry["style_id"], entry["case"])
    img = os.path.join(OUT, entry["image_file"])
    data_url = image_data_url(img)
    question = make_question(entry)
    last_err = None
    for attempt in range(3):
        try:
            try:
                text = call_model(env, question, data_url, with_thinking=True)
            except urllib.error.HTTPError as e:
                if e.code == 400:
                    text = call_model(env, question, data_url, with_thinking=False)
                else:
                    raise
            style, content, note = parse_scores(text)
            return key, {"style_score": style, "content_score": content, "note": note,
                         "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": MODEL}
        except Exception as e:
            last_err = e
            time.sleep(3 * (attempt + 1))
    return key, {"error": "%s: %s" % (type(last_err).__name__, str(last_err)[:200])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", help="逗号分隔的 key，缺省=全部")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    env = load_env()
    plan = json.load(open(os.path.join(OUT, "samples_plan.json"), encoding="utf-8"))["samples"]
    todo = []
    for entry in plan:
        key = "%s-%s" % (entry["style_id"], entry["case"])
        if args.keys and key not in set(args.keys.split(",")):
            continue
        if not os.path.exists(os.path.join(OUT, entry["image_file"])):
            print("[skip-no-image] %s" % key)
            continue
        todo.append(entry)

    results = {}
    if os.path.exists(RESULT_PATH):
        results = json.load(open(RESULT_PATH, encoding="utf-8"))
    pending = []
    for e in todo:
        k = "%s-%s" % (e["style_id"], e["case"])
        r = results.get(k)
        if r is None or "error" in r:
            pending.append(e)
    todo = pending
    random.Random(20260919).shuffle(todo)
    print("待评审 %d 张，并发 %d" % (len(todo), args.workers))

    done = [0]

    def work(entry):
        key, res = review_one(env, entry)
        with _lock:
            results[key] = res
            done[0] += 1
            with open(RESULT_PATH, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            if "error" in res:
                print("[ERR] %s -> %s" % (key, res["error"]))
            else:
                print("[%d/%d] %s style=%d content=%d %s" % (
                    done[0], len(todo), key, res["style_score"], res["content_score"], res["note"][:50]))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))
    print("review done: %d 条结果" % len(results))


if __name__ == "__main__":
    main()
