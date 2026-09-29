#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""canary：先出 2 张差异最大的风格各 1 张（Aix0011 硬边撞色 / Aix0015 暗黑颗粒），
质检通过后再全量。复用 batch60 的 gen_one。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batch60  # noqa: E402

KEYS = ["Aix0011-01", "Aix0015-01"]


def main():
    env = batch60.load_env()
    for key in KEYS:
        prompt = open(os.path.join(batch60.OUT, "prompts", key + ".txt"), encoding="utf-8").read()
        try:
            batch60.gen_one(env, key, prompt)
        except Exception as e:
            print("[FAIL] %s %s %s" % (key, type(e).__name__, str(e)[:200]))


if __name__ == "__main__":
    main()
