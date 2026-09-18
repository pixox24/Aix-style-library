#!/usr/bin/env python3
"""Local performance benchmark for get/search.

Includes CLI process startup, matching the PRD measurement method: one warm-up
run, then 30 timed runs, reporting p50/p95. ``--synthetic N`` clones the
library to a temporary root with N styles to exercise the 1,000-style target.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SKILL_SRC = PROJECT / "skill" / "aix-style-library"
SCRIPT = SKILL_SRC / "scripts" / "aix.py"
RUNS = 30


def clone_library(dest: Path, count: int) -> Path:
    shutil.copytree(SKILL_SRC, dest / "aix-style-library")
    root = dest / "aix-style-library"
    template = json.loads((root / "styles" / "Aix0001" / "style.json").read_text(encoding="utf-8"))
    thumb = (root / "styles" / "Aix0001" / "thumbnail.webp").read_bytes()
    for number in range(2, count + 1):
        sid = "Aix%04d" % number
        directory = root / "styles" / sid
        directory.mkdir(parents=True, exist_ok=True)
        obj = json.loads(json.dumps(template))
        obj["id"] = sid
        obj["name"] = "%s %d" % (template["name"], number)
        (directory / "style.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (directory / "thumbnail.webp").write_bytes(thumb)
    subprocess.run(
        [sys.executable, str(root / "scripts" / "aix.py"), "build-index"],
        check=True, capture_output=True,
    )
    return root


def time_command(argv, cwd):
    start = time.perf_counter()
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    elapsed_ms = (time.perf_counter() - start) * 1000
    if completed.returncode != 0:
        raise SystemExit("command failed: %s\n%s" % (argv, completed.stdout))
    return elapsed_ms


def summarize(label, samples):
    samples = sorted(samples)
    p50 = statistics.median(samples)
    p95 = samples[max(0, int(len(samples) * 0.95) - 1)]
    print("%-28s p50=%6.1f ms  p95=%6.1f ms" % (label, p50, p95))
    return {"p50": round(p50, 2), "p95": round(p95, 2)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", type=int, default=0)
    parser.add_argument("--runs", type=int, default=RUNS)
    args = parser.parse_args()

    if args.synthetic:
        temp = Path(tempfile.mkdtemp(prefix="aix-bench-"))
        root = clone_library(temp, args.synthetic)
    else:
        temp = None
        root = SKILL_SRC
    cwd = temp or PROJECT

    script = root / "scripts" / "aix.py"
    request = temp / "search-request.json" if temp else PROJECT / "tests" / "fixtures" / "requests" / "search-soft.json"
    if temp:
        request.write_text(json.dumps({
            "api_version": "1.0", "operation": "search", "query": "柔和水彩",
            "terms": ["柔和", "水彩"], "category": None, "limit": 3,
        }, ensure_ascii=False), encoding="utf-8")

    style_count = len(list((root / "styles").glob("*/style.json")))
    print("styles=%d  python=%s  platform=%s  cpu_count=%s" % (
        style_count, platform.python_version(), platform.platform(), os.cpu_count()))

    get_cmd = [sys.executable, str(script), "get", "--id", "0001"]
    search_cmd = [sys.executable, str(script), "search", "--input", str(request)]

    time_command(get_cmd, cwd)
    time_command(search_cmd, cwd)

    results = {
        "styles": style_count,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "runs": args.runs,
    }
    results["get"] = summarize("get", [time_command(get_cmd, cwd) for _ in range(args.runs)])
    results["search"] = summarize("search", [time_command(search_cmd, cwd) for _ in range(args.runs)])

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if temp:
        shutil.rmtree(temp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
