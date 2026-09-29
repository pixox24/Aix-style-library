#!/usr/bin/env python3
"""Validate a staged runtime package, smoke-test its archive, then publish it.

Only allowlisted runtime resources are copied. Drafts and arbitrary files are
excluded, the staged index is rebuilt, and existing archives are never replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SKILL_DIR = PROJECT / "skill" / "aix-style-library"
RELEASES = PROJECT / "releases"
EVIDENCE = PROJECT / "evaluation"
RUNTIME_FILES = (
    "SKILL.md", "LICENSE.md", "library.json", "agents/openai.yaml",
    "scripts/aix.py", "references/host-tools.md", "references/protocol.md",
    "references/composition.md", "references/release.md",
    "references/schemas/style.schema.json", "references/schemas/catalog.schema.json",
    "references/schemas/request.schema.json", "references/schemas/response.schema.json",
)


def load_cli():
    spec = importlib.util.spec_from_file_location("aix_release_cli", SKILL_DIR / "scripts/aix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_call(cli, root, args):
    envelope, code = cli.run(args, root=root)
    if code:
        raise ValueError("%s: %s" % (envelope["code"], envelope["message"]))
    return envelope


def copy_runtime_file(cli, stage, relative):
    source = Path(cli.safe_child(SKILL_DIR, *relative.split("/")))
    if not source.is_file():
        raise ValueError("运行资源缺失：%s" % relative)
    target = stage / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def stage_package(cli, stage):
    for relative in RUNTIME_FILES:
        copy_runtime_file(cli, stage, relative)
    for sid in cli.style_directory_ids(SKILL_DIR):
        path = cli.safe_child(SKILL_DIR, "styles", sid, "style.json")
        obj = cli.load_json_file(path, limit=cli.STYLE_LIMIT_BYTES)
        cli.validate_style_obj(obj, sid)
        if obj["status"] == "draft":
            continue
        for name in ("style.json", "thumbnail.webp"):
            copy_runtime_file(cli, stage, "styles/%s/%s" % (sid, name))
    checked_call(cli, stage, ["build-index"])


def smoke_archive(cli, archive_path, work, evidence, baseline):
    extracted = work / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("发布 ZIP 校验失败。")
        archive.extractall(extracted)  # Archive was just built from our allowlist.
    root = extracted / "aix-style-library"
    validate = ["validate", "--scope", "release", "--evidence-root", str(evidence)]
    if baseline:
        validate += ["--baseline", str(baseline)]
    checked_call(cli, root, validate)
    script = root / "scripts/aix.py"
    entries = cli.read_index(root)["styles"]
    chosen = next(e for e in entries if e["status"] == "active")
    request = {
        "api_version": "1.0", "operation": "search", "query": chosen["name"],
        "terms": [chosen["name"][:40]], "category": None, "limit": 3,
    }
    search_path = work / "search.json"
    search_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    prepare = {
        "api_version": "1.0", "operation": "prepare", "style_id": chosen["id"],
        "style_version": chosen["version"], "mode": "prompt", "target": "generic-text-v1",
        "strength": "balanced", "intent": {"description": "一台咖啡机，纯白背景。",
        "aspect_ratio": "9:16", "text_literals": [], "must_preserve": ["纯白背景"]},
        "resolution": {"exclude_features": [], "exclude_avoid": []},
    }
    prepare_path = work / "prepare.json"
    prepare_path.write_text(json.dumps(prepare, ensure_ascii=False), encoding="utf-8")
    commands = [
        (["get", "--id", chosen["id"]], "resolved"),
        (["search", "--input", str(search_path)], "candidates"),
        (["prepare", "--input", str(prepare_path)], "prepared"),
    ]
    for args, stage in commands:
        result = subprocess.run([sys.executable, "-B", str(script), *args], cwd=work,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        if result.returncode != 0 or result.stderr:
            raise ValueError("解包后冒烟失败：%s" % args[0])
        output = json.loads(result.stdout)
        if output["data"]["stage"] != stage:
            raise ValueError("解包后阶段错误：%s" % args[0])
        if stage == "candidates" and chosen["id"] not in [c["id"] for c in output["data"]["candidates"]]:
            raise ValueError("解包后检索未命中已发布风格。")


def build(version=None, evidence_root=None, baseline=None):
    cli = load_cli()
    actual_version = cli.library_version(SKILL_DIR)
    version = actual_version if version is None else version
    if version != actual_version:
        raise ValueError("发布版本必须与 library.json 一致：%s。" % actual_version)
    evidence = Path(evidence_root or EVIDENCE).resolve()
    baseline = Path(baseline).resolve() if baseline else None
    RELEASES.mkdir(parents=True, exist_ok=True)
    target = RELEASES / ("aix-style-library-%s.zip" % version)
    checksum = target.with_suffix(".zip.sha256")
    if target.exists() or checksum.exists():
        raise ValueError("发布产物已存在，不允许覆盖：%s。请提升 library_version。" % target.name)
    with tempfile.TemporaryDirectory(prefix=".aix-stage-", dir=RELEASES) as temp:
        work = Path(temp)
        stage = work / "aix-style-library"
        stage_package(cli, stage)
        args = ["validate", "--scope", "release", "--evidence-root", str(evidence)]
        if baseline:
            args += ["--baseline", str(baseline)]
        checked_call(cli, stage, args)
        archive_path = work / target.name
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    # Stable timestamps and permissions make same-content builds reproducible.
                    info = zipfile.ZipInfo("aix-style-library/" + path.relative_to(stage).as_posix(),
                                           date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes())
        smoke_archive(cli, archive_path, work, evidence, baseline)
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        checksum_temp = work / checksum.name
        checksum_temp.write_text("%s  %s\n" % (digest, target.name), encoding="utf-8")
        # Same-filesystem hard links publish atomically and refuse overwrite,
        # including a competing build that completed after the earlier check.
        published = []
        try:
            for source, destination in ((archive_path, target), (checksum_temp, checksum)):
                os.link(source, destination)
                published.append(destination)
        except BaseException:
            for destination in published:
                destination.unlink()
            raise
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version")
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        target = build(args.version, args.evidence_root, args.baseline)
    except Exception as exc:
        print("发布失败：%s" % exc, file=sys.stderr)
        return 1
    print("release -> %s" % target)
    print("sha256  -> %s" % hashlib.sha256(target.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
