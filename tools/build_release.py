#!/usr/bin/env python3
"""Build an immutable release archive from the run package.

The archive contains only ``skill/aix-style-library/`` (the installable run
package). Development files stay in the repository. Existing archives are
never overwritten: a published version must be bumped instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SKILL_DIR = PROJECT / "skill" / "aix-style-library"
RELEASES = PROJECT / "releases"
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def library_version() -> str:
    data = json.loads((SKILL_DIR / "library.json").read_text(encoding="utf-8"))
    return data["library_version"]


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        yield path


def build(version: str) -> Path:
    RELEASES.mkdir(parents=True, exist_ok=True)
    target = RELEASES / ("aix-style-library-%s.zip" % version)
    if target.exists():
        raise SystemExit("发布包已存在，不允许覆盖：%s。请先提升 library_version。" % target.name)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in iter_files(SKILL_DIR):
            arcname = Path("aix-style-library") / path.relative_to(SKILL_DIR)
            archive.write(path, arcname.as_posix())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (RELEASES / ("aix-style-library-%s.zip.sha256" % version)).write_text(
        "%s  %s\n" % (digest, target.name), encoding="utf-8"
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=None)
    args = parser.parse_args()
    version = args.version or library_version()
    target = build(version)
    print("release -> %s" % target.relative_to(PROJECT))
    print("sha256  -> %s" % hashlib.sha256(target.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
