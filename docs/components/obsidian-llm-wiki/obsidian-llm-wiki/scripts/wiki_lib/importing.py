"""Import verified conversion snapshots only into isolated workspaces."""

from __future__ import annotations
from pathlib import Path, PurePosixPath
import shutil

from .bundles import load_batch
from .metadata import page, split_page
from .navigation import append_log, refresh
from .paths import (
    CONTROL,
    STATE,
    digest,
    file_hash,
    json_bytes,
    now,
    read_json,
    read_state,
    safe,
)

PENDING = "<!-- semantic-pending -->"


def source_card(source_id: str, record: dict, previous: str | None) -> bytes:
    snapshot = record["snapshots"][record["active"]]
    raw = "../../" + snapshot["path"]
    data = {
        "title": record["title"],
        "type": "source-summary",
        "description": "Imported extraction; read the original and warnings before synthesis.",
        "updated": now(),
        "sources": [source_id],
        "status": "draft",
        "source_id": source_id,
        "extraction_status": snapshot["status"],
        "raw_document": raw + "/document.md",
        "warnings": snapshot["warnings"],
    }
    body = (
        f'# {record["title"]}\n\n## Evidence\n\n'
        f"[Complete extracted Markdown]({raw}/document.md)\n\n"
        f'[Original file]({raw}/{snapshot["source_path"]})\n\n'
        f"[Conversion report]({raw}/report.json)\n\n"
    )
    body += (
        "## Extraction limits\n\n"
        + "\n".join("- " + str(w).replace("\n", " ") for w in snapshot["warnings"])
        + "\n\n"
    )
    if previous and previous != source_id:
        body += (
            f"Input revision candidate: [{previous}]({previous}.md). "
            "Compare actual versions, dates, and scope before declaring replacement.\n\n"
        )
    return page(
        data,
        body
        + f"## Summary\n\n{PENDING}\nSemantic compilation has not been performed.\n",
    )


def _copy_snapshot(entry, snapshot_root: Path, report_hash: str) -> dict[str, str]:
    expected = {item["path"]: item["sha256"] for item in entry.report["artifacts"]}
    expected["report.json"] = report_hash
    snapshot_root.mkdir(parents=True, exist_ok=True)
    for relative, source in entry.files.items():
        target = safe(snapshot_root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with source.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        if file_hash(target) != expected[relative]:
            raise ValueError(f"Snapshot changed or collides: {relative}")
    return expected


def import_batch(workspace: Path, batch_path: Path, collection: str) -> dict:
    workspace = workspace.resolve()
    origin = read_json(safe(workspace, f"{CONTROL}/workspace.json"))
    state = read_state(workspace)
    if origin.get("vault_id") != state["vault_id"]:
        raise ValueError("Imports require an isolated managed workspace")
    if not collection.strip() or len(collection) > 128:
        raise ValueError("Provide a short explicit collection identity")
    batch = load_batch(batch_path)
    if (
        batch.batch_id in state["batches"]
        and collection in state["batches"][batch.batch_id]["collections"]
    ):
        return {
            "batch_id": batch.batch_id,
            "changed": False,
            "readable": 0,
            "skipped": len(batch.entries),
        }
    manifest_bytes = (batch.root / "manifest.json").read_bytes()
    if batch.batch_id != "b-" + digest(manifest_bytes)[:24]:
        raise ValueError("Manifest changed after validation")
    report_hashes = {
        item["bundle"]: item["report_sha256"] for item in batch.manifest["entries"]
    }
    lineage = state["collections"].setdefault(collection, {})
    outcomes, rejected = [], []
    for entry in batch.entries:
        if entry.status not in {"converted", "partial"}:
            rejected.append(
                {
                    "path": entry.relative_path,
                    "status": entry.status,
                    "error": entry.report.get("error"),
                }
            )
            continue
        source_id = "s-" + entry.source_sha256[:24]
        record = state["sources"].get(source_id)
        if record and record["source_sha256"] != entry.source_sha256:
            raise ValueError("Source identity collision")
        previous = lineage.get(entry.relative_path)
        path = f"raw/{source_id}/{entry.snapshot_id}"
        hashes = _copy_snapshot(
            entry, safe(workspace, path), report_hashes[entry.bundle]
        )
        new_source = record is None
        record = record or {
            "source_sha256": entry.source_sha256,
            "title": PurePosixPath(entry.relative_path).stem,
            "snapshots": {},
        }
        changed_snapshot = record.get("active") != entry.snapshot_id
        snapshot_record = {
            "path": path,
            "files": hashes,
            "status": entry.status,
            "warnings": entry.report.get("warnings", []),
            "source_path": entry.source_path,
            "batch_id": batch.batch_id,
        }
        if entry.snapshot_id not in record["snapshots"]:
            record["snapshots"][entry.snapshot_id] = snapshot_record
        elif any(
            record["snapshots"][entry.snapshot_id].get(key) != value
            for key, value in snapshot_record.items()
            if key != "batch_id"
        ):
            raise ValueError("Existing extraction identity has different metadata")
        record["active"] = entry.snapshot_id
        card = safe(workspace, f"wiki/sources/{source_id}.md")
        card.parent.mkdir(parents=True, exist_ok=True)
        if new_source:
            if card.exists():
                raise ValueError(f"Unmanaged source note already exists: {card.name}")
            card.write_bytes(source_card(source_id, record, previous))
        elif changed_snapshot:
            data, body = split_page(card.read_text(encoding="utf-8"))
            data.update(
                updated=now(),
                extraction_status=entry.status,
                raw_document="../../" + path + "/document.md",
                warnings=record["snapshots"][entry.snapshot_id]["warnings"],
                status="draft",
            )
            body += (
                f"\n## Extraction update\n\n{PENDING}\n"
                f"[New extraction](../../{path}/document.md); "
                "recheck the summary against this snapshot.\n"
            )
            card.write_bytes(page(data, body))
        if new_source or changed_snapshot:
            if source_id not in state["pending"]:
                state["pending"].append(source_id)
        state["sources"][source_id] = record
        lineage[entry.relative_path] = source_id
        outcomes.append(
            {
                "path": entry.relative_path,
                "source_id": source_id,
                "snapshot_id": entry.snapshot_id,
                "status": entry.status,
                "new_source": new_source,
                "new_extraction": changed_snapshot,
                "previous_source": previous,
            }
        )
    receipt = state["batches"].setdefault(
        batch.batch_id,
        {
            "collections": [],
            "rejected": rejected,
            "traversal_errors": batch.manifest["traversal_errors"],
            "excluded": batch.manifest["excluded"],
        },
    )
    receipt["collections"].append(collection)
    safe(workspace, STATE).write_bytes(json_bytes(state))
    receipt_path = safe(workspace, f"{CONTROL}/batches/{batch.batch_id}.json")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(manifest_bytes)
    append_log(
        workspace,
        "import",
        f"{batch.batch_id}: {len(outcomes)} readable, {len(rejected)} diagnostic entries excluded",
    )
    refresh(workspace)
    return {
        "batch_id": batch.batch_id,
        "changed": True,
        "readable": len(outcomes),
        "rejected": rejected,
        "sources": outcomes,
        "pending": state["pending"],
        "traversal_errors": batch.manifest["traversal_errors"],
        "excluded": batch.manifest["excluded"],
    }
