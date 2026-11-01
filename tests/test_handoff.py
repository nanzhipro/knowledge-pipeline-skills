"""Execute the real Rust converter and Python consumer as a single local pipeline."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "skills/obsidian-llm-wiki"
RUST = ROOT / "skills/anydoc-markdown/scripts/anydoc-md"
BINARY = Path(
    os.environ.get(
        "ANYDOC_MD_BIN",
        str(
            RUST
            / "target/release"
            / ("anydoc-md.exe" if os.name == "nt" else "anydoc-md")
        ),
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path, exclude_proposals: bool = False) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if exclude_proposals and relative.startswith(".llm-wiki/proposals/"):
                continue
            result[relative] = sha256(path)
    return result


class RealHandoffTest(unittest.TestCase):
    def command(self, executable: list[str], *arguments, codes=(0,)) -> dict:
        completed = subprocess.run(
            [*map(str, executable), *map(str, arguments)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertIn(
            completed.returncode,
            codes,
            f"Command failed: {arguments!r}\n{completed.stdout}\n{completed.stderr}",
        )
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            self.fail(
                f"Missing JSON output: {completed.stdout!r}; {completed.stderr!r}"
            )

    def wiki(self, *arguments, **kwargs) -> dict:
        return self.command(
            [sys.executable, str(WIKI / "scripts/wiki.py")], *arguments, **kwargs
        )

    def test_actual_converter_to_reviewed_vault_with_diagnostic_isolation(self):
        self.assertTrue(BINARY.is_file(), f"Build the Rust CLI first: {BINARY}")
        with tempfile.TemporaryDirectory(prefix="real-handoff-") as temporary:
            root = Path(temporary)
            inputs, output = root / "原始资料", root / "转换结果"
            vault, work = root / "正式知识库", root / "候选工作区"
            inputs.mkdir()
            images = sorted(
                (WIKI / "tests/fixtures/anydoc-v1").rglob("source/original.docx")
            )
            self.assertEqual(
                len(images), 1, "Select the licensed public image DOCX fixture"
            )
            shutil.copyfile(images[0], inputs / "图文材料.docx")
            (inputs / "观测.csv").write_bytes(
                b"period,reviews,completion\n2026-10,12,0.85\n"
            )
            (inputs / "diagnostic.bin").write_bytes(b"\x00\x01not-a-document\xfe\xff")
            initial_inputs = inventory(inputs)

            manifest = self.command(
                [str(BINARY)], "convert", inputs, "--output", output, codes=(2,)
            )
            self.assertEqual(manifest["schema"], "anydoc-markdown/1")
            self.assertEqual(len(manifest["entries"]), 3)
            self.assertEqual(manifest["counts"].get("unsupported"), 1)
            self.assertTrue(self.command([str(BINARY)], "verify", output)["ok"])
            initial_output = inventory(output)
            readable = [
                entry
                for entry in manifest["entries"]
                if entry["status"] in {"converted", "partial"}
            ]
            self.assertEqual(len(readable), 2)
            assets = []
            for entry in readable:
                report_path = output / entry["bundle"] / "report.json"
                self.assertEqual(sha256(report_path), entry["report_sha256"])
                report = json.loads(report_path.read_text(encoding="utf-8"))
                for artifact in report["artifacts"]:
                    path = report_path.parent / artifact["path"]
                    self.assertEqual(sha256(path), artifact["sha256"])
                    self.assertEqual(path.stat().st_size, artifact["bytes"])
                    if artifact["path"].startswith("source/"):
                        self.assertEqual(
                            sha256(path), initial_inputs[entry["source_relative_path"]]
                        )
                    if artifact["path"].startswith("assets/"):
                        assets.append(path)
            self.assertGreater(
                len(assets), 0, "The real conversion must emit an attachment"
            )

            self.wiki(
                "init",
                "--vault",
                vault,
                "--name",
                "交接验证",
                "--domain",
                "Synthetic fixture intake",
                "--language",
                "zh-CN",
            )
            (vault / ".obsidian").mkdir()
            (vault / ".obsidian/app.json").write_bytes(b'{"readableLineLength":true}\n')
            (vault / "personal.txt").write_bytes(
                b"Unmanaged personal file must survive.\n"
            )
            formal_before = inventory(vault)
            self.wiki("workspace", "--vault", vault, "--output", work)
            imported = self.wiki(
                "import",
                "--workspace",
                work,
                "--batch",
                output,
                "--collection",
                "public-handoff",
            )
            self.assertEqual(imported["readable"], 2)
            self.assertEqual(len(imported["rejected"]), 1)
            self.assertEqual(imported["rejected"][0]["status"], "unsupported")
            self.assertEqual(inventory(vault), formal_before)
            working_before_repeat = inventory(work)
            repeated = self.wiki(
                "import",
                "--workspace",
                work,
                "--batch",
                output,
                "--collection",
                "public-handoff",
            )
            self.assertFalse(repeated["changed"])
            self.assertEqual(inventory(work), working_before_repeat)

            prepared = self.wiki(
                "prepare",
                "--vault",
                vault,
                "--workspace",
                work,
                "--reason",
                "Stage real extraction with semantic work explicitly pending",
                "--operation",
                "ingest",
            )
            self.assertTrue(prepared["changed"])
            self.assertEqual(inventory(vault, exclude_proposals=True), formal_before)
            reviewed = self.wiki(
                "diff", "--vault", vault, "--proposal", prepared["proposal"]
            )
            self.assertEqual(len(reviewed["review_hash"]), 64)
            applied = self.wiki(
                "apply",
                "--vault",
                vault,
                "--proposal",
                prepared["proposal"],
                "--reviewed",
                reviewed["review_hash"],
            )
            self.assertEqual(applied["revision"], 1)
            lint = self.wiki("lint", "--vault", vault)
            self.assertTrue(lint["ok"], lint)
            self.assertEqual(lint["sources"], 2)
            self.assertEqual(len(lint["pending"]), 2)
            self.assertEqual(self.wiki("status", "--vault", vault)["rejected"], 1)
            cards = sorted((vault / "wiki/sources").glob("*.md"))
            self.assertEqual(len(cards), 2)
            for card in cards:
                self.assertIn(
                    "<!-- semantic-pending -->", card.read_text(encoding="utf-8")
                )
                self.assertNotIn("diagnostic.bin", card.read_text(encoding="utf-8"))

            state = json.loads(
                (vault / ".llm-wiki/state.json").read_text(encoding="utf-8")
            )
            for source in state["sources"].values():
                for snapshot in source["snapshots"].values():
                    for path, expected in snapshot["files"].items():
                        self.assertEqual(
                            sha256(vault / snapshot["path"] / path), expected
                        )
            self.assertEqual(
                sha256(vault / ".obsidian/app.json"),
                formal_before[".obsidian/app.json"],
            )
            self.assertEqual(
                sha256(vault / "personal.txt"), formal_before["personal.txt"]
            )
            before_query = inventory(vault)
            self.assertTrue(
                self.wiki("search", "--vault", vault, "--query", "图文材料")["hits"]
            )
            self.assertEqual(inventory(vault), before_query)

            repeated_work = root / "再次导入"
            self.wiki("workspace", "--vault", vault, "--output", repeated_work)
            self.assertFalse(
                self.wiki(
                    "import",
                    "--workspace",
                    repeated_work,
                    "--batch",
                    output,
                    "--collection",
                    "public-handoff",
                )["changed"]
            )
            unchanged = self.wiki(
                "prepare",
                "--vault",
                vault,
                "--workspace",
                repeated_work,
                "--reason",
                "Exact repeated batch must create no proposal",
                "--operation",
                "ingest",
            )
            self.assertFalse(unchanged["changed"])
            self.assertEqual(inventory(vault), before_query)
            self.assertEqual(inventory(inputs), initial_inputs)
            self.assertEqual(inventory(output), initial_output)


if __name__ == "__main__":
    unittest.main()
