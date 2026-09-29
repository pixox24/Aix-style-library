#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回滚演练 0.3.2 → 0.2.0 → 0.3.2：逐版本解包冒烟（get/search/prepare）+
包完整性核对。产出 evaluation/results/0.3.0/package-rollback.json。

用法：/tmp/aix-dev/bin/python drill.py   （发布完成后运行）
"""
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path("/Users/huazi/Desktop/aix-style-library-project")
RELEASES = PROJECT / "releases"
SKILL_SRC = PROJECT / "skill" / "aix-style-library"
OUT = PROJECT / "evaluation" / "results" / "0.3.0"

# 每轮的探测目标：新版用新风格，旧版用旧风格
PROBES = {
    "0.3.2": {"sid": "0011", "term": "撞色"},
    "0.2.0": {"sid": "0004", "term": "水墨"},
}
SEQUENCE = ["0.3.2", "0.2.0", "0.3.2"]


def run_cli(root, args):
    r = subprocess.run([sys.executable, "-B", str(root / "scripts" / "aix.py"), *args],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    if r.returncode != 0:
        return {"code": "FAIL", "stage": None, "stderr": (r.stderr or r.stdout)[:200]}
    out = json.loads(r.stdout)
    return {"code": out.get("code", "?"), "stage": out.get("data", {}).get("stage")}


def probe_version(version, work):
    zip_path = RELEASES / ("aix-style-library-%s.zip" % version)
    extract = work / ("v" + version)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract)
    root = extract / "aix-style-library"
    p = PROBES[version]
    search_req = {"api_version": "1.0", "operation": "search", "query": p["term"],
                  "terms": [p["term"]], "category": None, "limit": 3}
    sp = work / ("search-%s.json" % version)
    sp.write_text(json.dumps(search_req, ensure_ascii=False), encoding="utf-8")
    prepare_req = {"api_version": "1.0", "operation": "prepare", "style_id": p["sid"],
                   "style_version": None, "mode": "prompt", "target": "generic-text-v1",
                   "strength": "balanced",
                   "intent": {"description": "一台咖啡机，纯白背景。", "aspect_ratio": "9:16",
                              "text_literals": [], "must_preserve": ["纯白背景"]},
                   "resolution": {"exclude_features": [], "exclude_avoid": []}}
    pp = work / ("prepare-%s.json" % version)
    pp.write_text(json.dumps(prepare_req, ensure_ascii=False), encoding="utf-8")
    records = []
    for args, expect in ((["get", "--id", p["sid"]], "resolved"),
                         (["search", "--input", str(sp)], "candidates"),
                         (["prepare", "--input", str(pp)], "prepared")):
        res = run_cli(root, args)
        records.append({"library_version": version, "operation": args[0],
                        "code": res["code"], "stage": res["stage"],
                        "expect": expect, "ok": res["code"] == "OK" and res["stage"] == expect,
                        "stderr": res.get("stderr")})
    return records


def main():
    with tempfile.TemporaryDirectory(prefix="aix-drill-") as tmp:
        work = Path(tmp)
        checks = []
        for version in SEQUENCE:
            checks.extend(probe_version(version, work))

        # 包与源一致：0.3.2 解包内容逐字节等于开发库（含重建索引）
        new_zip = RELEASES / "aix-style-library-0.3.2.zip"
        extract = work / "src-compare"
        with zipfile.ZipFile(new_zip) as z:
            z.extractall(extract)
        packaged = extract / "aix-style-library"
        mismatches = []
        for f in sorted(packaged.rglob("*")):
            if f.is_file():
                rel = f.relative_to(packaged)
                src = SKILL_SRC / rel
                if not src.is_file():
                    mismatches.append("缺源文件: %s" % rel)
                elif src.read_bytes() != f.read_bytes():
                    mismatches.append("内容不一致: %s" % rel)
        ignored = lambda p: (p.name == ".DS_Store" or p.suffix in (".pyc", ".pyo")
                             or "__pycache__" in p.parts)
        extra = [str(p.relative_to(SKILL_SRC)) for p in SKILL_SRC.rglob("*")
                 if p.is_file() and not (packaged / p.relative_to(SKILL_SRC)).is_file()
                 and not ignored(p)]
        archive_matches_source = not mismatches and not extra
        file_count = sum(1 for f in packaged.rglob("*") if f.is_file())

        # 旧包校验和完好
        old_zip = RELEASES / "aix-style-library-0.2.0.zip"
        old_sha_file = RELEASES / "aix-style-library-0.2.0.zip.sha256"
        recorded = old_sha_file.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(old_zip.read_bytes()).hexdigest()
        old_ok = recorded == actual

    report = {
        "date": "2026-09-20",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "sequence": SEQUENCE,
        "checks": checks,
        "new_archive_file_count": file_count,
        "archive_matches_source": archive_matches_source,
        "archive_mismatches": mismatches[:10],
        "skill_extra_files": extra[:10],
        "old_archive_checksum_matches": old_ok,
    }
    with open(OUT / "package-rollback.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    all_ok = all(c["ok"] for c in checks) and archive_matches_source and old_ok
    print("演练序列:", " → ".join(SEQUENCE))
    for c in checks:
        print("%s %-8s %s" % (c["library_version"], c["operation"], "OK" if c["ok"] else "FAIL"))
    print("包文件数:", file_count, "| 包与源一致:", archive_matches_source, "| 旧包校验和:", old_ok)
    print("总判定:", "全通过 ✓" if all_ok else "存在问题 ✗")


if __name__ == "__main__":
    main()
