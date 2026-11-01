"""Rollback must preserve edits that arrive after its first conflict scan."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from wiki_lib import publication
from wiki_lib.bootstrap import initialize, workspace
from wiki_lib.paths import CONTROL, read_json


class RecoveryRaceTest(unittest.TestCase):
    def test_unknown_edit_between_recovery_scans_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix="wiki-recovery-race-") as temporary:
            root = Path(temporary).resolve()
            vault, candidate = root / "vault", root / "candidate"
            initialize(vault, "Recovery fixture", "Local synthetic evidence", "source")
            workspace(vault, candidate)
            overview = candidate / "wiki/overview.md"
            overview.write_bytes(overview.read_bytes() + b"\nProposed maintenance.\n")
            proposal = publication.prepare(
                vault, candidate, "Exercise rollback", "maintain", []
            )
            review = publication.diff(vault, proposal["proposal"])["review_hash"]
            write_change = publication._write_change

            def interrupt_after_first_write(*args):
                write_change(*args)
                raise RuntimeError("Simulated interruption")

            with patch.object(
                publication, "_write_change", interrupt_after_first_write
            ):
                with self.assertRaisesRegex(ValueError, "Publication interrupted"):
                    publication.apply(vault, proposal["proposal"], review)

            active = vault / CONTROL / "active.json"
            journal = vault / CONTROL / "journals" / proposal["proposal"]
            plan = read_json(journal / "plan.json")
            final_preflight = journal / "before" / plan["changes"][-1]["path"]
            formal_note = vault / "wiki/overview.md"
            external_bytes = formal_note.read_bytes() + b"\nExternal human edit.\n"
            hash_file, injected = publication.file_hash, []

            def edit_after_last_preflight_hash(path):
                result = hash_file(path)
                if Path(path).resolve() == final_preflight.resolve() and not injected:
                    formal_note.write_bytes(external_bytes)
                    injected.append(True)
                return result

            with patch.object(publication, "file_hash", edit_after_last_preflight_hash):
                with self.assertRaisesRegex(ValueError, "external edit"):
                    publication.recover(vault, rollback=True)

            self.assertTrue(
                injected, "The test must reach the gap between recovery scans"
            )
            self.assertEqual(formal_note.read_bytes(), external_bytes)
            self.assertTrue(
                active.is_file(), "Conflict must retain the recovery marker"
            )
            self.assertFalse((journal / "rolled-back.json").exists())


if __name__ == "__main__":
    unittest.main()
