"""Cross-platform byte preservation for append-only Wiki history."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
CLI = SKILL / "scripts" / "wiki.py"
FIXTURES = Path(__file__).parent / "fixtures"


class LogByteTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="wiki-log-bytes-")
        self.root = Path(self.temporary.name)
        self.vault = self.root / "知识库"

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def initialize(self):
        self.cli(
            "init",
            "--vault",
            self.vault,
            "--name",
            "History byte preservation",
            "--domain",
            "Synthetic public documents",
            "--language",
            "zh-CN",
        )

    def test_crlf_history_bytes_survive_import_prepare_and_apply(self):
        self.initialize()
        history = (
            "# Wiki operation history\r\n\r\n"
            "## [2026-10-31] legacy | 既有历史，保留字节\r\n\r\n"
            "- Original Windows CRLF history; café.\r\n"
        ).encode("utf-8")
        formal_log = self.vault / "wiki/log.md"
        formal_log.write_bytes(history)
        workspace = self.root / "candidate"
        self.cli("workspace", "--vault", self.vault, "--output", workspace)
        self.cli(
            "import",
            "--workspace",
            workspace,
            "--batch",
            FIXTURES / "anydoc-v1",
            "--collection",
            "public-fixture",
        )
        candidate_log = workspace / "wiki/log.md"
        imported = candidate_log.read_bytes()
        self.assertTrue(imported.startswith(history))
        self.assertEqual(formal_log.read_bytes(), history)
        prepared = self.cli(
            "prepare",
            "--vault",
            self.vault,
            "--workspace",
            workspace,
            "--reason",
            "Add pending source drafts while preserving legacy history",
            "--operation",
            "ingest",
        )
        self.assertTrue(candidate_log.read_bytes().startswith(imported))
        self.assertEqual(formal_log.read_bytes(), history)
        reviewed = self.cli(
            "diff", "--vault", self.vault, "--proposal", prepared["proposal"]
        )
        self.cli(
            "apply",
            "--vault",
            self.vault,
            "--proposal",
            prepared["proposal"],
            "--reviewed",
            reviewed["review_hash"],
        )
        self.assertTrue(formal_log.read_bytes().startswith(history))
        self.assertEqual(formal_log.read_bytes(), candidate_log.read_bytes())

    def test_initial_generated_text_uses_lf_on_every_platform(self):
        self.initialize()
        generated = [p for p in self.vault.rglob("*") if p.is_file()]
        self.assertGreaterEqual(len(generated), 8)
        self.assertTrue((self.vault / "AGENTS.md").is_file())
        self.assertTrue((self.vault / "wiki/log.md").is_file())
        for path in generated:
            with self.subTest(path=path.relative_to(self.vault).as_posix()):
                raw = path.read_bytes()
                raw.decode("utf-8")
                self.assertIn(b"\n", raw)
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
