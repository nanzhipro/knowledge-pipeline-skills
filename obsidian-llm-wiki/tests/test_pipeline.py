"""Independent contract tests over real anydoc outputs; no model-score assertions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from wiki_lib.bundles import load_batch
from wiki_lib.metadata import page, split_page
from wiki_lib.paths import managed_files, read_state, safe, publish_new
from wiki_lib import publication


def hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.is_symlink()
    }


def write_json(path: Path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="wiki-test-")
        self.root = Path(self.temporary.name)
        self.vault = self.root / "正式知识库"
        self.work = self.root / "候选工作区"

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "wiki.py"), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(
                f"CLI did not return JSON: {result.stdout!r} stderr={result.stderr!r}"
            )
        if ok:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertEqual(result.returncode, 2, output)
            self.assertIn("error", output)
        return output

    def create(self):
        self.cli(
            "init",
            "--vault",
            self.vault,
            "--name",
            "审查记录库",
            "--domain",
            "Synthetic public incident evidence",
            "--language",
            "zh-CN",
        )
        self.cli("workspace", "--vault", self.vault, "--output", self.work)

    def ingest(self):
        self.create()
        return self.cli(
            "import",
            "--workspace",
            self.work,
            "--batch",
            FIXTURES / "anydoc-v1",
            "--collection",
            "synthetic-policy",
        )

    def prepared(self):
        self.ingest()
        return self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            self.work,
            "--reason",
            "Import public fixture evidence as pending drafts",
            "--operation",
            "ingest",
        )["proposal"]

    def reviewed(self, proposal):
        return self.cli("diff", "--vault", self.vault, "--proposal", proposal)[
            "review_hash"
        ]

    def apply(self, proposal):
        return self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            self.reviewed(proposal),
        )

    def mutate_batch(self):
        batch = self.root / "mutated-input"
        shutil.copytree(FIXTURES / "anydoc-v1", batch)
        return batch

    def test_real_batches_and_originals_remain_unchanged(self):
        for version in ("anydoc-v1", "anydoc-v2"):
            batch_path = FIXTURES / version
            before = hashes(batch_path)
            batch = load_batch(batch_path)
            self.assertEqual(len(batch.entries), 10)
            self.assertEqual(
                sum(e.status in {"converted", "partial"} for e in batch.entries), 7
            )
            self.assertEqual(before, hashes(batch_path))

    def test_independent_artifact_tampering_is_rejected(self):
        for pattern in ("document.md", "source/original.rtf", "assets/*.png"):
            with self.subTest(pattern=pattern):
                batch = self.mutate_batch()
                artifact = next(batch.glob("documents/*/" + pattern))
                artifact.write_bytes(artifact.read_bytes() + b"\nchanged")
                with self.assertRaises((ValueError, OSError)):
                    load_batch(batch)
                shutil.rmtree(batch)

    def test_forged_status_with_refreshed_report_hash_is_rejected(self):
        batch = self.mutate_batch()
        manifest_path = batch / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(
            e
            for e in manifest["entries"]
            if e["source_relative_path"].endswith("service-protocol.rtf")
        )
        report_path = batch / entry["bundle"] / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report.update(status="converted", warnings=[])
        write_json(report_path, report)
        entry.update(
            status="converted",
            report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        )
        manifest["counts"]["converted"] += 1
        manifest["counts"]["partial"] -= 1
        write_json(manifest_path, manifest)
        with self.assertRaises(ValueError):
            load_batch(batch)

    def test_manifest_unknown_schema_duplicate_and_index_tampering_rejected(self):
        for mutation in ("schema", "duplicate", "index"):
            with self.subTest(mutation=mutation):
                batch = self.mutate_batch()
                manifest_path = batch / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if mutation == "schema":
                    manifest["schema"] = "future-format/9"
                elif mutation == "duplicate":
                    manifest["entries"].append(manifest["entries"][0])
                else:
                    (batch / "index.md").write_text("changed", encoding="utf-8")
                write_json(manifest_path, manifest)
                with self.assertRaises(ValueError):
                    load_batch(batch)
                shutil.rmtree(batch)

    def test_traversing_report_artifact_is_rejected_after_hash_refresh(self):
        batch = self.mutate_batch()
        manifest_path = batch / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = manifest["entries"][0]
        report_path = batch / entry["bundle"] / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["artifacts"][0]["path"] = "../escape.md"
        write_json(report_path, report)
        entry["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
        write_json(manifest_path, manifest)
        with self.assertRaises(ValueError):
            load_batch(batch)
        self.assertFalse((self.root / "escape.md").exists())

    def test_bundle_symlink_is_rejected(self):
        batch = self.mutate_batch()
        entry = json.loads((batch / "manifest.json").read_text(encoding="utf-8"))[
            "entries"
        ][0]
        target = batch / entry["bundle"]
        original = self.root / "outside-bundle"
        shutil.move(str(target), original)
        try:
            target.symlink_to(original, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Host cannot create directory symlinks")
        with self.assertRaises(ValueError):
            load_batch(batch)

    def test_initialize_is_non_destructive_and_native_no_replace(self):
        self.vault.mkdir()
        sentinel = self.vault / "personal.md"
        sentinel.write_text("retain me", encoding="utf-8")
        self.cli(
            "init",
            "--vault",
            self.vault,
            "--name",
            "Test",
            "--domain",
            "Test",
            "--language",
            "en",
            ok=False,
        )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "retain me")
        source, destination = self.root / "a", self.root / "b"
        source.write_bytes(b"candidate")
        destination.write_bytes(b"existing")
        with self.assertRaises(OSError):
            publish_new(source, destination)
        self.assertEqual(destination.read_bytes(), b"existing")
        self.assertEqual(source.read_bytes(), b"candidate")

    def test_managed_paths_reject_normalization_and_escape(self):
        for path in (
            ".",
            "../escape",
            "wiki//x.md",
            "wiki/./x.md",
            "/absolute",
            "C:/absolute",
            "wiki\\x.md",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe(self.root, path)

    def test_import_gate_identity_and_repeat_are_idempotent(self):
        output = self.ingest()
        self.assertEqual(output["readable"], 7)
        self.assertEqual(len(output["rejected"]), 3)
        state = read_state(self.work)
        self.assertEqual(len(state["sources"]), 7)
        self.assertEqual(len(list((self.work / "wiki/sources").glob("*.md"))), 7)
        self.assertEqual(len(read_state(self.vault)["sources"]), 0)
        before = hashes(self.work)
        repeated = self.cli(
            "import",
            "--workspace",
            self.work,
            "--batch",
            FIXTURES / "anydoc-v1",
            "--collection",
            "synthetic-policy",
        )
        self.assertFalse(repeated["changed"])
        self.assertEqual(before, hashes(self.work))
        partial_cards = []
        for card in (self.work / "wiki/sources").glob("*.md"):
            data, body = split_page(card.read_text(encoding="utf-8"))
            self.assertIn("semantic-pending", body)
            if data["extraction_status"] == "partial":
                self.assertTrue(data["warnings"])
                partial_cards.append(card)
        self.assertEqual(len(partial_cards), 6)
        self.assertFalse(Path("/tmp/obsidian-wiki-tests/INJECTION_EXECUTED").exists())

    def test_same_basename_memos_have_distinct_identities(self):
        self.ingest()
        lineage = read_state(self.work)["collections"]["synthetic-policy"]
        self.assertNotEqual(
            lineage["research/memo.rtf"], lineage["operations/memo.rtf"]
        )

    def test_v2_preserves_v1_raw_and_deduplicates_unchanged_sources(self):
        self.ingest()
        state_before = read_state(self.work)
        raw_before = hashes(self.work / "raw")
        output = self.cli(
            "import",
            "--workspace",
            self.work,
            "--batch",
            FIXTURES / "anydoc-v2",
            "--collection",
            "synthetic-policy",
        )
        state_after = read_state(self.work)
        self.assertEqual(len(state_after["sources"]), 9)
        self.assertEqual(sum(item["new_source"] for item in output["sources"]), 2)
        self.assertNotEqual(
            state_before["collections"]["synthetic-policy"][
                "handbook/service-protocol.rtf"
            ],
            state_after["collections"]["synthetic-policy"][
                "handbook/service-protocol.rtf"
            ],
        )
        self.assertEqual(
            state_before["collections"]["synthetic-policy"][
                "books/knowledge-brief.epub"
            ],
            state_after["collections"]["synthetic-policy"][
                "books/knowledge-brief.epub"
            ],
        )
        self.assertTrue(
            all(
                hashes(self.work / "raw").get(key) == value
                for key, value in raw_before.items()
            )
        )

    def test_prepare_changes_no_live_content_and_apply_is_review_bound(self):
        self.create()
        formal_before = managed_files(self.vault)
        self.cli(
            "import",
            "--workspace",
            self.work,
            "--batch",
            FIXTURES / "anydoc-v1",
            "--collection",
            "synthetic-policy",
        )
        prepared = self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            self.work,
            "--reason",
            "Stage readable extracts with explicit pending summaries",
            "--operation",
            "ingest",
        )
        self.assertEqual(managed_files(self.vault), formal_before)
        proposal = prepared["proposal"]
        review = self.cli("diff", "--vault", self.vault, "--proposal", proposal)
        self.assertIn("wiki/sources/", review["diff"])
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            "0" * 64,
            ok=False,
        )
        self.assertEqual(managed_files(self.vault), formal_before)
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            review["review_hash"],
        )
        self.assertEqual(len(read_state(self.vault)["sources"]), 7)
        after = managed_files(self.vault)
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            review["review_hash"],
            ok=False,
        )
        self.assertEqual(managed_files(self.vault), after)
        self.assertTrue(self.cli("lint", "--vault", self.vault)["ok"])

    def test_marker_cannot_be_declared_semantically_compiled(self):
        self.ingest()
        source_id = next(iter(read_state(self.work)["sources"]))
        before = managed_files(self.vault)
        self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            self.work,
            "--reason",
            "Invalid finished marker",
            "--operation",
            "ingest",
            "--compiled",
            source_id,
            ok=False,
        )
        self.assertEqual(before, managed_files(self.vault))

    def test_invalid_citation_broken_link_and_raw_edit_stop_prepare(self):
        for mutation in ("source", "link", "raw"):
            with self.subTest(mutation=mutation):
                self.ingest()
                if mutation == "raw":
                    artifact = next((self.work / "raw").rglob("document.md"))
                    artifact.write_bytes(artifact.read_bytes() + b"changed")
                else:
                    note = self.work / "wiki/overview.md"
                    data, body = split_page(note.read_text(encoding="utf-8"))
                    if mutation == "source":
                        data["sources"] = ["s-" + "f" * 24]
                    else:
                        body += "\n[Missing evidence](not-present.md)\n"
                    note.write_bytes(page(data, body))
                before = managed_files(self.vault)
                self.cli(
                    "prepare",
                    "--vault",
                    self.vault,
                    "--workspace",
                    self.work,
                    "--reason",
                    "Invalid candidate",
                    "--operation",
                    "ingest",
                    ok=False,
                )
                self.assertEqual(before, managed_files(self.vault))
                shutil.rmtree(self.vault)
                shutil.rmtree(self.work)

    def test_external_change_since_workspace_blocks_prepare(self):
        self.ingest()
        note = self.vault / "wiki/overview.md"
        note.write_bytes(note.read_bytes() + b"\nManual external edit.\n")
        before = managed_files(self.vault)
        self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            self.work,
            "--reason",
            "Stale workspace",
            "--operation",
            "ingest",
            ok=False,
        )
        self.assertEqual(before, managed_files(self.vault))

    def test_live_note_change_after_review_blocks_every_write(self):
        proposal = self.prepared()
        reviewed = self.reviewed(proposal)
        path = self.vault / "wiki/overview.md"
        path.write_bytes(path.read_bytes() + b"\nUser annotation.\n")
        before = managed_files(self.vault)
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            reviewed,
            ok=False,
        )
        self.assertEqual(before, managed_files(self.vault))
        self.assertFalse((self.vault / ".llm-wiki/active.json").exists())

    def test_prepared_artifact_tampering_blocks_publication(self):
        proposal = self.prepared()
        reviewed = self.reviewed(proposal)
        artifact = next(
            (self.vault / ".llm-wiki/proposals" / proposal / "files/wiki/sources").glob(
                "*.md"
            )
        )
        artifact.write_bytes(artifact.read_bytes() + b"\nUnreviewed content.\n")
        before = managed_files(self.vault)
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            reviewed,
            ok=False,
        )
        self.assertEqual(before, managed_files(self.vault))

    def test_interruption_journal_rolls_back_exact_prior_state(self):
        proposal = self.prepared()
        reviewed = self.reviewed(proposal)
        before = managed_files(self.vault)
        real_write = publication._write_change
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Synthetic disk interruption")
            return real_write(*args, **kwargs)

        with patch.object(publication, "_write_change", fail_second):
            with self.assertRaisesRegex(ValueError, "interrupted"):
                publication.apply(self.vault, proposal, reviewed)
        self.assertTrue((self.vault / ".llm-wiki/active.json").exists())
        self.cli(
            "workspace",
            "--vault",
            self.vault,
            "--output",
            self.root / "blocked",
            ok=False,
        )
        self.cli("recover", "--vault", self.vault, "--rollback")
        self.assertEqual(managed_files(self.vault), before)
        self.assertFalse((self.vault / ".llm-wiki/active.json").exists())

    def test_recovery_refuses_unknown_external_bytes(self):
        proposal = self.prepared()
        reviewed = self.reviewed(proposal)
        real_write = publication._write_change
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Synthetic interruption")
            return real_write(*args, **kwargs)

        with patch.object(publication, "_write_change", fail_second):
            with self.assertRaises(ValueError):
                publication.apply(self.vault, proposal, reviewed)
        plan = json.loads(
            (self.vault / ".llm-wiki/journals" / proposal / "plan.json").read_text(
                encoding="utf-8"
            )
        )
        first = sorted(
            plan["changes"],
            key=lambda i: (i["path"] == ".llm-wiki/state.json", i["path"]),
        )[0]
        path = self.vault / first["path"]
        path.write_bytes(b"Unknown user content after interruption")
        before = hashes(self.vault)
        self.cli("recover", "--vault", self.vault, "--rollback", ok=False)
        self.assertEqual(hashes(self.vault), before)
        self.assertEqual(path.read_bytes(), b"Unknown user content after interruption")

    def test_new_manifest_receipt_does_not_rewrite_existing_snapshot(self):
        self.apply(self.prepared())
        candidate = self.root / "new-receipt-workspace"
        self.cli("workspace", "--vault", self.vault, "--output", candidate)
        batch = self.mutate_batch()
        manifest_path = batch / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["created_at"] = "2026-11-02T00:00:00+00:00"
        write_json(manifest_path, manifest)
        old_sources = read_state(candidate)["sources"]
        output = self.cli(
            "import",
            "--workspace",
            candidate,
            "--batch",
            batch,
            "--collection",
            "synthetic-policy",
        )
        self.assertTrue(output["changed"])
        self.assertEqual(old_sources, read_state(candidate)["sources"])
        proposal = self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            candidate,
            "--reason",
            "Retain a new batch receipt for identical extraction snapshots",
            "--operation",
            "ingest",
        )["proposal"]
        self.apply(proposal)
        self.assertEqual(old_sources, read_state(self.vault)["sources"])
        self.assertEqual(len(read_state(self.vault)["batches"]), 2)

    def test_new_extraction_same_original_keeps_old_snapshot(self):
        self.apply(self.prepared())
        candidate = self.root / "new-extraction-workspace"
        self.cli("workspace", "--vault", self.vault, "--output", candidate)
        batch = self.mutate_batch()
        manifest_path = batch / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(
            e
            for e in manifest["entries"]
            if e["source_relative_path"].endswith("service-protocol.rtf")
        )
        report_path = batch / entry["bundle"] / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["warnings"].append(
            "Synthetic new parser limitation; original bytes unchanged."
        )
        write_json(report_path, report)
        entry["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
        write_json(manifest_path, manifest)
        sid = read_state(candidate)["collections"]["synthetic-policy"][
            "handbook/service-protocol.rtf"
        ]
        old_snapshots = read_state(candidate)["sources"][sid]["snapshots"]
        self.cli(
            "import",
            "--workspace",
            candidate,
            "--batch",
            batch,
            "--collection",
            "synthetic-policy",
        )
        state = read_state(candidate)
        self.assertEqual(len(state["sources"]), 7)
        self.assertEqual(len(state["sources"][sid]["snapshots"]), 2)
        self.assertTrue(
            all(
                state["sources"][sid]["snapshots"][key] == value
                for key, value in old_snapshots.items()
            )
        )
        proposal = self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            candidate,
            "--reason",
            "Add extraction revision with a new retained limitation",
            "--operation",
            "ingest",
        )["proposal"]
        self.apply(proposal)
        self.assertTrue(self.cli("lint", "--vault", self.vault)["ok"])

    def test_bm25_cache_detects_add_modify_delete_and_search_is_read_only(self):
        proposal = self.prepared()
        self.apply(proposal)
        for mutation in ("add", "modify", "delete"):
            self.cli("index-search", "--vault", self.vault)
            path = self.vault / "wiki/synthesis/retrieval.md"
            if mutation == "add":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(
                    page(
                        {
                            "title": "Retrieval",
                            "type": "synthesis",
                            "description": "Cache freshness",
                            "sources": [],
                            "updated": "2026-11-01",
                        },
                        "# Retrieval\n\nNew freshness sentinel.\n",
                    )
                )
            elif mutation == "modify":
                path.write_bytes(
                    path.read_bytes() + b"\nModified freshness sentinel.\n"
                )
            else:
                path.unlink()
            before = hashes(self.vault)
            result = self.cli(
                "search", "--vault", self.vault, "--query", "freshness", "--bm25"
            )
            self.assertEqual(result["mode"], "text")
            self.assertIn("stale", result["warning"])
            self.assertEqual(before, hashes(self.vault))

    def test_raw_drift_after_prepare_blocks_every_write(self):
        self.apply(self.prepared())
        work2 = self.root / "second-candidate"
        self.cli("workspace", "--vault", self.vault, "--output", work2)
        note = work2 / "wiki/overview.md"
        note.write_bytes(note.read_bytes() + b"\nAgent candidate interpretation.\n")
        proposal = self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            work2,
            "--reason",
            "New interpretation",
            "--operation",
            "lint",
        )["proposal"]
        reviewed = self.reviewed(proposal)
        artifact = next((self.vault / "raw").rglob("document.md"))
        artifact.write_bytes(artifact.read_bytes() + b"\nUnreviewed raw drift.\n")
        before = managed_files(self.vault)
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            proposal,
            "--reviewed",
            reviewed,
            ok=False,
        )
        self.assertEqual(before, managed_files(self.vault))

    def test_corrupt_bm25_cache_falls_back_without_writing(self):
        self.apply(self.prepared())
        cache = self.vault / ".llm-wiki/search.sqlite"
        cache.write_bytes(b"Not a SQLite database")
        before = hashes(self.vault)
        result = self.cli(
            "search", "--vault", self.vault, "--query", "source", "--bm25"
        )
        self.assertEqual(result["mode"], "text")
        self.assertTrue(result["warning"])
        self.assertEqual(before, hashes(self.vault))

    def test_malformed_yaml_returns_json_error_and_preserves_formal_vault(self):
        self.ingest()
        path = self.work / "wiki/overview.md"
        path.write_text("---\ntitle: [unclosed\n---\n\nBody.\n", encoding="utf-8")
        before = managed_files(self.vault)
        result = self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            self.work,
            "--reason",
            "Reject malformed frontmatter",
            "--operation",
            "ingest",
            ok=False,
        )
        self.assertIn("error", result)
        self.assertEqual(before, managed_files(self.vault))

    def test_query_and_lint_are_read_only_and_chinese_search_works(self):
        proposal = self.prepared()
        self.apply(proposal)
        overview = self.vault / "wiki/overview.md"
        data, body = split_page(overview.read_text(encoding="utf-8"))
        overview.write_bytes(
            page(data, body + "\n知识管理与运营记忆的中文检索样本。\n")
        )
        before = hashes(self.vault)
        self.cli("status", "--vault", self.vault)
        self.cli("lint", "--vault", self.vault)
        found = self.cli("search", "--vault", self.vault, "--query", "运营记忆")
        self.assertIn("wiki/overview.md", json.dumps(found, ensure_ascii=False))
        self.assertEqual(hashes(self.vault), before)


if __name__ == "__main__":
    unittest.main()
