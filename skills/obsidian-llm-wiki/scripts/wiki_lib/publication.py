"""Review-bound changes with optimistic conflict checks and recoverable journals.

Each file replacement is atomic, the collection of replacements is not. External
editors do not obey our lock. Never describe this as a database transaction.
"""

from __future__ import annotations
from contextlib import contextmanager
import difflib
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from .importing import PENDING
from .navigation import append_log, refresh
from .paths import (
    CONTROL,
    FIXED,
    STATE,
    atomic_write,
    digest,
    ensure_ready,
    file_hash,
    json_bytes,
    managed_files,
    now,
    publish_new,
    read_json,
    read_state,
    safe,
)


def _audit(root: Path) -> dict:
    from .quality import audit

    result = audit(root)
    if not result["ok"]:
        raise ValueError("Candidate failed lint: " + "; ".join(result["errors"][:12]))
    return result


def _immutable(before: dict, after: dict) -> None:
    for relative, expected in before.items():
        if (
            relative.startswith(("raw/", f"{CONTROL}/batches/"))
            or relative in FIXED[:-1]
        ):
            if after.get(relative) != expected:
                raise ValueError(f"Immutable artifact changed: {relative}")


def _registry(base: dict, candidate: dict) -> None:
    for field in ("vault_id", "format", "name", "domain", "language"):
        if base[field] != candidate[field]:
            raise ValueError(f"Library identity changed: {field}")
    for source_id, old in base["sources"].items():
        new = candidate["sources"].get(source_id, {})
        if old["source_sha256"] != new.get("source_sha256"):
            raise ValueError("Registered source identity removed or changed")
        for snapshot_id, snapshot in old["snapshots"].items():
            if new.get("snapshots", {}).get(snapshot_id) != snapshot:
                raise ValueError("Registered source snapshot removed or changed")


def prepare(
    vault: Path,
    workspace: Path,
    reason: str,
    operation: str,
    compiled: list[str],
    allow_delete: bool = False,
) -> dict:
    vault, workspace = vault.resolve(), workspace.resolve()
    ensure_ready(vault)
    origin = read_json(safe(workspace, f"{CONTROL}/workspace.json"))
    base = origin["base"]
    current = managed_files(vault)
    if (
        origin.get("format") != "wiki-workspace/1"
        or origin.get("vault_id") != read_state(vault)["vault_id"]
    ):
        raise ValueError("Workspace belongs to a different library")
    if current != base:
        raise ValueError(
            "Formal library changed since workspace creation; create a fresh workspace and reconcile"
        )
    state = read_state(workspace)
    _registry(read_state(vault), state)
    for source_id in compiled:
        if source_id not in state["sources"]:
            raise ValueError(f"Unknown compiled source: {source_id}")
        card = safe(workspace, f"wiki/sources/{source_id}.md").read_text(
            encoding="utf-8"
        )
        if PENDING in card:
            raise ValueError(
                f"Source still has an unfinished semantic marker: {source_id}"
            )
        state["pending"] = [item for item in state["pending"] if item != source_id]
    safe(workspace, STATE).write_bytes(json_bytes(state))
    refresh(workspace)
    candidate = managed_files(workspace)
    _immutable(base, candidate)
    old_log = safe(vault, "wiki/log.md").read_bytes()
    if not safe(workspace, "wiki/log.md").read_bytes().startswith(old_log):
        raise ValueError("Operation history must remain append-only")
    if base == candidate:
        return {"changed": False, "proposal": None}
    deleted = sorted(set(base) - set(candidate))
    if deleted and not allow_delete:
        raise ValueError(
            "Deletion requires --allow-delete and complete diff review: "
            + ", ".join(deleted)
        )
    if not reason.strip():
        raise ValueError("A concrete change reason is required")
    state["revision"] = read_state(vault)["revision"] + 1
    safe(workspace, STATE).write_bytes(json_bytes(state))
    append_log(workspace, operation, reason)
    lint = _audit(workspace)
    candidate = managed_files(workspace)
    changes = [
        {"path": key, "before": base.get(key), "after": candidate.get(key)}
        for key in sorted(set(base) | set(candidate))
        if base.get(key) != candidate.get(key)
    ]
    proposal_id = "p-" + uuid.uuid4().hex[:24]
    plan = {
        "format": "wiki-proposal/1",
        "proposal": proposal_id,
        "vault_id": state["vault_id"],
        "created_at": now(),
        "reason": reason,
        "operation": operation,
        "base": base,
        "candidate": candidate,
        "changes": changes,
        "warnings": lint["warnings"],
    }
    destination = safe(vault, f"{CONTROL}/proposals/{proposal_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".proposal-", dir=destination.parent
    ) as temporary:
        staging = Path(temporary) / "proposal"
        staging.mkdir()
        for item in changes:
            if item["after"] is not None:
                target = safe(staging, "files/" + item["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe(workspace, item["path"]), target)
                if file_hash(target) != item["after"]:
                    raise ValueError(
                        "Candidate changed while preparing; retry with stable files"
                    )
        (staging / "plan.json").write_bytes(json_bytes(plan))
        publish_new(staging, destination)
    return {
        "changed": True,
        "proposal": proposal_id,
        "changes": len(changes),
        "warnings": lint["warnings"],
    }


def _proposal(vault: Path, proposal_id: str) -> tuple[Path, dict, str]:
    if not re.fullmatch(r"p-[0-9a-f]{24}", proposal_id):
        raise ValueError("Invalid proposal ID")
    root = safe(vault, f"{CONTROL}/proposals/{proposal_id}")
    plan = read_json(safe(root, "plan.json"))
    if (
        plan.get("format") != "wiki-proposal/1"
        or plan.get("proposal") != proposal_id
        or plan.get("vault_id") != read_state(vault)["vault_id"]
    ):
        raise ValueError("Invalid proposal identity")
    expected_changes = [
        {
            "path": key,
            "before": plan["base"].get(key),
            "after": plan["candidate"].get(key),
        }
        for key in sorted(set(plan["base"]) | set(plan["candidate"]))
        if plan["base"].get(key) != plan["candidate"].get(key)
    ]
    if plan["changes"] != expected_changes:
        raise ValueError("Inconsistent proposal change manifest")
    for item in plan["changes"]:
        relative = item["path"]
        if relative != STATE and not relative.startswith(
            ("wiki/", "raw/", f"{CONTROL}/batches/")
        ):
            raise ValueError("Proposal contains an unmanaged write")
        safe(vault, relative)
        if (
            item["after"] is not None
            and file_hash(safe(root, "files/" + relative)) != item["after"]
        ):
            raise ValueError("Prepared artifact changed after preparation")
    _immutable(plan["base"], plan["candidate"])
    return root, plan, digest(json_bytes(plan))


def diff(vault: Path, proposal_id: str) -> dict:
    root, plan, review_hash = _proposal(vault, proposal_id)
    chunks = []
    for item in plan["changes"]:
        relative = item["path"]
        before_path = safe(vault, relative)
        before = before_path.read_bytes() if before_path.is_file() else b""
        after = (
            safe(root, "files/" + relative).read_bytes()
            if item["after"] is not None
            else b""
        )
        if relative.endswith((".md", ".json")):
            try:
                chunks.append(
                    "".join(
                        difflib.unified_diff(
                            before.decode("utf-8").splitlines(True),
                            after.decode("utf-8").splitlines(True),
                            fromfile="before/" + relative,
                            tofile="after/" + relative,
                        )
                    )
                )
            except UnicodeDecodeError:
                chunks.append(
                    f'Binary content: {relative} {item["before"]} -> {item["after"]}\n'
                )
        else:
            chunks.append(f'Artifact: {relative} {item["before"]} -> {item["after"]}\n')
    return {
        "proposal": proposal_id,
        "review_hash": review_hash,
        "changes": plan["changes"],
        "warnings": plan["warnings"],
        "diff": "\n".join(chunks),
    }


@contextmanager
def _lock(vault: Path):
    path = safe(vault, f"{CONTROL}/LOCK")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError(
            "Managed writer lock exists. Check for a running helper; use recover --clear-lock only after it has stopped"
        ) from None
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json_bytes({"pid": os.getpid(), "created_at": now()}))
        yield
    finally:
        path.unlink(missing_ok=True)


def _write_change(
    root: Path, relative: str, data: bytes | None, expected: str | None
) -> None:
    path = safe(root, relative)
    actual = file_hash(path) if path.is_file() else None
    if actual != expected:
        raise ValueError(f"External change detected: {relative}")
    if data is None:
        if expected is not None:
            path.unlink()
    else:
        atomic_write(path, data, expected)


def apply(vault: Path, proposal_id: str, reviewed: str) -> dict:
    vault = vault.resolve()
    ensure_ready(vault)
    with _lock(vault):
        root, plan, review_hash = _proposal(vault, proposal_id)
        if reviewed != review_hash:
            raise ValueError(
                "Review hash does not match this exact prepared change; inspect diff again"
            )
        if managed_files(vault) != plan["base"]:
            raise ValueError(
                "Formal library changed after preparation; reconcile in a new workspace"
            )
        _registry(read_state(vault), read_json(safe(root, "files/" + STATE)))
        journal = safe(vault, f"{CONTROL}/journals/{proposal_id}")
        journal.mkdir(parents=True, exist_ok=False)
        (journal / "plan.json").write_bytes(json_bytes(plan))
        for item in plan["changes"]:
            for name, source, expected in [
                ("before", safe(vault, item["path"]), item["before"]),
                ("after", safe(root, "files/" + item["path"]), item["after"]),
            ]:
                if expected is not None:
                    target = safe(journal, name + "/" + item["path"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    if file_hash(target) != expected:
                        raise ValueError(
                            "File changed while recording recovery journal"
                        )
        active = safe(vault, f"{CONTROL}/active.json")
        atomic_write(
            active,
            json_bytes({"proposal": proposal_id, "review_hash": review_hash}),
            None,
        )
        try:
            for item in sorted(
                plan["changes"], key=lambda i: (i["path"] == STATE, i["path"])
            ):
                data = (
                    safe(journal, "after/" + item["path"]).read_bytes()
                    if item["after"] is not None
                    else None
                )
                _write_change(vault, item["path"], data, item["before"])
            if managed_files(vault) != plan["candidate"]:
                raise ValueError(
                    "Library changed during publication; recovery required"
                )
            (journal / "completed.json").write_bytes(
                json_bytes({"completed_at": now(), "review_hash": review_hash})
            )
            active.unlink()
        except Exception as error:
            raise ValueError(
                f"Publication interrupted: {error}. Stop editing and use recover --rollback"
            ) from error
    return {
        "applied": proposal_id,
        "revision": read_state(vault)["revision"],
        "changes": len(plan["changes"]),
    }


def recover(vault: Path, rollback: bool, clear_lock: bool = False) -> dict:
    vault = vault.resolve()
    if clear_lock:
        safe(vault, f"{CONTROL}/LOCK").unlink(missing_ok=True)
    active = safe(vault, f"{CONTROL}/active.json")
    if not active.exists():
        return {"recovery": "not-needed", "lock_cleared": clear_lock}
    if not rollback:
        raise ValueError(
            "Interrupted publication exists; inspect journal and request --rollback"
        )
    with _lock(vault):
        marker = read_json(active)
        proposal_id = marker["proposal"]
        if not re.fullmatch(r"p-[0-9a-f]{24}", proposal_id):
            raise ValueError("Invalid recovery marker")
        journal = safe(vault, f"{CONTROL}/journals/{proposal_id}")
        plan = read_json(safe(journal, "plan.json"))
        if digest(json_bytes(plan)) != marker["review_hash"]:
            raise ValueError("Recovery journal changed; manual reconciliation required")
        for item in plan["changes"]:
            path = safe(vault, item["path"])
            actual = file_hash(path) if path.is_file() else None
            if actual not in (item["before"], item["after"]):
                raise ValueError(
                    f'Recovery would overwrite unknown external edit: {item["path"]}'
                )
            if (
                item["before"] is not None
                and file_hash(safe(journal, "before/" + item["path"])) != item["before"]
            ):
                raise ValueError("Recovery before-image changed")
        for item in sorted(
            plan["changes"], key=lambda i: (i["path"] == STATE, i["path"]), reverse=True
        ):
            path = safe(vault, item["path"])
            actual = file_hash(path) if path.is_file() else None
            if actual == item["before"]:
                continue
            if actual != item["after"]:
                raise ValueError(f'Recovery found a new external edit: {item["path"]}')
            data = (
                safe(journal, "before/" + item["path"]).read_bytes()
                if item["before"] is not None
                else None
            )
            _write_change(vault, item["path"], data, item["after"])
        if managed_files(vault) != plan["base"]:
            raise ValueError(
                "Unexpected files remain; inspect journal before clearing recovery marker"
            )
        (journal / "rolled-back.json").write_bytes(
            json_bytes({"rolled_back_at": now()})
        )
        active.unlink()
    return {"recovery": "rolled-back", "proposal": proposal_id}
