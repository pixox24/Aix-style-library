#!/usr/bin/env python3
"""Aix Style Library deterministic CLI.

Subcommands: get, search, prepare, validate, build-index.

Runtime (get/search/prepare/build-index) depends only on the Python standard
library. Full ``validate --scope release`` may additionally use jsonschema and
Pillow when available; it degrades with an actionable message otherwise.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata

API_VERSION = "1.0"
SCHEMA_VERSION = "1.0"
CATEGORIES = ("illustration", "painting", "photographic", "3d", "graphic")
AXES = ("medium", "line", "palette", "lighting", "texture", "composition")
TIERS = ("core", "support", "accent")
STATUSES = ("draft", "active", "deprecated")
SOURCE_TYPES = ("original", "licensed", "public_domain", "unknown")
COMMERCIAL = ("allowed", "restricted", "unknown")
REVIEW_STATUS = ("pending", "passed", "failed")
STRENGTHS = ("light", "balanced", "strong")
MODES = ("prompt", "generate")
TARGETS = ("generic-text-v1",)
OPERATIONS = ("get", "search", "prepare", "validate", "build-index")

ID_NUM_RE = re.compile(r"^(?:[Aa][Ii][Xx]-?)?([0-9]+)$")
CANON_RE = re.compile(r"^Aix(?:[0-9]{4}|[1-9][0-9]{4,7})$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
FEATURE_ID_RE = re.compile(r"^F[0-9]{2}$")
AVOID_ID_RE = re.compile(r"^N[0-9]{2}$")
RATIO_RE = re.compile(r"^\s*([0-9]{1,3})\s*:\s*([0-9]{1,3})\s*$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

EXIT_CODES = {
    "OK": 0,
    "INVALID_REQUEST": 2,
    "INVALID_STYLE_ID": 2,
    "STYLE_NOT_FOUND": 3,
    "STYLE_NOT_ACTIVE": 3,
    "STYLE_DEPRECATED": 3,
    "STYLE_VERSION_UNAVAILABLE": 3,
    "STYLE_INVALID": 4,
    "ASSET_MISSING": 4,
    "PATH_OUTSIDE_LIBRARY": 4,
    "SCHEMA_UNSUPPORTED": 4,
    "INDEX_MISSING": 4,
    "INDEX_STALE": 4,
    "STYLE_NOT_APPLICABLE": 5,
    "TARGET_UNSUPPORTED": 5,
    "INTERNAL_ERROR": 6,
}

STYLE_KEYS = {
    "schema_version", "id", "version", "status", "name", "description",
    "category", "tags", "aliases", "thumbnail", "features", "avoid",
    "suitable_for", "weak_for", "known_failures", "provenance", "quality",
    "replacement_id",
}
THUMB_KEYS = {"path", "media_type", "alt"}
FEATURE_KEYS = {"id", "axis", "tier", "text"}
AVOID_KEYS = {"id", "text"}
PROV_KEYS = {"source_type", "source_ref", "license_ref", "commercial_use", "attribution"}
QUALITY_KEYS = {"review_status", "tested_tool", "tested_at", "evidence_ref"}
SEARCH_KEYS = {"api_version", "operation", "query", "terms", "category", "limit"}
PREPARE_KEYS = {
    "api_version", "operation", "style_id", "style_version", "mode", "target",
    "strength", "intent", "resolution",
}
INTENT_KEYS = {"description", "aspect_ratio", "text_literals", "must_preserve"}
RESOLUTION_KEYS = {"exclude_features", "exclude_avoid"}
EXCLUDE_KEYS = {"id", "reason"}

REQUEST_LIMIT_BYTES = 64 * 1024


class AixError(Exception):
    def __init__(self, code, message, related_ids=None, warnings=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.related_ids = list(related_ids or [])
        self.warnings = list(warnings or [])

    @property
    def exit_code(self):
        return EXIT_CODES.get(self.code, 6)


# --------------------------------------------------------------------------
# JSON loading
# --------------------------------------------------------------------------

def _no_dup_pairs(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key: %s" % key)
        seen[key] = value
    return seen


def _reject_constant(name):
    raise ValueError("invalid JSON constant: %s" % name)


def parse_json_bytes(raw, code, label):
    if raw.startswith(codecs.BOM_UTF8):
        raise AixError(code, "%s 含 UTF-8 BOM，协议禁止。" % label)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise AixError(code, "%s 不是有效的 UTF-8。" % label)
    try:
        return json.loads(text, object_pairs_hook=_no_dup_pairs, parse_constant=_reject_constant)
    except ValueError as exc:
        raise AixError(code, "%s 不是合法 JSON：%s" % (label, exc))


def load_json_file(path, code="STYLE_INVALID", label=None):
    path = os.fspath(path)
    label = label or os.path.basename(path)
    if not os.path.isfile(path):
        raise AixError(code, "文件不存在：%s" % label)
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise AixError(code, "无法读取 %s：%s" % (label, exc))
    return parse_json_bytes(raw, code, label)


def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

def default_skill_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _real(path):
    return os.path.realpath(os.path.abspath(path))


def _is_within(base, candidate):
    return candidate == base or candidate.startswith(base + os.sep)


def safe_child(root, *parts):
    root = _real(root)
    resolved = _real(os.path.join(root, *parts))
    if not _is_within(root, resolved):
        raise AixError("PATH_OUTSIDE_LIBRARY", "解析后的路径位于风格库之外，已拒绝。")
    return resolved


def library_version(root):
    lib = os.path.join(_real(root), "library.json")
    if not os.path.isfile(lib):
        return None
    try:
        data = load_json_file(lib, code="SCHEMA_UNSUPPORTED", label="library.json")
    except AixError:
        return None
    value = data.get("library_version")
    return value if isinstance(value, str) else None


# --------------------------------------------------------------------------
# ID normalization (PRD section 10.1)
# --------------------------------------------------------------------------

def normalize_style_id(raw):
    if not isinstance(raw, str):
        raise AixError("INVALID_STYLE_ID", "风格编号必须是字符串。")
    normalized = unicodedata.normalize("NFKC", raw).strip()
    match = ID_NUM_RE.fullmatch(normalized)
    if not match:
        raise AixError(
            "INVALID_STYLE_ID",
            "无法识别的风格编号：%r。请核对编号；不会自动改用其他编号。" % raw,
        )
    digits = match.group(1)
    if not digits.isascii() or not (1 <= len(digits) <= 8):
        raise AixError("INVALID_STYLE_ID", "风格编号数字部分长度必须在 1～8 位之间。")
    number = int(digits)
    if number == 0 or number > 99999999:
        raise AixError("INVALID_STYLE_ID", "风格编号数值必须在 1～99,999,999 之间。")
    return "Aix%04d" % number


def is_canonical_id(value):
    return bool(CANON_RE.fullmatch(value)) and value != "Aix0000"


# --------------------------------------------------------------------------
# Style validation (PRD sections 6 and 10)
# --------------------------------------------------------------------------

def _fail(msg, code="STYLE_INVALID"):
    raise AixError(code, msg)


def _check_str(value, lo, hi, label, code="STYLE_INVALID"):
    if not isinstance(value, str):
        _fail("%s 必须是字符串。" % label, code)
    if not (lo <= len(value) <= hi):
        _fail("%s 长度必须在 %d～%d 字符之间。" % (label, lo, hi), code)
    return value


def _check_str_list(value, lo_count, hi_count, lo_len, hi_len, label, code="STYLE_INVALID"):
    if not isinstance(value, list):
        _fail("%s 必须是数组。" % label, code)
    if not (lo_count <= len(value) <= hi_count):
        _fail("%s 数量必须在 %d～%d 之间。" % (label, lo_count, hi_count), code)
    seen = set()
    for item in value:
        _check_str(item, lo_len, hi_len, label + " 的项", code)
        if item in seen:
            _fail("%s 不允许重复项：%r。" % (label, item), code)
        seen.add(item)
    return value


def _check_keys(obj, allowed, label, code):
    if not isinstance(obj, dict):
        _fail("%s 必须是对象。" % label, code)
    unknown = set(obj) - allowed
    if unknown:
        _fail("%s 含未知字段：%s。" % (label, ", ".join(sorted(unknown))), code)


def validate_style_obj(obj, sid):
    _check_keys(obj, STYLE_KEYS, "style.json", "SCHEMA_UNSUPPORTED")
    if obj.get("schema_version") != SCHEMA_VERSION:
        _fail("不支持的 style schema_version：%r。" % obj.get("schema_version"), "SCHEMA_UNSUPPORTED")
    if obj.get("id") != sid:
        _fail("style.json 的 id 与父目录不一致：%r != %r。" % (obj.get("id"), sid))
    if not is_canonical_id(sid):
        _fail("目录名不是规范 ID：%r。" % sid)
    version = obj.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        _fail("version 必须是三段非负整数，如 1.0.0。")
    if obj.get("status") not in STATUSES:
        _fail("status 非法：%r。" % obj.get("status"))
    _check_str(obj.get("name"), 1, 60, "name")
    _check_str(obj.get("description"), 1, 240, "description")
    if obj.get("category") not in CATEGORIES:
        _fail("category 非法：%r。" % obj.get("category"))
    _check_str_list(obj.get("tags"), 1, 12, 1, 24, "tags")
    aliases = _check_str_list(obj.get("aliases"), 0, 8, 1, 60, "aliases")
    for alias in aliases:
        try:
            normalize_style_id(alias)
        except AixError:
            continue
        _fail("aliases 不得占用他人的规范 ID：%r。" % alias)

    thumb = obj.get("thumbnail")
    _check_keys(thumb, THUMB_KEYS, "thumbnail", "STYLE_INVALID")
    if thumb.get("path") != "thumbnail.webp":
        _fail("thumbnail.path 必须固定为 thumbnail.webp。")
    if thumb.get("media_type") != "image/webp":
        _fail("thumbnail.media_type 必须固定为 image/webp。")
    _check_str(thumb.get("alt"), 1, 180, "thumbnail.alt")

    features = obj.get("features")
    if not isinstance(features, list) or not (2 <= len(features) <= 10):
        _fail("features 必须是 2～10 个元素的数组。")
    seen_fids = set()
    has_core = False
    for feature in features:
        _check_keys(feature, FEATURE_KEYS, "features 元素", "STYLE_INVALID")
        fid = feature.get("id")
        if not isinstance(fid, str) or not FEATURE_ID_RE.fullmatch(fid):
            _fail("features.id 必须是 F 加两位数字，如 F01。")
        if fid in seen_fids:
            _fail("features.id 重复：%s。" % fid)
        seen_fids.add(fid)
        if feature.get("axis") not in AXES:
            _fail("features.axis 非法：%r。" % feature.get("axis"))
        if feature.get("tier") not in TIERS:
            _fail("features.tier 非法：%r。" % feature.get("tier"))
        _check_str(feature.get("text"), 1, 240, "features.text")
        if feature.get("tier") == "core":
            has_core = True
    if not has_core:
        _fail("features 至少需要一个 core 组件。")

    avoid = obj.get("avoid")
    if not isinstance(avoid, list) or not (0 <= len(avoid) <= 8):
        _fail("avoid 必须是 0～8 个元素的数组。")
    seen_nids = set()
    for item in avoid:
        _check_keys(item, AVOID_KEYS, "avoid 元素", "STYLE_INVALID")
        nid = item.get("id")
        if not isinstance(nid, str) or not AVOID_ID_RE.fullmatch(nid):
            _fail("avoid.id 必须是 N 加两位数字，如 N01。")
        if nid in seen_nids:
            _fail("avoid.id 重复：%s。" % nid)
        seen_nids.add(nid)
        _check_str(item.get("text"), 1, 160, "avoid.text")

    _check_str_list(obj.get("suitable_for"), 1, 6, 1, 80, "suitable_for")
    _check_str_list(obj.get("weak_for"), 0, 6, 1, 80, "weak_for")
    _check_str_list(obj.get("known_failures"), 0, 6, 1, 200, "known_failures")

    prov = obj.get("provenance")
    _check_keys(prov, PROV_KEYS, "provenance", "STYLE_INVALID")
    if prov.get("source_type") not in SOURCE_TYPES:
        _fail("provenance.source_type 非法。")
    if prov.get("commercial_use") not in COMMERCIAL:
        _fail("provenance.commercial_use 非法。")
    for key in ("source_ref", "license_ref", "attribution"):
        value = prov.get(key)
        if value is not None and not isinstance(value, str):
            _fail("provenance.%s 必须是字符串或 null。" % key)

    quality = obj.get("quality")
    _check_keys(quality, QUALITY_KEYS, "quality", "STYLE_INVALID")
    if quality.get("review_status") not in REVIEW_STATUS:
        _fail("quality.review_status 非法。")
    tested_at = quality.get("tested_at")
    if tested_at is not None and not (isinstance(tested_at, str) and DATE_RE.fullmatch(tested_at)):
        _fail("quality.tested_at 必须是 YYYY-MM-DD 或 null。")
    for key in ("tested_tool", "evidence_ref"):
        value = quality.get(key)
        if value is not None and not isinstance(value, str):
            _fail("quality.%s 必须是字符串或 null。" % key)

    if obj.get("status") == "active":
        if prov.get("source_ref") is None or prov.get("license_ref") is None:
            _fail("active 风格必须提供 provenance.source_ref 与 license_ref。")
        if quality.get("review_status") != "passed":
            _fail("active 风格要求 quality.review_status=passed。")
        for key in ("tested_tool", "tested_at", "evidence_ref"):
            if quality.get(key) is None:
                _fail("active 风格要求 quality.%s 非空。" % key)

    replacement = obj.get("replacement_id")
    if replacement is not None:
        if not isinstance(replacement, str) or not is_canonical_id(replacement):
            _fail("replacement_id 必须是规范 ID 或 null。")
        if replacement == sid:
            _fail("replacement_id 不允许自指。")
    return obj


def read_style(root, sid):
    _, style_file, thumb_file = style_paths(root, sid)
    if not os.path.isfile(style_file):
        raise AixError("STYLE_NOT_FOUND", "风格 %s 不存在。请核对编号；不会自动改用其他风格。" % sid)
    obj = load_json_file(style_file, code="STYLE_INVALID", label="styles/%s/style.json" % sid)
    validate_style_obj(obj, sid)
    if not os.path.isfile(thumb_file):
        raise AixError("ASSET_MISSING", "风格 %s 的缩略图缺失或不存在。" % sid)
    try:
        with open(thumb_file, "rb") as handle:
            thumb_bytes = handle.read()
    except OSError as exc:
        raise AixError("ASSET_MISSING", "无法读取风格 %s 的缩略图：%s" % (sid, exc))
    return obj, thumb_bytes


def style_paths(root, sid):
    directory = safe_child(root, "styles", sid)
    return (
        directory,
        os.path.join(directory, "style.json"),
        os.path.join(directory, "thumbnail.webp"),
    )


def content_hash(style_obj, thumb_bytes):
    normalized = json.dumps(
        style_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(normalized)
    digest.update(b"\n")
    digest.update(thumb_bytes)
    return digest.hexdigest()


def style_content_hash(root, sid):
    obj, thumb_bytes = read_style(root, sid)
    return content_hash(obj, thumb_bytes)


# --------------------------------------------------------------------------
# Request validation
# --------------------------------------------------------------------------

def validate_request_obj(obj, operation):
    allowed = SEARCH_KEYS if operation == "search" else PREPARE_KEYS
    _check_keys(obj, allowed, "request", "INVALID_REQUEST")
    if obj.get("api_version") != API_VERSION:
        _fail("不支持的 api_version：%r。" % obj.get("api_version"), "SCHEMA_UNSUPPORTED")
    if obj.get("operation") != operation:
        _fail("request.operation 必须为 %r。" % operation, "INVALID_REQUEST")
    if operation == "search":
        _check_str(obj.get("query"), 1, 500, "query", "INVALID_REQUEST")
        _check_str_list(obj.get("terms"), 1, 8, 1, 40, "terms", "INVALID_REQUEST")
        category = obj.get("category")
        if category is not None and category not in CATEGORIES:
            _fail("category 非法。", "INVALID_REQUEST")
        limit = obj.get("limit")
        if not isinstance(limit, int) or isinstance(limit, bool) or not (1 <= limit <= 5):
            _fail("limit 必须是 1～5 的整数。", "INVALID_REQUEST")
    else:
        _check_str(obj.get("style_id"), 1, 64, "style_id", "INVALID_REQUEST")
        style_version = obj.get("style_version")
        if style_version is not None and not (isinstance(style_version, str) and VERSION_RE.fullmatch(style_version)):
            _fail("style_version 必须是三段版本或 null。", "INVALID_REQUEST")
        if obj.get("mode") not in MODES:
            _fail("mode 必须是 prompt 或 generate。", "INVALID_REQUEST")
        if obj.get("target") not in TARGETS:
            _fail("target 不受支持：%r。" % obj.get("target"), "TARGET_UNSUPPORTED")
        if obj.get("strength") not in STRENGTHS:
            _fail("strength 必须是 light/balanced/strong。", "INVALID_REQUEST")
        intent = obj.get("intent")
        _check_keys(intent, INTENT_KEYS, "intent", "INVALID_REQUEST")
        _check_str(intent.get("description"), 1, 4000, "intent.description", "INVALID_REQUEST")
        ratio = intent.get("aspect_ratio")
        if ratio is not None:
            normalize_ratio(ratio)
        _check_str_list(intent.get("text_literals"), 0, 10, 1, 200, "intent.text_literals", "INVALID_REQUEST")
        _check_str_list(intent.get("must_preserve"), 0, 12, 1, 200, "intent.must_preserve", "INVALID_REQUEST")
        resolution = obj.get("resolution")
        _check_keys(resolution, RESOLUTION_KEYS, "resolution", "INVALID_REQUEST")
        for key in ("exclude_features", "exclude_avoid"):
            items = resolution.get(key)
            if not isinstance(items, list):
                _fail("resolution.%s 必须是数组。" % key, "INVALID_REQUEST")
            seen = set()
            for item in items:
                _check_keys(item, EXCLUDE_KEYS, "resolution.%s 元素" % key, "INVALID_REQUEST")
                item_id = item.get("id")
                if not isinstance(item_id, str) or not item_id:
                    _fail("排除项 id 必须是非空字符串。", "INVALID_REQUEST")
                if item_id in seen:
                    _fail("排除项 id 重复：%s。" % item_id, "INVALID_REQUEST")
                seen.add(item_id)
                _check_str(item.get("reason"), 1, 200, "排除原因", "INVALID_REQUEST")
    return obj


def load_request(path):
    path = os.fspath(path)
    if not os.path.isfile(path):
        raise AixError("INVALID_REQUEST", "请求文件不存在：%s。" % os.path.basename(path))
    with open(path, "rb") as handle:
        raw = handle.read()
    if len(raw) > REQUEST_LIMIT_BYTES:
        raise AixError("INVALID_REQUEST", "请求文件超过 64 KiB 上限。")
    return parse_json_bytes(raw, "INVALID_REQUEST", "request")


def normalize_ratio(value):
    if not isinstance(value, str):
        _fail("aspect_ratio 必须是比例字符串或 null。", "INVALID_REQUEST")
    match = RATIO_RE.fullmatch(value)
    if not match:
        _fail("aspect_ratio 格式非法：%r。" % value, "INVALID_REQUEST")
    left, right = int(match.group(1)), int(match.group(2))
    if not (1 <= left <= 100 and 1 <= right <= 100):
        _fail("aspect_ratio 分子分母必须各在 1～100 之间。", "INVALID_REQUEST")
    divisor = math.gcd(left, right)
    return "%d:%d" % (left // divisor, right // divisor)


# --------------------------------------------------------------------------
# Search scoring (PRD section 9.4)
# --------------------------------------------------------------------------

def norm_text(value):
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def term_score(term, entry):
    name = norm_text(entry.get("name", ""))
    aliases = [norm_text(a) for a in entry.get("aliases", [])]
    tags = [norm_text(t) for t in entry.get("tags", [])]
    description = norm_text(entry.get("description", ""))
    best = 0
    if term == name or term in aliases:
        best = max(best, 10)
    if term in tags:
        best = max(best, 8)
    if term and (term in name or any(term in alias for alias in aliases)):
        best = max(best, 5)
    if term and any(term in tag for tag in tags):
        best = max(best, 4)
    if term and term in description:
        best = max(best, 1)
    return best


def score_entry(terms, entry):
    total = 0
    matched = []
    for term in terms:
        value = term_score(term, entry)
        total += value
        if value >= 4:
            matched.append(term)
    return total, matched


def build_reason(matched):
    if not matched:
        return "无有效字段命中"
    return "命中检索词：" + "、".join(matched)


# --------------------------------------------------------------------------
# Index
# --------------------------------------------------------------------------

def index_path(root):
    return safe_child(root, "catalog", "index.json")


def style_directory_ids(root):
    styles_dir = os.path.join(_real(root), "styles")
    if not os.path.isdir(styles_dir):
        return []
    ids = []
    for name in os.listdir(styles_dir):
        if not os.path.isdir(os.path.join(styles_dir, name)):
            continue
        if not is_canonical_id(name):
            _fail("styles 下存在非规范 ID 目录：%r。" % name)
        ids.append(name)
    return sorted(ids, key=lambda value: int(value[3:]))


def source_digest(entries):
    digest = hashlib.sha256()
    for entry in entries:
        line = "%s %s %s\n" % (entry["id"], entry["version"], entry["content_hash"])
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def collect_entries(root, active_only=False):
    entries = []
    for sid in style_directory_ids(root):
        obj, thumb_bytes = read_style(root, sid)
        if active_only and obj["status"] != "active":
            continue
        entries.append({
            "id": sid,
            "version": obj["version"],
            "status": obj["status"],
            "name": obj["name"],
            "description": obj["description"],
            "category": obj["category"],
            "tags": list(obj["tags"]),
            "aliases": list(obj["aliases"]),
            "thumbnail_path": "styles/%s/thumbnail.webp" % sid,
            "thumbnail_alt": obj["thumbnail"]["alt"],
            "content_hash": content_hash(obj, thumb_bytes),
        })
    return entries


def build_index_payload(root):
    entries = collect_entries(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "library_version": library_version(root),
        "source_digest": source_digest(entries),
        "styles": entries,
    }


def write_index(root, payload):
    import tempfile

    target = index_path(root)
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=parent, prefix="index.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(dump_json(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_get(root, sid_raw, version):
    sid = normalize_style_id(sid_raw)
    obj, thumb_bytes = read_style(root, sid)
    if version is not None and obj["version"] != version:
        raise AixError(
            "STYLE_VERSION_UNAVAILABLE",
            "风格 %s 的版本 %s 不在当前包内（可用版本 %s）。不会静默使用最新版本。"
            % (sid, version, obj["version"]),
        )
    status = obj["status"]
    if status == "draft":
        raise AixError("STYLE_NOT_ACTIVE", "风格 %s 尚未发布（draft），不用于普通调用。" % sid)
    if status == "deprecated":
        warnings = []
        if obj.get("replacement_id"):
            replacement = obj["replacement_id"]
            warnings.append({
                "code": "REPLACEMENT_SUGGESTED",
                "message": "风格 %s 已弃用，已登记替代 %s，仅供参考，仍需你确认。" % (sid, replacement),
                "related_ids": [replacement],
            })
        raise AixError("STYLE_DEPRECATED", "风格 %s 已弃用。" % sid, warnings=warnings)
    data = {
        "stage": "resolved",
        "style": obj,
        "thumbnail_path": "styles/%s/thumbnail.webp" % sid,
        "provenance": {
            "style_id": sid,
            "style_version": obj["version"],
            "library_version": library_version(root),
            "content_hash": content_hash(obj, thumb_bytes),
        },
    }
    return data, []


def cmd_search(root, request_path):
    request = validate_request_obj(load_request(request_path), "search")
    idx_file = index_path(root)
    if not os.path.isfile(idx_file):
        raise AixError("INDEX_MISSING", "搜索索引缺失，请由维护者运行 build-index。")
    index = load_json_file(idx_file, code="INDEX_MISSING", label="catalog/index.json")
    if index.get("schema_version") != SCHEMA_VERSION:
        raise AixError("SCHEMA_UNSUPPORTED", "索引 schema_version 不受支持。")

    terms = []
    for term in request["terms"]:
        normalized = norm_text(term)
        if normalized and normalized not in terms:
            terms.append(normalized)

    scored = []
    for entry in index.get("styles", []):
        if entry.get("status") != "active":
            continue
        if request.get("category") and entry.get("category") != request["category"]:
            continue
        total, matched = score_entry(terms, entry)
        if not matched:
            continue
        scored.append((entry, total, matched))
    scored.sort(key=lambda item: (-item[1], -len(item[2]), int(item[0]["id"][3:])))

    candidates = []
    for entry, total, matched in scored:
        sid = entry["id"]
        try:
            obj, thumb_bytes = read_style(root, sid)
        except AixError as exc:
            raise AixError("INDEX_STALE", "索引候选 %s 与源文件不一致：%s。" % (sid, exc.message))
        actual = content_hash(obj, thumb_bytes)
        if (obj["version"] != entry.get("version") or obj["status"] != entry.get("status")
                or actual != entry.get("content_hash")):
            raise AixError("INDEX_STALE", "索引候选 %s 已陈旧，请维护者重建索引。" % sid)
        candidates.append({
            "id": sid,
            "version": obj["version"],
            "name": obj["name"],
            "description": obj["description"],
            "thumbnail_path": "styles/%s/thumbnail.webp" % sid,
            "thumbnail_alt": obj["thumbnail"]["alt"],
            "matched_terms": matched,
            "score": total,
            "reason": build_reason(matched),
        })
        if len(candidates) >= request["limit"]:
            break

    data = {
        "stage": "candidates",
        "query": request["query"],
        "candidates": candidates,
    }
    return data, []


def cmd_prepare(root, request_path):
    request = validate_request_obj(load_request(request_path), "prepare")
    sid = normalize_style_id(request["style_id"])
    obj, thumb_bytes = read_style(root, sid)
    if request.get("style_version") is not None and obj["version"] != request["style_version"]:
        raise AixError(
            "STYLE_VERSION_UNAVAILABLE",
            "风格 %s 的版本 %s 不在当前包内（可用版本 %s）。" % (sid, request["style_version"], obj["version"]),
        )
    if obj["status"] != "active":
        if obj["status"] == "draft":
            raise AixError("STYLE_NOT_ACTIVE", "风格 %s 尚未发布（draft）。" % sid)
        raise AixError("STYLE_DEPRECATED", "风格 %s 已弃用。" % sid)

    strength = request["strength"]
    tier_set = {
        "light": {"core"},
        "balanced": {"core", "support"},
        "strong": {"core", "support", "accent"},
    }[strength]

    features = [f for f in obj["features"] if f["tier"] in tier_set]
    selected_ids = {f["id"] for f in features}
    warnings = []

    exclude_features = request["resolution"]["exclude_features"]
    omitted_features = []
    for item in exclude_features:
        if item["id"] not in selected_ids:
            raise AixError(
                "INVALID_REQUEST",
                "exclude_features 只能排除当前强度会选中的组件：%s。" % item["id"],
            )
        omitted_features.append({"id": item["id"], "reason": item["reason"]})
    omitted_feature_ids = {item["id"] for item in omitted_features}
    features = [f for f in features if f["id"] not in omitted_feature_ids]
    if not any(f["tier"] == "core" for f in features):
        raise AixError(
            "STYLE_NOT_APPLICABLE",
            "风格 %s 的所有核心组件均被排除，无法代表该风格；请修改要求或另选风格。" % sid,
        )
    if omitted_features:
        warnings.append({
            "code": "STYLE_ADJUSTED",
            "message": "为保留用户明确要求，省略了风格组件：" + "、".join(item["id"] for item in omitted_features) + "。",
            "related_ids": [sid],
        })

    avoid_ids = {item["id"] for item in obj["avoid"]}
    omitted_avoid = []
    for item in request["resolution"]["exclude_avoid"]:
        if item["id"] not in avoid_ids:
            raise AixError("INVALID_REQUEST", "exclude_avoid 引用了不存在的避用项：%s。" % item["id"])
        omitted_avoid.append({"id": item["id"], "reason": item["reason"]})
    omitted_avoid_ids = {item["id"] for item in omitted_avoid}
    kept_avoid = [item for item in obj["avoid"] if item["id"] not in omitted_avoid_ids]
    if omitted_avoid:
        warnings.append({
            "code": "NEGATIVE_ADJUSTED",
            "message": "为保留用户明确要求，省略了避用建议：" + "、".join(item["id"] for item in omitted_avoid) + "。",
            "related_ids": [sid],
        })

    intent = request["intent"]
    ratio = normalize_ratio(intent["aspect_ratio"]) if intent["aspect_ratio"] is not None else None

    paragraphs = ["画面内容：%s" % intent["description"]]
    if intent["must_preserve"]:
        paragraphs.append("必须保留：" + "；".join(intent["must_preserve"]))
    if intent["text_literals"]:
        paragraphs.append("画面中的文字（逐字）：" + "；".join(intent["text_literals"]))
    if features:
        paragraphs.append("视觉风格：" + "；".join(f["text"] for f in features))
    if ratio is not None:
        paragraphs.append("画幅比例：%s" % ratio)
    if kept_avoid:
        paragraphs.append("避免出现：" + "；".join(item["text"] for item in kept_avoid))
    final_prompt = "\n".join(paragraphs)

    data = {
        "stage": "prepared",
        "style_id": sid,
        "style_name": obj["name"],
        "style_version": obj["version"],
        "thumbnail_path": "styles/%s/thumbnail.webp" % sid,
        "target": request["target"],
        "mode": request["mode"],
        "strength": strength,
        "final_prompt": final_prompt,
        "negative_prompt": None,
        "requested_parameters": {"aspect_ratio": ratio},
        "tool_parameters": {},
        "applied_feature_ids": [f["id"] for f in features],
        "omitted_features": omitted_features,
        "omitted_avoid": omitted_avoid,
        "provenance": {
            "style_id": sid,
            "style_version": obj["version"],
            "library_version": library_version(root),
            "content_hash": content_hash(obj, thumb_bytes),
        },
    }
    return data, warnings


def cmd_validate(root, scope, evidence_root, baseline):
    entries = collect_entries(root)
    active = [entry for entry in entries if entry["status"] == "active"]
    if scope == "release":
        _validate_release(root, active, evidence_root, baseline)
    data = {
        "scope": scope,
        "checked_styles": len(entries),
        "checked_assets": sum(
            1 for sid in style_directory_ids(root)
            if os.path.isfile(os.path.join(root, "styles", sid, "thumbnail.webp"))
        ),
        "active_styles": len(active),
        "source_digest": source_digest(entries),
    }
    return data, []


def _resolve_within(base, relative, label):
    resolved = _real(os.path.join(base, relative))
    if not _is_within(base, resolved):
        _fail("%s 逃逸出评测根目录。" % label)
    return resolved


def _validate_release(root, active, evidence_root, baseline):
    if not evidence_root:
        raise AixError("INVALID_REQUEST", "release 校验需要 --evidence-root。")
    evidence_root = _real(evidence_root)
    if not os.path.isdir(evidence_root):
        raise AixError("INVALID_REQUEST", "evidence-root 不存在或不是目录。")

    for entry in active:
        sid = entry["id"]
        obj, _ = read_style(root, sid)
        prov = obj["provenance"]
        if prov["commercial_use"] != "allowed":
            _fail("release 要求 active 风格 %s 的 commercial_use=allowed。" % sid)
        evidence_ref = obj["quality"]["evidence_ref"]
        resolved = _resolve_within(evidence_root, evidence_ref, "风格 %s 的 evidence_ref" % sid)
        if not os.path.isfile(resolved):
            _fail("风格 %s 的评测记录不存在：%s。" % (sid, evidence_ref))
        record = load_json_file(resolved, code="STYLE_INVALID", label=evidence_ref)
        required = {
            "style_id", "style_version", "tested_tool", "tested_at", "reviewer",
            "review_mode", "rights_record", "samples", "versatility_score",
        }
        missing = required - set(record)
        if missing:
            _fail("风格 %s 的评测记录缺少字段：%s。" % (sid, ", ".join(sorted(missing))))
        if record["style_id"] != sid or record["style_version"] != obj["version"]:
            _fail("风格 %s 的评测记录与当前版本不一致。" % sid)
        if record["review_mode"] not in ("independent", "self_blind"):
            _fail("风格 %s 的 review_mode 非法。" % sid)
        if not (isinstance(record["versatility_score"], int) and 1 <= record["versatility_score"] <= 5):
            _fail("风格 %s 的 versatility_score 必须是 1～5 整数。" % sid)
        rights = _resolve_within(evidence_root, record["rights_record"], "风格 %s 的 rights_record" % sid)
        if not os.path.isfile(rights):
            _fail("风格 %s 的 rights_record 不存在。" % sid)
        if not isinstance(record["samples"], list) or len(record["samples"]) < 6:
            _fail("风格 %s 至少需要 6 个视觉样例。" % sid)
        for sample in record["samples"]:
            sample_keys = {
                "case_id", "subject_category", "prompt", "image_path",
                "style_score", "content_score", "notes",
            }
            missing_sample = sample_keys - set(sample)
            if missing_sample:
                _fail("风格 %s 的样例缺少字段：%s。" % (sid, ", ".join(sorted(missing_sample))))
            for key in ("style_score", "content_score"):
                if not (isinstance(sample[key], int) and 1 <= sample[key] <= 5):
                    _fail("风格 %s 的样例 %s 分数必须是 1～5 整数。" % (sid, sample["case_id"]))
            image = _resolve_within(
                evidence_root, sample["image_path"], "风格 %s 的样例图片路径" % sid
            )
            if not os.path.isfile(image):
                _fail("风格 %s 的样例图片不存在：%s。" % (sid, sample["image_path"]))

    payload = build_index_payload(root)
    idx_file = index_path(root)
    if not os.path.isfile(idx_file):
        raise AixError("INDEX_MISSING", "release 校验要求已构建索引。")
    on_disk = load_json_file(idx_file, code="INDEX_MISSING", label="catalog/index.json")
    if on_disk.get("source_digest") != payload["source_digest"]:
        raise AixError("INDEX_STALE", "索引与源文件摘要不一致，请重建索引。")
    if on_disk.get("library_version") != payload["library_version"]:
        raise AixError("INDEX_STALE", "索引 library_version 与 library.json 不一致。")

    if baseline:
        _compare_baseline(root, baseline)


def _compare_baseline(root, baseline):
    baseline_index = os.path.join(_real(baseline), "catalog", "index.json")
    if not os.path.isfile(baseline_index):
        raise AixError("INVALID_REQUEST", "baseline 目录缺少 catalog/index.json。")
    old = load_json_file(baseline_index, code="INVALID_REQUEST", label="baseline index")
    old_map = {entry["id"]: entry for entry in old.get("styles", [])}
    for entry in collect_entries(root):
        previous = old_map.get(entry["id"])
        if previous is None:
            continue
        if previous["version"] != entry["version"] and _version_less(entry["version"], previous["version"]):
            _fail("风格 %s 版本回退：%s -> %s。" % (entry["id"], previous["version"], entry["version"]))
        if previous["version"] == entry["version"] and previous["content_hash"] != entry["content_hash"]:
            _fail("风格 %s 在同版本下内容被覆盖。" % entry["id"])
    for sid in old_map:
        if sid not in {entry["id"] for entry in collect_entries(root)}:
            _fail("已发布风格 %s 在新包中消失。" % sid)


def _version_less(left, right):
    return tuple(int(part) for part in left.split(".")) < tuple(int(part) for part in right.split("."))


def cmd_build_index(root):
    payload = build_index_payload(root)
    write_index(root, payload)
    data = {
        "indexed_styles": len(payload["styles"]),
        "source_digest": payload["source_digest"],
        "catalog_path": "catalog/index.json",
    }
    return data, []


# --------------------------------------------------------------------------
# Envelope / CLI
# --------------------------------------------------------------------------

def make_envelope(operation, status, code, message, data, warnings, mode, elapsed_ms, lib_version):
    return {
        "api_version": API_VERSION,
        "operation": operation,
        "status": status,
        "code": code,
        "message": message,
        "data": data,
        "warnings": warnings,
        "meta": {
            "library_version": lib_version,
            "execution_mode": mode,
            "elapsed_ms": elapsed_ms,
        },
    }


def _parse_options(argv, allowed, required):
    values = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if not token.startswith("--") or len(token) == 2:
            raise AixError("INVALID_REQUEST", "无法识别的参数：%s。" % token)
        if "=" in token:
            key, value = token[2:].split("=", 1)
        else:
            key = token[2:]
            if index + 1 >= len(argv):
                raise AixError("INVALID_REQUEST", "参数 --%s 缺少取值。" % key)
            value = argv[index + 1]
            index += 1
        if key not in allowed:
            raise AixError("INVALID_REQUEST", "未知参数：--%s。" % key)
        values[key] = value
        index += 1
    for key in required:
        if key not in values:
            raise AixError("INVALID_REQUEST", "缺少必需参数 --%s。" % key)
    return values


def run(argv, root=None):
    root = root if root is not None else default_skill_root()
    start = time.perf_counter()
    operation = argv[0] if argv else None

    def finish(status, code, message, data, warnings):
        elapsed = int(round((time.perf_counter() - start) * 1000))
        return make_envelope(
            operation or "unknown", status, code, message, data, warnings,
            "script", elapsed, library_version(root),
        ), EXIT_CODES.get(code, 6)

    if not argv:
        return finish("error", "INVALID_REQUEST", "缺少子命令。", None, [])

    try:
        if operation == "get":
            options = _parse_options(argv[1:], {"id", "version"}, {"id"})
            data, warnings = cmd_get(root, options["id"], options.get("version"))
        elif operation in ("search", "prepare"):
            options = _parse_options(argv[1:], {"input"}, {"input"})
            command = cmd_search if operation == "search" else cmd_prepare
            data, warnings = command(root, options["input"])
        elif operation == "validate":
            options = _parse_options(
                argv[1:], {"scope", "evidence-root", "baseline"}, {"scope"}
            )
            scope = options["scope"]
            if scope not in ("all", "release"):
                raise AixError("INVALID_REQUEST", "--scope 必须是 all 或 release。")
            data, warnings = cmd_validate(
                root, scope, options.get("evidence-root"), options.get("baseline")
            )
        elif operation == "build-index":
            data, warnings = cmd_build_index(root)
        else:
            return finish("error", "INVALID_REQUEST", "未知子命令：%s。" % operation, None, [])
        return finish("ok", "OK", "命令成功。", data, warnings)
    except AixError as exc:
        return finish("error", exc.code, exc.message, None, exc.warnings)
    except Exception as exc:  # noqa: BLE001 - convert unexpected failures
        sys.stderr.write("aix.py internal error: %r\n" % (exc,))
        return finish("error", "INTERNAL_ERROR", "发生未预期错误，已停止。", None, [])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    envelope, exit_code = run(argv)
    sys.stdout.write(dump_json(envelope))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
