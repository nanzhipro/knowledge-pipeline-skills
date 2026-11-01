"""Read-only structural audit; byte integrity is not semantic verification."""

from __future__ import annotations

from datetime import date, datetime
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

import yaml

from .bundle_checks import (
    READABLE,
    SCHEMA,
    STATUSES,
    array,
    checked_file,
    digest,
    integer,
    json_bytes,
    mapping,
    portable_key,
    readable_frontmatter,
    relative,
    string,
    strings,
)
from .bundles import ENTRY_FIELDS, MANIFEST_FIELDS, _artifacts, _report
from .links import targets
from .metadata import note_issues, split_page
from .navigation import GENERATED, pages
from .paths import CONTROL, PREFS, STATE, file_hash, read_state, safe

SID = re.compile(r"s-[0-9a-f]{24}\Z")
VID = re.compile(r"v-[0-9a-f]{16}\Z")
BID = re.compile(r"b-[0-9a-f]{24}\Z")
RESERVED = re.compile(
    r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z", re.I
)
KINDS = {
    "entities": "entity",
    "concepts": "concept",
    "comparisons": "comparison",
    "synthesis": "synthesis",
    "questions": "question",
    "decisions": "decision",
}
CAUGHT = (
    OSError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    RuntimeError,
    yaml.YAMLError,
)


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _iso(value) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


class Audit:
    def __init__(self, root: Path):
        self.root = root
        self.errors, self.warnings = [], [
            "Structural checks do not verify quotes, claim support, source completeness, "
            "or factual correctness; no L3 semantic review was performed."
        ]
        self.state, self.sources, self.snapshots, self.receipts = {}, {}, {}, {}
        self.declared, self.actual_raw, self.notes, self.pending = set(), set(), {}, []

    def error(self, where: str, error: object) -> None:
        self.errors.append(f"{where}: {error}")

    def layout(self) -> None:
        for name in ("raw", "wiki"):
            _check(
                safe(self.root, name).is_dir(), f"required directory missing: {name}"
            )
        for name in (
            "SCHEMA.md",
            "AGENTS.md",
            PREFS,
            STATE,
            *sorted(GENERATED),
            "wiki/overview.md",
        ):
            checked_file(self.root, name, name)
        names = {}
        for prefix in ("raw", "wiki", CONTROL, ".llm-wiki-bootstrap"):
            folder = safe(self.root, prefix)
            if not folder.exists():
                continue
            for directory, folders, files in os.walk(folder, followlinks=False):
                for name in sorted(folders + files):
                    path = Path(directory) / name
                    location = path.relative_to(self.root).as_posix()
                    if path.is_symlink():
                        self.error(location, "symlink is not a managed artifact")
                        continue
                    key = unicodedata.normalize("NFC", location).casefold()
                    if key in names and names[key] != location:
                        self.error(
                            location, f"case/Unicode path collision with {names[key]}"
                        )
                    names[key] = location
                    if (
                        name.endswith((" ", "."))
                        or RESERVED.fullmatch(name)
                        or re.search(r'[<>:"\\|?*\x00-\x1f]', name)
                    ):
                        self.error(
                            location, "generated path is not portable on Windows"
                        )
                    if prefix == "raw" and path.is_file():
                        self.actual_raw.add(location)

    def registry(self) -> None:
        self.state = read_state(self.root)
        for key in ("sources", "collections", "batches"):
            _check(type(self.state.get(key)) is dict, f"state.{key} must be an object")
        for key in ("vault_id", "name", "domain", "language"):
            _check(
                isinstance(self.state.get(key), str) and bool(self.state[key]),
                f"state.{key} must be a nonempty string",
            )
        _check(
            type(self.state.get("revision")) is int and self.state["revision"] >= 0,
            "state.revision must be a nonnegative integer",
        )
        self.sources = self.state["sources"]
        pending = self.state.get("pending")
        _check(
            type(pending) is list and all(isinstance(item, str) for item in pending),
            "state.pending must be a list of source IDs",
        )
        _check(
            len(pending) == len(set(pending)),
            "state.pending contains duplicate source IDs",
        )
        self.pending = list(pending)
        for source_id in pending:
            _check(
                source_id in self.sources,
                f"state.pending refers to unregistered source {source_id}",
            )
        for batch_id, receipt in self.state["batches"].items():
            try:
                self.receipt(batch_id, receipt)
            except CAUGHT as exc:
                self.error(f"state.batches[{batch_id!r}]", exc)
        for source_id, record in self.sources.items():
            try:
                self.source(source_id, record)
            except CAUGHT as exc:
                self.error(f"state.sources[{source_id!r}]", exc)
        for collection, lineage in self.state["collections"].items():
            _check(
                isinstance(collection, str) and type(lineage) is dict,
                "state.collections requires named lineage objects",
            )
            for path, source_id in lineage.items():
                relative(path, f"collection {collection!r}")
                _check(
                    isinstance(source_id, str) and source_id in self.sources,
                    f"collection {collection!r}: unregistered source {source_id!r}",
                )
        if self.pending:
            self.warnings.append(
                f"Semantic compilation is pending for {len(self.pending)} registered source(s): "
                + ", ".join(self.pending)
            )
        for undeclared in sorted(self.actual_raw - self.declared):
            self.error(undeclared, "raw file is not declared by any source snapshot")

    def receipt(self, batch_id: str, receipt: dict) -> None:
        _check(
            isinstance(batch_id, str) and BID.fullmatch(batch_id), "invalid batch ID"
        )
        mapping(
            receipt,
            batch_id,
            {"collections", "rejected"},
            {"traversal_errors", "excluded"},
        )
        strings(receipt["collections"], batch_id + ".collections")
        _check(
            len(set(receipt["collections"])) == len(receipt["collections"]),
            "duplicate receipt collection",
        )
        _check(
            all(
                value and value in self.state["collections"]
                for value in receipt["collections"]
            ),
            "receipt collection is not registered",
        )
        path = checked_file(self.root, f"{CONTROL}/batches/{batch_id}.json", batch_id)
        manifest, raw = json_bytes(path)
        _check(
            batch_id == "b-" + hashlib.sha256(raw).hexdigest()[:24],
            "batch ID does not bind the original manifest bytes",
        )
        mapping(manifest, str(path), MANIFEST_FIELDS)
        _check(manifest["schema"] == SCHEMA, "unsupported receipt manifest schema")
        for key in ("converter_version", "anydoc_version", "created_at"):
            string(manifest[key], batch_id + "." + key)
        for key in ("excluded", "traversal_errors"):
            strings(manifest[key], batch_id + "." + key)
            if key in receipt:
                _check(
                    receipt[key] == manifest[key],
                    f"state receipt {key} differs from original manifest",
                )
        digest(manifest["index_sha256"], batch_id + ".index_sha256")
        seen_paths, seen_bundles, counts = set(), set(), Counter()
        for entry in array(manifest["entries"], batch_id + ".entries"):
            mapping(entry, batch_id + ".entry", ENTRY_FIELDS)
            source = relative(
                entry["source_relative_path"], batch_id + ".source_relative_path"
            )
            bundle = relative(entry["bundle"], batch_id + ".bundle")
            _check(
                bundle.startswith("documents/") and len(bundle.split("/")) == 2,
                "receipt entry has invalid bundle path",
            )
            _check(
                bundle.endswith(
                    "--" + hashlib.sha256(source.encode()).hexdigest()[:16]
                ),
                "receipt bundle identity differs from its original relative path",
            )
            _check(
                source not in seen_paths and portable_key(bundle) not in seen_bundles,
                "duplicate receipt source/bundle identity",
            )
            seen_paths.add(source)
            seen_bundles.add(portable_key(bundle))
            _check(
                isinstance(entry["status"], str) and entry["status"] in STATUSES,
                "unknown receipt conversion status",
            )
            digest(entry["source_sha256"], batch_id + ".source_sha256", empty=True)
            digest(entry["report_sha256"], batch_id + ".report_sha256")
            counts[entry["status"]] += 1
        _check(type(manifest["counts"]) is dict, "receipt counts must be an object")
        for key, value in manifest["counts"].items():
            _check(key in STATUSES, "unknown receipt count status")
            integer(value, batch_id + ".counts." + key)
        _check(
            dict(counts) == manifest["counts"], "receipt counts do not match entries"
        )
        rejected = []
        for item in array(receipt["rejected"], batch_id + ".rejected"):
            mapping(item, batch_id + ".rejected[]", {"path", "status", "error"})
            relative(item["path"], batch_id + ".rejected.path")
            _check(
                isinstance(item["status"], str)
                and item["status"] in STATUSES - READABLE,
                "rejected record requires a diagnostic status",
            )
            if item["error"] is not None:
                string(item["error"], batch_id + ".rejected.error", empty=True)
            rejected.append((item["path"], item["status"]))
        expected = [
            (entry["source_relative_path"], entry["status"])
            for entry in manifest["entries"]
            if entry["status"] not in READABLE
        ]
        _check(
            rejected == expected,
            "receipt rejected records do not match diagnostic manifest entries",
        )
        if manifest["traversal_errors"]:
            self.warnings.append(
                f"{batch_id}: input discovery had {len(manifest['traversal_errors'])} "
                "traversal error(s); collection coverage is incomplete."
            )
        self.receipts[batch_id] = manifest

    def source(self, source_id: str, record: dict) -> None:
        _check(
            isinstance(source_id, str) and SID.fullmatch(source_id), "invalid source ID"
        )
        _check(type(record) is dict, "source record must be an object")
        original = digest(record.get("source_sha256"), source_id + ".source_sha256")
        _check(
            source_id == "s-" + original[:24],
            "source ID does not match original SHA-256",
        )
        _check(isinstance(record.get("title"), str), "source title must be a string")
        snapshots = record.get("snapshots")
        _check(
            type(snapshots) is dict and snapshots,
            "source snapshots must be a nonempty object",
        )
        _check(
            isinstance(record.get("active"), str) and record["active"] in snapshots,
            "active snapshot is not registered",
        )
        for snapshot_id, snapshot in snapshots.items():
            try:
                self.snapshot(source_id, original, snapshot_id, snapshot)
            except CAUGHT as exc:
                self.error(f"{source_id}/{snapshot_id}", exc)

    def snapshot(
        self, source_id: str, original: str, snapshot_id: str, snapshot: dict
    ) -> None:
        _check(
            isinstance(snapshot_id, str) and VID.fullmatch(snapshot_id),
            "invalid snapshot ID",
        )
        _check(type(snapshot) is dict, "snapshot must be an object")
        path = relative(snapshot.get("path"), "snapshot.path")
        _check(
            path == f"raw/{source_id}/{snapshot_id}",
            "snapshot path does not match its source/snapshot IDs",
        )
        hashes = snapshot.get("files")
        _check(
            type(hashes) is dict and hashes,
            "snapshot.files must be a nonempty path-to-SHA object",
        )
        for name, expected in hashes.items():
            relative(name, path + ".files")
            digest(expected, path + "/" + name)
            location = f"{path}/{name}"
            _check(
                location not in self.declared,
                f"raw file declared by multiple snapshots: {location}",
            )
            self.declared.add(location)
            actual = checked_file(self.root, location, location)
            _check(
                file_hash(actual) == expected,
                f"state file SHA-256 mismatch: {location}",
            )
        _check("report.json" in hashes, "snapshot.files must declare report.json")
        metadata, _ = json_bytes(checked_file(self.root, path + "/report.json", path))
        entry = {
            "bundle": path,
            "source_relative_path": metadata.get("source_relative_path"),
            "status": snapshot.get("status"),
            "source_sha256": original,
            "report_sha256": hashes["report.json"],
        }
        report, report_path = _report(self.root, entry, path)
        verified, source_path = _artifacts(self.root, entry, report, report_path)
        _check(
            set(verified) == set(hashes),
            "state.files differs from the report's declared artifact inventory",
        )
        expected_artifacts = {
            item["path"]: item["sha256"] for item in report["artifacts"]
        }
        _check(
            all(hashes[name] == value for name, value in expected_artifacts.items()),
            "state.files hashes differ from report artifact hashes",
        )
        _check(
            snapshot.get("source_path") == source_path,
            "state source_path differs from the preserved-original artifact",
        )
        _check(
            snapshot.get("warnings") == report["warnings"],
            "state warnings differ from conversion report warnings",
        )
        _check(
            isinstance(snapshot.get("batch_id"), str)
            and snapshot["batch_id"] in self.state["batches"],
            "snapshot batch ID is not registered",
        )
        receipt = self.receipts.get(snapshot["batch_id"])
        _check(receipt is not None, "snapshot has no valid original batch receipt")
        matches = [
            item
            for item in receipt["entries"]
            if item["source_relative_path"] == report["source_relative_path"]
        ]
        _check(
            len(matches) == 1
            and matches[0]["source_sha256"] == original
            and matches[0]["report_sha256"] == hashes["report.json"]
            and matches[0]["status"] == report["status"],
            "snapshot report/source/status does not match its original manifest entry",
        )
        canonical = dict(
            report, artifacts=sorted(report["artifacts"], key=lambda item: item["path"])
        )
        encoded = json.dumps(
            canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        _check(
            snapshot_id == "v-" + hashlib.sha256(encoded).hexdigest()[:16],
            "snapshot ID does not match canonical report/artifact inventory",
        )
        if report["status"] in READABLE:
            readable_frontmatter(verified["document.md"], report, source_path)
        if report["status"] == "partial":
            self.warnings.append(
                f"{path}: partial extraction; retain and review {len(report['warnings'])} conversion warning(s)."
            )
        elif report["status"] not in READABLE:
            self.warnings.append(
                f"{path}: diagnostic extraction status {report['status']}; no knowledge source card may use it."
            )
        self.snapshots[source_id, snapshot_id] = snapshot

    def content(self) -> None:
        # navigation.pages applies the same YAML parser used by generation.
        for location, data, body in pages(self.root):
            self.notes[location] = (data, body)
            for issue in note_issues(data, body):
                self.error(location, issue)
            if not _iso(data.get("updated")):
                self.error(location, "updated must be an ISO date or timestamp")
            sources = data.get("sources")
            if isinstance(sources, list) and all(
                isinstance(item, str) for item in sources
            ):
                if len(sources) != len(set(sources)):
                    self.error(location, "sources contains duplicate source IDs")
                for source_id in sources:
                    if source_id not in self.sources:
                        self.error(location, f"unregistered source ID: {source_id}")
            parts = location.split("/")
            if (
                len(parts) > 2
                and parts[1] in KINDS
                and data.get("type") != KINDS[parts[1]]
            ):
                self.error(
                    location, f"type must be {KINDS[parts[1]]!r} in this directory"
                )
            if location == "wiki/overview.md" and data.get("type") != "overview":
                self.error(location, "overview.md must use type overview")
            if parts[1] == "sources" or data.get("type") in {
                "source",
                "source-summary",
            }:
                try:
                    self.source_note(location, data)
                except CAUGHT as exc:
                    self.error(location, exc)
            if parts[1] == "concepts":
                if not isinstance(data.get("related"), list) or any(
                    not isinstance(item, str) for item in data["related"]
                ):
                    self.error(
                        location, "concept related must be a list of page-path strings"
                    )
                for name in ("cluster", "maintenance"):
                    if not isinstance(data.get(name), str):
                        self.error(location, f"concept {name} must be a string")
            if "<!-- semantic-pending -->" in body:
                self.warnings.append(
                    f"{location}: contains an unfinished semantic compilation marker."
                )
        for location in sorted(GENERATED):
            text = safe(self.root, location).read_text(encoding="utf-8")
            _check(
                not text.startswith("---\n"),
                f"{location}: helper-generated navigation/log must not have frontmatter",
            )
            self.notes[location] = ({}, text)
        for source_id, record in self.sources.items():
            if (
                isinstance(record, dict)
                and (source_id, record.get("active")) in self.snapshots
            ):
                snapshot = self.snapshots[source_id, record["active"]]
                if (
                    snapshot["status"] in READABLE
                    and f"wiki/sources/{source_id}.md" not in self.notes
                ):
                    self.error(
                        source_id, "registered readable source has no source card"
                    )

    def source_note(self, location: str, data: dict) -> None:
        source_id = data.get("source_id")
        _check(
            isinstance(source_id, str) and source_id in self.sources,
            "source card source_id is not registered",
        )
        _check(
            location == f"wiki/sources/{source_id}.md",
            "source card filename must identify its source ID",
        )
        _check(
            data.get("type") == "source-summary",
            "source card type must be source-summary",
        )
        _check(
            isinstance(data.get("sources"), list) and source_id in data["sources"],
            "source card sources must include its source_id",
        )
        record = self.sources[source_id]
        _check(type(record) is dict, "source card registry entry must be an object")
        snapshot = self.snapshots.get((source_id, record.get("active")))
        _check(snapshot is not None, "source card has no valid active snapshot")
        _check(
            snapshot["status"] in READABLE,
            "failed/diagnostic extraction cannot generate a source card",
        )
        _check(
            data.get("extraction_status") == snapshot["status"],
            "source card extraction_status differs from its active snapshot",
        )
        _check(
            data.get("warnings") == snapshot["warnings"],
            "source card must preserve active snapshot warnings",
        )
        raw = data.get("raw_document")
        _check(
            isinstance(raw, str),
            "source card raw_document must be a local resource string",
        )
        linked, errors = targets(self.root, location, f"[raw document](<{raw}>)")
        _check(
            not errors and linked == {snapshot["path"] + "/document.md"},
            "source card raw_document does not resolve to its active extraction",
        )

    def navigation(self) -> None:
        linked = {}
        for location, (_, body) in self.notes.items():
            found, errors = targets(self.root, location, body)
            linked[location] = found
            self.errors.extend(errors)
        ordinary = set(self.notes) - GENERATED
        for location in sorted(ordinary - linked.get("wiki/index.md", set())):
            self.error(location, "knowledge note is absent from wiki/index.md")
        concepts = {
            location for location in ordinary if location.startswith("wiki/concepts/")
        }
        for location in sorted(concepts - linked.get("wiki/concept-table.md", set())):
            self.error(location, "concept is absent from wiki/concept-table.md")
        log = self.notes.get("wiki/log.md", ({}, ""))[1]
        headings = re.findall(r"(?m)^##\s+(.+)$", log)
        _check(headings, "wiki/log.md has no operation entry")
        for heading in headings:
            match = re.fullmatch(r"\[(\d{4}-\d{2}-\d{2})\]\s+\S.*", heading)
            _check(
                match and _iso(match[1]),
                f"wiki/log.md: invalid operation heading {heading!r}",
            )


def audit(root: Path) -> dict:
    """Inspect a managed formal vault or workspace, without changing its state."""
    root = Path(root).absolute()
    inspector = Audit(root)
    if root.is_symlink() or not root.is_dir():
        inspector.error(str(root), "audit root must be a real directory")
    else:
        inspector.root = root.resolve()
        for name in ("layout", "registry", "content", "navigation"):
            try:
                getattr(inspector, name)()
            except CAUGHT as exc:
                inspector.error(name, exc)
    return {
        "ok": not inspector.errors,
        "errors": list(dict.fromkeys(inspector.errors)),
        "warnings": list(dict.fromkeys(inspector.warnings)),
        "sources": len(inspector.sources),
        "pages": len(set(inspector.notes) - GENERATED),
        "pending": inspector.pending,
    }
