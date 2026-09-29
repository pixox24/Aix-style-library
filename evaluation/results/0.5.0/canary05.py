#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0.5.0 canary：先出差异最大的 2 张（Aix0071 / Aix0095），通过后再全量。

用法：/tmp/aix-dev/bin/python canary05.py
"""
import sys
from pathlib import Path

OUT = Path("/Users/huazi/Desktop/aix-style-library-project/evaluation/results/0.5.0")
sys.path.insert(0, str(OUT))
import batch240  # noqa: E402

env = batch240.load_env()
for key in ("Aix0071-01", "Aix0095-01"):
    prompt = (OUT / "prompts" / (key + ".txt")).read_text(encoding="utf-8")
    try:
        batch240.gen_one(env, key, prompt)
    except Exception as e:
        print("[FAIL] %s %s: %s" % (key, type(e).__name__, str(e)[:200]))
print("canary done")
