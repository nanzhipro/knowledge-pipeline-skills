"""Validate an AnyDoc batch without writing files or executing the converter."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .bundle_checks import (
    READABLE,
    SCHEMA,
    STATUSES,
    array,
    checked_file,
    digest,
    fail,
    file_hash,
    integer,
    json_bytes,
    mapping,
    portable_key,
    readable_frontmatter,
    relative,
    string,
    strings,
)


@dataclass
class Entry:
    relative_path: str
    bundle: str
    status: str
    source_sha256: str
    report: dict
    files: dict[str, Path]
    source_path: str
    markdown_path: str
    snapshot_id: str


@dataclass
class Batch:
    root: Path
    batch_id: str
    manifest: dict
    entries: list[Entry]


MANIFEST_FIELDS = {
    "schema",
    "converter_version",
    "anydoc_version",
    "created_at",
    "entries",
    "counts",
    "traversal_errors",
    "excluded",
    "index_sha256",
}
ENTRY_FIELDS = {
    "source_relative_path",
    "bundle",
    "status",
    "source_sha256",
    "report_sha256",
}
REPORT_FIELDS = {
    "schema",
    "source_relative_path",
    "source_sha256",
    "status",
    "format",
    "engine",
    "warnings",
    "ocr_pages",
    "error",
    "artifacts",
}


def _status(value: object, where: str) -> str:
    value = string(value, where)
    if value not in STATUSES:
        fail(where, f"unknown conversion status {value!r}")
    return value


def _root(path: Path) -> Path:
    try:
        path = Path(path).expanduser().absolute()
        if path.is_symlink():
            fail(str(path), "symlink input root/manifest refused")
        if path.is_file():
            if path.name != "manifest.json":
                fail(str(path), "select the batch directory or its manifest.json")
            path = path.parent
        if path.is_symlink() or not path.is_dir():
            fail(str(path), "input root must be a real directory")
        return path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        fail(str(path), f"cannot resolve input root: {exc}")


def _manifest(root: Path) -> tuple[dict, bytes]:
    path = checked_file(root, "manifest.json", "manifest.json")
    manifest, raw = json_bytes(path)
    mapping(manifest, str(path), MANIFEST_FIELDS)
    if manifest["schema"] != SCHEMA:
        fail(str(path), f"unsupported manifest schema {manifest['schema']!r}")
    for key in ("schema", "converter_version", "anydoc_version", "created_at"):
        string(manifest[key], f"manifest.{key}")
    for key in ("traversal_errors", "excluded"):
        strings(manifest[key], f"manifest.{key}")
    array(manifest["entries"], "manifest.entries")
    if type(manifest["counts"]) is not dict:
        fail("manifest.counts", "expected an object")
    for status, count in manifest["counts"].items():
        _status(status, "manifest.counts key")
        integer(count, f"manifest.counts.{status}")
    expected = digest(manifest["index_sha256"], "manifest.index_sha256")
    actual, _ = file_hash(checked_file(root, "index.md", "index.md"))
    if expected != actual:
        fail("index.md", "SHA-256 does not match manifest.index_sha256")
    return manifest, raw


def _report(root: Path, entry: dict, where: str) -> tuple[dict, Path]:
    path = checked_file(root, f"{entry['bundle']}/report.json", where + ".report")
    report, raw = json_bytes(path)
    if hashlib.sha256(raw).hexdigest() != entry["report_sha256"]:
        fail(str(path), "SHA-256 does not match manifest entry.report_sha256")
    mapping(report, str(path), REPORT_FIELDS)
    if report["schema"] != SCHEMA:
        fail(str(path), f"unsupported report schema {report['schema']!r}")
    for key in ("schema", "format", "engine"):
        string(report[key], f"{path}:{key}", empty=(key == "format"))
    relative(report["source_relative_path"], f"{path}:source_relative_path")
    digest(report["source_sha256"], f"{path}:source_sha256", empty=True)
    _status(report["status"], f"{path}:status")
    for key in ("source_relative_path", "source_sha256", "status"):
        if report[key] != entry[key]:
            fail(str(path), f"report.{key} does not match manifest entry")
    strings(report["warnings"], f"{path}:warnings")
    pages = array(report["ocr_pages"], f"{path}:ocr_pages")
    for index, page in enumerate(pages):
        integer(page, f"{path}:ocr_pages[{index}]", minimum=1)
    if len(pages) != len(set(pages)):
        fail(str(path), "duplicate OCR page numbers")
    if report["error"] is not None:
        string(report["error"], f"{path}:error", empty=True)
    if report["status"] == "converted" and report["warnings"]:
        fail(str(path), "converted report contains warnings; expected partial status")
    if report["status"] in READABLE and (report["error"] is not None or pages):
        fail(str(path), "readable report cannot contain an error or OCR pages")
    array(report["artifacts"], f"{path}:artifacts")
    return report, path


def _artifacts(root: Path, entry: dict, report: dict, path: Path) -> tuple[dict, str]:
    files, keys, sources = {"report.json": path}, {"report.json"}, []
    for index, artifact in enumerate(report["artifacts"]):
        where = f"{path}:artifacts[{index}]"
        mapping(artifact, where, {"path", "sha256", "bytes"}, {"origin", "media_type"})
        name = relative(artifact["path"], where + ".path")
        key = portable_key(name)
        if key in keys:
            fail(where, f"duplicate or case/Unicode-colliding artifact path {name!r}")
        keys.add(key)
        if name.startswith("source/"):
            if not re.fullmatch(r"source/original\.[a-z0-9]{1,12}", name):
                fail(where, "preserved source must be source/original.<safe extension>")
            sources.append(name)
        elif name != "document.md" and not name.startswith("assets/"):
            fail(
                where,
                "artifact must be document.md, source/original.<ext>, or assets/*",
            )
        for field in ("origin", "media_type"):
            if field in artifact:
                string(artifact[field], where + "." + field, empty=True)
        expected = digest(artifact["sha256"], where + ".sha256")
        size = integer(artifact["bytes"], where + ".bytes")
        artifact_path = checked_file(root, f"{entry['bundle']}/{name}", where)
        actual, length = file_hash(artifact_path)
        if actual != expected or length != size:
            fail(where, f"artifact bytes/SHA-256 mismatch for {name}")
        files[name] = artifact_path
        if name.startswith("source/") and expected != entry["source_sha256"]:
            fail(where, "preserved source SHA-256 does not match source_sha256")
    if "document.md" not in files:
        fail(str(path), "declared document.md artifact is missing")
    if len(sources) > 1 or bool(sources) != bool(entry["source_sha256"]):
        fail(
            str(path),
            "nonempty source_sha256 requires exactly one preserved source; empty hash requires none",
        )
    if report["status"] in READABLE and not sources:
        fail(str(path), "readable extraction requires a preserved original")
    return files, sources[0] if sources else ""


def load_batch(root: Path) -> Batch:
    """Return verified declared artifacts only; raise ValueError on invalid input.

    Verification establishes recorded byte integrity, not authenticity or semantic
    fidelity. A caller copying files must recheck its copied snapshot before use.
    Unlisted files, including Finder metadata, are deliberately not imported.
    """
    root = _root(root)
    manifest, raw = _manifest(root)
    entries, paths, bundles, counts = [], set(), set(), Counter()
    for index, item in enumerate(manifest["entries"]):
        where = f"manifest.entries[{index}]"
        mapping(item, where, ENTRY_FIELDS)
        source = relative(item["source_relative_path"], where + ".source_relative_path")
        bundle = relative(item["bundle"], where + ".bundle")
        if len(bundle.split("/")) != 2 or not bundle.startswith("documents/"):
            fail(where, "bundle must be an immediate child of documents/")
        key = portable_key(bundle)
        if source in paths or key in bundles:
            fail(where, "duplicate source_relative_path or colliding bundle identity")
        paths.add(source)
        bundles.add(key)
        status = _status(item["status"], where + ".status")
        digest(item["source_sha256"], where + ".source_sha256", empty=True)
        digest(item["report_sha256"], where + ".report_sha256")
        report, report_path = _report(root, item, where)
        files, source_path = _artifacts(root, item, report, report_path)
        if status in READABLE:
            readable_frontmatter(files["document.md"], report, source_path)
        canonical = dict(
            report,
            artifacts=sorted(report["artifacts"], key=lambda value: value["path"]),
        )
        identity = json.dumps(
            canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        snapshot_id = "v-" + hashlib.sha256(identity).hexdigest()[:16]
        entries.append(
            Entry(
                source,
                bundle,
                status,
                item["source_sha256"],
                report,
                files,
                source_path,
                "document.md",
                snapshot_id,
            )
        )
        counts[status] += 1
    if dict(counts) != manifest["counts"]:
        fail("manifest.counts", f"counts do not match entries: expected {dict(counts)}")
    return Batch(root, "b-" + hashlib.sha256(raw).hexdigest()[:24], manifest, entries)
