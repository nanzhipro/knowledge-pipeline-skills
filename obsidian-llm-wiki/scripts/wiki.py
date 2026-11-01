#!/usr/bin/env python3
"""Portable local Wiki lifecycle. Success and errors are JSON; no model API calls."""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path
import sys


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Initialize a new empty vault")
    init.add_argument("--vault", type=Path, required=True)
    init.add_argument("--name", required=True)
    init.add_argument("--domain", required=True)
    init.add_argument("--language", default="source")
    work = commands.add_parser("workspace", help="Copy a consistent managed baseline")
    work.add_argument("--vault", type=Path, required=True)
    work.add_argument("--output", type=Path, required=True)
    ingest = commands.add_parser(
        "import", help="Validate and import an AnyDoc batch into a workspace"
    )
    ingest.add_argument("--workspace", type=Path, required=True)
    ingest.add_argument("--batch", type=Path, required=True)
    ingest.add_argument("--collection", required=True)
    prepare = commands.add_parser(
        "prepare", help="Validate and freeze a reviewable proposal"
    )
    prepare.add_argument("--vault", type=Path, required=True)
    prepare.add_argument("--workspace", type=Path, required=True)
    prepare.add_argument("--reason", required=True)
    prepare.add_argument(
        "--operation", choices=["ingest", "query-filed", "lint"], default="ingest"
    )
    prepare.add_argument("--compiled", action="append", default=[])
    prepare.add_argument("--allow-delete", action="store_true")
    for name in (
        "diff",
        "apply",
        "recover",
        "lint",
        "search",
        "index-search",
        "status",
    ):
        command = commands.add_parser(name)
        command.add_argument("--vault", type=Path, required=True)
        if name in {"diff", "apply"}:
            command.add_argument("--proposal", required=True)
        if name == "apply":
            command.add_argument("--reviewed", required=True)
        if name == "recover":
            command.add_argument("--rollback", action="store_true")
            command.add_argument("--clear-lock", action="store_true")
        if name == "search":
            command.add_argument("--query", required=True)
            command.add_argument("--limit", type=int, default=20)
            command.add_argument("--bm25", action="store_true")
    return result


def execute(args) -> dict:
    from wiki_lib import bootstrap, importing, publication, searching
    from wiki_lib.paths import ensure_ready, read_state

    if args.command == "init":
        return bootstrap.initialize(args.vault, args.name, args.domain, args.language)
    if args.command == "workspace":
        return bootstrap.workspace(args.vault, args.output)
    if args.command == "import":
        return importing.import_batch(args.workspace, args.batch, args.collection)
    if args.command == "prepare":
        return publication.prepare(
            args.vault,
            args.workspace,
            args.reason,
            args.operation,
            args.compiled,
            args.allow_delete,
        )
    if args.command == "diff":
        return publication.diff(args.vault, args.proposal)
    if args.command == "apply":
        return publication.apply(args.vault, args.proposal, args.reviewed)
    if args.command == "recover":
        return publication.recover(args.vault, args.rollback, args.clear_lock)
    if args.command == "lint":
        from wiki_lib.quality import audit

        ensure_ready(args.vault)
        return audit(args.vault)
    if args.command == "search":
        return searching.search(args.vault.resolve(), args.query, args.limit, args.bm25)
    if args.command == "index-search":
        return searching.build_index(args.vault.resolve())
    ensure_ready(args.vault)
    state = read_state(args.vault)
    return {
        "revision": state["revision"],
        "sources": len(state["sources"]),
        "snapshots": sum(len(s["snapshots"]) for s in state["sources"].values()),
        "pending": state["pending"],
        "batches": len(state["batches"]),
        "rejected": sum(len(b["rejected"]) for b in state["batches"].values()),
    }


def main() -> int:
    if sys.version_info < (3, 10):
        print(json.dumps({"ok": False, "error": "Python 3.10 or newer is required"}))
        return 2
    args = parser().parse_args()
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok", True) else 2
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        ImportError,
        json.JSONDecodeError,
        sqlite3.Error,
    ) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
