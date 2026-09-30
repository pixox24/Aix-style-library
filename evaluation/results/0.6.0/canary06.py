#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0.6.0 canary：先出差异最大的 2 张（Aix0111 / Aix0136），通过后再全量。

/tmp/aix-dev/bin/python canary06.py
"""
import sys
from pathlib import Path

OUT = Path("/Users/huazi/Desktop/aix-style-library-project/evaluation/results/0.6.0")
sys.path.insert(0, str(OUT))
import batch300  # noqa: E402

env = batch300.load_env()
for key in ("Aix0111-01", "Aix0136-01"):
    prompt = (OUT / "prompts" / (key + ".txt")).read_text(encoding="utf-8")
    try:
        batch300.gen_one(env, key, prompt)
    except Exception as e:
        print("[FAIL] %s %s: %s" % (key, type(e).__name__, str(e)[:200]))
print("canary done")
