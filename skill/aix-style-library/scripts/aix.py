#!/usr/bin/env python3
"""Aix Style Library deterministic CLI.

Subcommands: get, search, prepare, validate, build-index.

Runtime (get/search/prepare/build-index) depends only on the Python standard
library. ``validate --scope release`` requires jsonschema and Pillow;
missing development dependencies fail explicitly without installing anything.
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
from datetime import date

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
    "DEPENDENCY_MISSING": 4,
    "RELEASE_NOT_READY": 4,
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
STYLE_LIMIT_BYTES = 12 * 1024
THUMB_LIMIT_BYTES = 250 * 1024
JSON_LIMIT_BYTES = 32 * 1024 * 1024
INDEX_KEYS = {"schema_version", "library_version", "source_digest", "styles"}
ENTRY_KEYS = {
    "id", "version", "status", "name", "description", "category", "tags",
    "aliases", "thumbnail_path", "thumbnail_alt", "content_hash",
}


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
        result = json.loads(text, object_pairs_hook=_no_dup_pairs, parse_constant=_reject_constant)
        # Escaped lone surrogates are legal to Python's parser but cannot be
        # written as UTF-8. Reject before they can break the response envelope.
        json.dumps(result, ensure_ascii=False).encode("utf-8")
        return result
    except (ValueError, RecursionError) as exc:
        raise AixError(code, "%s 不是合法 JSON：%s" % (label, exc))


def load_json_file(path, code="STYLE_INVALID", label=None, limit=JSON_LIMIT_BYTES):
    path = os.fspath(path)
    label = label or os.path.basename(path)
    if not os.path.isfile(path):
        raise AixError(code, "文件不存在：%s" % label)
    try:
        with open(path, "rb") as handle:
            raw = handle.read(limit + 1)
    except OSError as exc:
        raise AixError(code, "无法读取 %s：%s" % (label, exc))
    if len(raw) > limit:
        raise AixError(code, "%s 超过 %d 字节上限。" % (label, limit))
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
    try:
        return os.path.normcase(os.path.commonpath([base, candidate])) == os.path.normcase(base)
    except ValueError:
        return False


def safe_child(root, *parts):
    root = _real(root)
    resolved = _real(os.path.join(root, *parts))
    if not _is_within(root, resolved):
        raise AixError("PATH_OUTSIDE_LIBRARY", "解析后的路径位于风格库之外，已拒绝。")
    return resolved


def library_version(root):
    lib = safe_child(root, "library.json")
    data = load_json_file(lib, code="SCHEMA_UNSUPPORTED", label="library.json", limit=8192)
    _check_keys(data, {"library_version", "schema_version", "api_version"},
                "library.json", "SCHEMA_UNSUPPORTED")
    value = data["library_version"]
    if not isinstance(value, str) or not VERSION_RE.fullmatch(value):
        _fail("library_version 必须是三段非负整数。", "SCHEMA_UNSUPPORTED")
    if data["schema_version"] != SCHEMA_VERSION or data["api_version"] != API_VERSION:
        _fail("library.json 的 schema/api 版本不受支持。", "SCHEMA_UNSUPPORTED")
    return value


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
    return isinstance(value, str) and bool(CANON_RE.fullmatch(value)) and value != "Aix0000"


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


def _check_keys(obj, allowed, label, code, required=None):
    if not isinstance(obj, dict):
        _fail("%s 必须是对象。" % label, code)
    unknown = set(obj) - allowed
    if unknown:
        _fail("%s 含未知字段：%s。" % (label, ", ".join(sorted(unknown))), code)
    missing = (allowed if required is None else required) - set(obj)
    if missing:
        _fail("%s 缺少字段：%s。" % (label, ", ".join(sorted(missing))), code)


def _check_date(value, label, code="STYLE_INVALID"):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        _fail("%s 必须是 YYYY-MM-DD。" % label, code)
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail("%s 不是有效日期。" % label, code)


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
    if tested_at is not None:
        _check_date(tested_at, "quality.tested_at")
    for key in ("tested_tool", "evidence_ref"):
        value = quality.get(key)
        if value is not None and not isinstance(value, str):
            _fail("quality.%s 必须是字符串或 null。" % key)

    if obj.get("status") == "active":
        for key in ("source_ref", "license_ref"):
            if not isinstance(prov[key], str) or not prov[key].strip():
                _fail("active 风格必须提供非空 provenance.%s。" % key)
        if quality.get("review_status") != "passed":
            _fail("active 风格要求 quality.review_status=passed。")
        for key in ("tested_tool", "tested_at", "evidence_ref"):
            if not isinstance(quality[key], str) or not quality[key].strip():
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
    obj = load_json_file(style_file, code="STYLE_INVALID", label="styles/%s/style.json" % sid,
                         limit=STYLE_LIMIT_BYTES)
    validate_style_obj(obj, sid)
    if not os.path.isfile(thumb_file):
        raise AixError("ASSET_MISSING", "风格 %s 的缩略图缺失或不存在。" % sid)
    try:
        with open(thumb_file, "rb") as handle:
            thumb_bytes = handle.read(THUMB_LIMIT_BYTES + 1)
    except OSError as exc:
        raise AixError("ASSET_MISSING", "无法读取风格 %s 的缩略图：%s" % (sid, exc))
    if not thumb_bytes or len(thumb_bytes) > THUMB_LIMIT_BYTES:
        _fail("风格 %s 的缩略图为空或超过 250 KiB。" % sid, "ASSET_MISSING")
    return obj, thumb_bytes


def style_paths(root, sid):
    directory = safe_child(root, "styles", sid)
    return (
        directory,
        safe_child(root, "styles", sid, "style.json"),
        safe_child(root, "styles", sid, "thumbnail.webp"),
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
    return load_json_file(path, "INVALID_REQUEST", "request", limit=REQUEST_LIMIT_BYTES)


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
    styles_dir = safe_child(root, "styles")
    if not os.path.isdir(styles_dir):
        return []
    ids = []
    for name in os.listdir(styles_dir):
        safe_child(root, "styles", name)
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
        entries.append(entry_for_style(obj, thumb_bytes))
    return entries


def entry_for_style(obj, thumb_bytes):
    sid = obj["id"]
    return {
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
    }


def build_index_payload(root):
    entries = collect_entries(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "library_version": library_version(root),
        "source_digest": source_digest(entries),
        "styles": entries,
    }


def read_index(root):
    path = index_path(root)
    if not os.path.isfile(path):
        raise AixError("INDEX_MISSING", "搜索索引缺失，请由维护者运行 build-index。")
    index = load_json_file(path, "INDEX_STALE", "catalog/index.json")
    _check_keys(index, INDEX_KEYS, "catalog", "INDEX_STALE")
    if index["schema_version"] != SCHEMA_VERSION:
        _fail("索引 schema_version 不受支持。", "SCHEMA_UNSUPPORTED")
    if index["library_version"] != library_version(root):
        _fail("索引 library_version 与源不一致。", "INDEX_STALE")
    entries = index["styles"]
    if not isinstance(entries, list):
        _fail("索引 styles 必须是数组。", "INDEX_STALE")
    ids = []
    for entry in entries:
        _check_keys(entry, ENTRY_KEYS, "索引记录", "INDEX_STALE")
        sid = entry["id"]
        if not is_canonical_id(sid):
            _fail("索引 ID 非法。", "INDEX_STALE")
        ids.append(sid)
        if not isinstance(entry["version"], str) or not VERSION_RE.fullmatch(entry["version"]):
            _fail("索引版本非法。", "INDEX_STALE")
        if entry["status"] not in STATUSES or entry["category"] not in CATEGORIES:
            _fail("索引状态或分类非法。", "INDEX_STALE")
        for key, high in (("name", 60), ("description", 240), ("thumbnail_alt", 180)):
            _check_str(entry[key], 1, high, "索引 " + key, "INDEX_STALE")
        _check_str_list(entry["tags"], 1, 12, 1, 24, "索引 tags", "INDEX_STALE")
        _check_str_list(entry["aliases"], 0, 8, 1, 60, "索引 aliases", "INDEX_STALE")
        if entry["thumbnail_path"] != "styles/%s/thumbnail.webp" % sid:
            _fail("索引 thumbnail_path 非法。", "INDEX_STALE")
        if not isinstance(entry["content_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["content_hash"]):
            _fail("索引 content_hash 非法。", "INDEX_STALE")
    if ids != sorted(set(ids), key=lambda sid: int(sid[3:])):
        _fail("索引 ID 重复或顺序非法。", "INDEX_STALE")
    if index["source_digest"] != source_digest(entries):
        _fail("索引记录与 source_digest 不一致。", "INDEX_STALE")
    # Directory names are cheap to inspect; no full source/thumbnail scan here.
    if ids != style_directory_ids(root):
        _fail("索引 ID 集合与风格目录不一致。", "INDEX_STALE")
    return index


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
    index = read_index(root)

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
            if exc.code == "PATH_OUTSIDE_LIBRARY":
                raise
            raise AixError("INDEX_STALE", "索引候选 %s 与源文件不一致：%s。" % (sid, exc.message))
        if entry_for_style(obj, thumb_bytes) != entry:
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
    index = read_index(root)
    if index != build_index_payload(root):
        _fail("索引与完整源数据不一致，请重建索引。", "INDEX_STALE")
    release_info = {}
    warnings = []
    if scope == "release":
        release_info = _validate_release(root, active, evidence_root, baseline)
        if release_info["release_profile"] == "preview":
            warnings.append({"code": "PREVIEW_ONLY", "message": "仅通过预览包校验，未认证真实出图、正式素材或 9 分验收。", "related_ids": []})
    data = {
        "scope": scope,
        "checked_styles": len(entries),
        "checked_assets": sum(
            1 for sid in style_directory_ids(root)
            if os.path.isfile(os.path.join(root, "styles", sid, "thumbnail.webp"))
        ),
        "active_styles": len(active),
        "source_digest": source_digest(entries),
        **release_info,
    }
    return data, warnings


def _resolve_within(base, relative, label):
    base = _real(base)
    if (not isinstance(relative, str) or not relative.strip() or os.path.isabs(relative)
            or "\\" in relative or ":" in relative or any(p in ("", ".", "..") for p in relative.split("/"))):
        _fail("%s 必须是规范相对路径。" % label)
    resolved = _real(os.path.join(base, relative))
    if not _is_within(base, resolved):
        _fail("%s 逃逸出评测根目录。" % label)
    return resolved


def _release_dependencies():
    try:
        from jsonschema import Draft202012Validator
        from PIL import Image
    except ImportError:
        _fail("完整发布校验需要开发依赖 jsonschema 与 Pillow；请在开发环境安装 requirements-dev.txt 后重试。",
              "DEPENDENCY_MISSING")
    return Draft202012Validator, Image


def _schema_validate(root, filename, value, validator_class):
    path = safe_child(root, "references", "schemas", filename)
    schema = load_json_file(path, "SCHEMA_UNSUPPORTED", filename)
    # Release validation is offline, including schemas supplied by the package.
    def local_refs(node):
        if isinstance(node, dict):
            for key, item in node.items():
                if key in ("$ref", "$dynamicRef") and (not isinstance(item, str) or not item.startswith("#")):
                    _fail("Schema 仅允许文件内引用。", "SCHEMA_UNSUPPORTED")
                local_refs(item)
        elif isinstance(node, list):
            for item in node:
                local_refs(item)
    local_refs(schema)
    try:
        validator_class.check_schema(schema)
    except Exception:
        _fail("无效的发布 Schema：%s。" % filename, "SCHEMA_UNSUPPORTED")
    error = next(validator_class(schema).iter_errors(value), None)
    if error is not None:
        _fail("%s 校验失败（%s）：%s。" % (filename, "/".join(map(str, error.path)), error.message))


def _check_image(path, image_module, thumbnail=False):
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", image_module.DecompressionBombWarning)
            with image_module.open(path) as image:
                if getattr(image, "n_frames", 1) != 1:
                    _fail("图片必须是静态图片：%s。" % os.path.basename(path))
                if thumbnail:
                    if image.format != "WEBP" or max(image.size) != 640 or min(image.size) < 320:
                        _fail("缩略图必须是静态 WebP，长边 640px、短边至少 320px。")
                    if os.path.getsize(path) > THUMB_LIMIT_BYTES:
                        _fail("缩略图超过 250 KiB。")
                image.verify()
            with image_module.open(path) as image:
                image.load()
                rgb = image.convert("RGB")
                # Hash decoded pixels, so re-encoding the same image cannot
                # fabricate six independent visual samples.
                digest = hashlib.sha256(str(rgb.size).encode("ascii") + rgb.tobytes()).hexdigest()
    except AixError:
        raise
    except Exception:
        _fail("图片无法安全解码：%s。" % os.path.basename(path), "ASSET_MISSING")
    return digest


def _nonempty_file(base, relative, label):
    path = _resolve_within(base, relative, label)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        _fail("%s 不存在或为空。" % label)
    return path


def _score(value, label):
    if type(value) is not int or not 1 <= value <= 5:
        _fail("%s 必须是 1～5 整数。" % label)
    return value


def _validate_release(root, active, evidence_root, baseline):
    validator_class, image_module = _release_dependencies()
    version = library_version(root)
    profile = "preview" if int(version.split(".")[0]) == 0 else "formal"
    if not evidence_root:
        raise AixError("INVALID_REQUEST", "release 校验需要 --evidence-root。")
    evidence_root = _real(evidence_root)
    if not os.path.isdir(evidence_root):
        raise AixError("INVALID_REQUEST", "evidence-root 不存在或不是目录。")
    if not active:
        _fail("发布包至少需要一个 active 风格。", "RELEASE_NOT_READY")
    entries = collect_entries(root)
    if any(entry["status"] == "draft" for entry in entries):
        _fail("发布包不能包含 draft；请先在 staging 目录组包。", "RELEASE_NOT_READY")
    if profile == "formal" and (len(active) < 20 or len({e["category"] for e in active}) < 3):
        _fail("正式版本需要至少 20 个 active 风格、覆盖至少 3 个分类。", "RELEASE_NOT_READY")
    for entry in entries:
        obj, _ = read_style(root, entry["id"])
        _schema_validate(root, "style.schema.json", obj, validator_class)
        _check_image(style_paths(root, entry["id"])[2], image_module, thumbnail=True)
        if obj["replacement_id"] is not None and obj["replacement_id"] not in {e["id"] for e in active}:
            _fail("replacement_id 必须指向包内 active 风格。")
    _schema_validate(root, "catalog.schema.json", read_index(root), validator_class)
    all_style_scores, all_content_scores = [], []
    image_digests = set()
    for entry in active:
        sid = entry["id"]
        obj, _ = read_style(root, sid)
        prov = obj["provenance"]
        if prov["commercial_use"] != "allowed" or prov["source_type"] == "unknown":
            _fail("release 要求 active 风格 %s 有已知来源且 commercial_use=allowed。" % sid)
        # Offline source URLs are declarations; the locally reviewed rights
        # record below is always required. Local references must resolve.
        source_ref = prov["source_ref"]
        if not source_ref.startswith(("https://", "http://")):
            local_source = source_ref.removeprefix("evaluation/")
            _nonempty_file(evidence_root, local_source, "source_ref")
        license_ref = prov["license_ref"].split("#", 1)[0]
        if not license_ref.startswith(("https://", "http://")):
            _nonempty_file(root, license_ref, "license_ref")
        evidence_ref = obj["quality"]["evidence_ref"]
        resolved = _nonempty_file(evidence_root, evidence_ref, "evidence_ref")
        record = load_json_file(resolved, code="STYLE_INVALID", label=evidence_ref)
        required = {
            "style_id", "style_version", "tested_tool", "tested_at", "reviewer",
            "review_mode", "rights_record", "samples", "versatility_score",
        }
        _check_keys(record, required | {"limitations", "evidence_type"}, "评测记录", "STYLE_INVALID", required)
        if record["style_id"] != sid or record["style_version"] != obj["version"]:
            _fail("风格 %s 的评测记录与当前版本不一致。" % sid)
        for key in ("tested_tool", "tested_at"):
            if record[key] != obj["quality"][key]:
                _fail("评测 %s 与风格 quality 不一致。" % key)
        _check_date(record["tested_at"], "评测 tested_at")
        for key in ("tested_tool", "reviewer"):
            _check_str(record[key], 1, 500, "评测 " + key)
            if not record[key].strip():
                _fail("评测 %s 不能为空白。" % key)
        if "limitations" in record and not isinstance(record["limitations"], str):
            _fail("limitations 必须是字符串。")
        if "evidence_type" in record and record["evidence_type"] not in ("procedural_preview", "image_model"):
            _fail("evidence_type 必须是 procedural_preview 或 image_model。")
        if record["review_mode"] not in ("independent", "self_blind"):
            _fail("review_mode 非法。")
        if record["review_mode"] == "self_blind" and not record.get("limitations", "").strip():
            _fail("self_blind 必须记录评审限制。")
        if profile == "formal" and record.get("evidence_type") != "image_model":
            _fail("正式版本需要 evidence_type=image_model 的真实生成证据。", "RELEASE_NOT_READY")
        versatility = _score(record["versatility_score"], "versatility_score")
        _nonempty_file(evidence_root, record["rights_record"], "rights_record")
        if not isinstance(record["samples"], list) or len(record["samples"]) < 6:
            _fail("风格 %s 至少需要 6 个视觉样例。" % sid)
        case_ids, image_paths = set(), set()
        categories = {"人物": 0, "物体": 0, "场景": 0}
        style_scores, content_scores = [], []
        for sample in record["samples"]:
            sample_keys = {
                "case_id", "subject_category", "prompt", "image_path",
                "style_score", "content_score", "notes",
            }
            _check_keys(sample, sample_keys | {"generation_ref"}, "视觉样例", "STYLE_INVALID", sample_keys)
            for key in ("case_id", "prompt", "notes"):
                _check_str(sample[key], 1, 12000, "样例 " + key)
                if not sample[key].strip():
                    _fail("样例 %s 不能为空白。" % key)
            if sample["case_id"] in case_ids:
                _fail("视觉样例 case_id 重复。")
            case_ids.add(sample["case_id"])
            category = sample["subject_category"]
            if not isinstance(category, str) or category not in categories:
                _fail("subject_category 必须是人物、物体或场景。")
            categories[category] += 1
            style_scores.append(_score(sample["style_score"], "style_score"))
            content_scores.append(_score(sample["content_score"], "content_score"))
            image = _nonempty_file(evidence_root, sample["image_path"], "样例图片")
            if image in image_paths:
                _fail("视觉样例 image_path 重复。")
            image_paths.add(image)
            digest = _check_image(image, image_module)
            if digest in image_digests:
                _fail("视觉样例图片内容重复，不能作为独立测试结果。")
            image_digests.add(digest)
            if profile == "formal":
                generation_path = _nonempty_file(evidence_root, sample.get("generation_ref"), "generation_ref")
                generation = load_json_file(generation_path)
                keys = {"status", "tool", "prompt", "image_sha256", "parameters"}
                _check_keys(generation, keys, "生成记录", "STYLE_INVALID")
                if (generation["status"] != "generated" or generation["tool"] != record["tested_tool"]
                        or generation["prompt"] != sample["prompt"] or not isinstance(generation["parameters"], dict)):
                    _fail("生成记录未完成或与样例不一致。", "RELEASE_NOT_READY")
                with open(image, "rb") as handle:
                    image_hash = hashlib.file_digest(handle, "sha256").hexdigest()
                if generation["image_sha256"] != image_hash:
                    _fail("生成记录与图片摘要不一致。", "RELEASE_NOT_READY")
        if min(categories.values()) < 2:
            _fail("每个风格人物、物体、场景样例分别至少 2 个。")
        if min(sum(style_scores) / len(style_scores), sum(content_scores) / len(content_scores), versatility) < 4:
            _fail("每风格的风格/内容均分及跨题材评分必须至少为 4。")
        all_style_scores.extend(style_scores)
        all_content_scores.extend(content_scores)
    if sum(s >= 4 for s in all_style_scores) / len(all_style_scores) < .9:
        _fail("全库风格一致性达标率不足 90%。")
    if sum(s >= 4 for s in all_content_scores) / len(all_content_scores) < .95:
        _fail("全库内容保留达标率不足 95%。")
    if profile == "formal":
        _validate_acceptance(root, evidence_root)
    if baseline:
        _compare_baseline(root, baseline)
    return {"release_profile": profile, "visual_samples": len(all_style_scores),
            "formal_evidence_checked": profile == "formal"}


def _validate_acceptance(root, evidence_root):
    # Human/agent judgments cannot be inferred from image metadata. Require
    # explicit, version-bound attestations with intact underlying records.
    path = _nonempty_file(evidence_root, "results/%s/acceptance.json" % library_version(root), "正式验收记录")
    record = load_json_file(path)
    _check_keys(record, {"library_version", "source_digest", "reviewer", "gates"}, "正式验收记录", "RELEASE_NOT_READY")
    if record["library_version"] != library_version(root) or record["source_digest"] != build_index_payload(root)["source_digest"]:
        _fail("正式验收记录与当前发布内容不一致。", "RELEASE_NOT_READY")
    _check_str(record["reviewer"], 1, 200, "验收人", "RELEASE_NOT_READY")
    if not record["reviewer"].strip():
        _fail("验收人不能为空白。", "RELEASE_NOT_READY")
    names = {"agent_behavior", "search", "host_tool", "portability", "rollback"}
    _check_keys(record["gates"], names, "正式验收 gates", "RELEASE_NOT_READY")
    for name, gate in record["gates"].items():
        _check_keys(gate, {"status", "record_ref", "sha256"}, name, "RELEASE_NOT_READY")
        if gate["status"] != "passed":
            _fail("正式验收项 %s 尚未通过。" % name, "RELEASE_NOT_READY")
        evidence = _nonempty_file(evidence_root, gate["record_ref"], name)
        with open(evidence, "rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != gate["sha256"]:
            _fail("正式验收项 %s 的记录摘要不一致。" % name, "RELEASE_NOT_READY")


def _compare_baseline(root, baseline):
    old = read_index(baseline)
    if old != build_index_payload(baseline):
        _fail("baseline 索引与源数据不一致。", "INDEX_STALE")
    old_map = {entry["id"]: entry for entry in old.get("styles", [])}
    current = collect_entries(root)
    if _version_less(library_version(root), library_version(baseline)):
        _fail("发布库版本不允许回退；回滚应直接恢复旧包。")
    if library_version(root) == library_version(baseline) and build_index_payload(root) != old:
        _fail("同一库版本下内容不可覆盖。")
    for entry in current:
        previous = old_map.get(entry["id"])
        if previous is None:
            continue
        if previous["version"] != entry["version"] and _version_less(entry["version"], previous["version"]):
            _fail("风格 %s 版本回退：%s -> %s。" % (entry["id"], previous["version"], entry["version"]))
        if previous["version"] == entry["version"] and previous["content_hash"] != entry["content_hash"]:
            _fail("风格 %s 在同版本下内容被覆盖。" % entry["id"])
    current_ids = {entry["id"] for entry in current}
    for sid, previous in old_map.items():
        if previous["status"] != "draft" and sid not in current_ids:
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
        if key in values:
            raise AixError("INVALID_REQUEST", "重复参数：--%s。" % key)
        values[key] = value
        index += 1
    for key in required:
        if key not in values:
            raise AixError("INVALID_REQUEST", "缺少必需参数 --%s。" % key)
    return values


def run(argv, root=None):
    root = root if root is not None else default_skill_root()
    start = time.perf_counter()
    requested_operation = argv[0] if argv else None
    operation = requested_operation if requested_operation in OPERATIONS else "unknown"
    lib_version = None

    def finish(status, code, message, data, warnings):
        elapsed = int(round((time.perf_counter() - start) * 1000))
        return make_envelope(
            operation, status, code, message, data, warnings,
            "script", elapsed, lib_version,
        ), EXIT_CODES.get(code, 6)

    if not argv:
        return finish("error", "INVALID_REQUEST", "缺少子命令。", None, [])

    try:
        lib_version = library_version(root)
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
            return finish("error", "INVALID_REQUEST", "未知子命令：%s。" % requested_operation, None, [])
        return finish("ok", "OK", "命令成功。", data, warnings)
    except AixError as exc:
        return finish("error", exc.code, exc.message, None, exc.warnings)
    except OSError as exc:
        return finish("error", "STYLE_INVALID", "资源无法访问：%s。" % exc, None, [])
    except Exception as exc:  # noqa: BLE001 - convert unexpected failures
        sys.stderr.write("aix.py internal error: %r\n" % (exc,))
        return finish("error", "INTERNAL_ERROR", "发生未预期错误，已停止。", None, [])


def main(argv=None):
    # Windows redirected streams may default to a legacy code page. The CLI
    # protocol is UTF-8 regardless of terminal locale or pipe destination.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace", newline="\n")
    argv = list(sys.argv[1:] if argv is None else argv)
    envelope, exit_code = run(argv)
    sys.stdout.write(dump_json(envelope))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
