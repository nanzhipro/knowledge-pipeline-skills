"""Create new libraries and isolated full managed workspaces."""

from __future__ import annotations
from pathlib import Path
import json
import shutil
import tempfile
import uuid

from .metadata import page
from .navigation import refresh
from .paths import (
    CONTROL,
    PREFS,
    STATE,
    ensure_ready,
    file_hash,
    json_bytes,
    managed_files,
    now,
    publish_new,
    read_state,
    safe,
)


def initialize(vault: Path, name: str, domain: str, language: str) -> dict:
    vault = vault.absolute()
    if vault.exists() or vault.is_symlink():
        raise ValueError(
            "Initialization requires a new directory; existing notes are never adopted silently"
        )
    vault.parent.mkdir(parents=True, exist_ok=True)
    template_root = Path(__file__).resolve().parents[2] / "references/templates"
    with tempfile.TemporaryDirectory(
        prefix=".wiki-init-", dir=vault.parent
    ) as temporary:
        root = Path(temporary) / "vault"
        root.mkdir()
        for directory in (
            "raw",
            ".llm-wiki",
            ".llm-wiki-bootstrap",
            "wiki/sources",
            "wiki/entities",
            "wiki/concepts",
            "wiki/comparisons",
            "wiki/synthesis",
            "wiki/questions",
            "wiki/decisions",
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        schema = (template_root / "SCHEMA.md").read_text(encoding="utf-8")
        for key, value in (("name", name), ("domain", domain), ("language", language)):
            schema = schema.replace("{" + key + "}", value)
        (root / "SCHEMA.md").write_text(schema, encoding="utf-8", newline="\n")
        (root / "AGENTS.md").write_text(
            "# Wiki runtime entry\n\nRead [SCHEMA.md](SCHEMA.md) before operating on this library.\n",
            encoding="utf-8",
        )
        (root / PREFS).write_text(
            (template_root / "EXTEND.md")
            .read_text(encoding="utf-8")
            .replace(
                "language: source",
                "language: " + json.dumps(language, ensure_ascii=False),
            ),
            encoding="utf-8",
            newline="\n",
        )
        state = {
            "format": "obsidian-llm-wiki/1",
            "vault_id": str(uuid.uuid4()),
            "revision": 0,
            "name": name,
            "domain": domain,
            "language": language,
            "sources": {},
            "collections": {},
            "batches": {},
            "pending": [],
        }
        (root / STATE).write_bytes(json_bytes(state))
        (root / "wiki/overview.md").write_bytes(
            page(
                {
                    "title": name,
                    "type": "overview",
                    "description": domain,
                    "updated": now(),
                    "sources": [],
                    "status": "draft",
                },
                "# Overview\n\nNo sources have been compiled yet.\n",
            )
        )
        (root / "wiki/log.md").write_text(
            f"# Wiki operation history\n\n## [{now()[:10]}] bootstrap | New managed library\n",
            encoding="utf-8",
        )
        refresh(root)
        publish_new(root, vault)
    return {"vault": str(vault), "vault_id": state["vault_id"], "created": True}


def workspace(vault: Path, output: Path) -> dict:
    vault = vault.resolve()
    ensure_ready(vault)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Workspace destination already exists")
    future = output.resolve()
    if future.is_relative_to(vault) or vault.is_relative_to(future):
        raise ValueError("Use a separate workspace outside the formal library")
    before = managed_files(vault)
    output.mkdir(parents=True)
    for directory in (
        "raw",
        "wiki/sources",
        "wiki/entities",
        "wiki/concepts",
        "wiki/comparisons",
        "wiki/synthesis",
        "wiki/questions",
        "wiki/decisions",
    ):
        (output / directory).mkdir(parents=True, exist_ok=True)
    for relative, expected in before.items():
        source, target = safe(vault, relative), safe(output, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if file_hash(target) != expected:
            raise ValueError(
                f"Library changed while copying: {relative}; discard this workspace"
            )
    if managed_files(vault) != before:
        raise ValueError("Library changed while copying; discard this workspace")
    origin = {
        "format": "wiki-workspace/1",
        "vault_id": read_state(vault)["vault_id"],
        "created_at": now(),
        "base": before,
    }
    safe(output, f"{CONTROL}/workspace.json").write_bytes(json_bytes(origin))
    return {
        "workspace": str(output),
        "files": len(before),
        "vault_id": origin["vault_id"],
    }
