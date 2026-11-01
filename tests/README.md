# Actual two-Skill handoff

`test_handoff.py` executes the native Rust `anydoc-md` binary and the Python Wiki
CLI from this repository, rather than trusting prewritten conversion outputs.
It converts three public inputs: the already licensed image DOCX fixture,
an inline synthetic CSV, and an unsupported binary. The fixture origin and MIT
notice remain under `skills/obsidian-llm-wiki/tests/fixtures/`.

The test checks the real manifest, original and attachment hashes, consumer intake,
diagnostic isolation, semantic-pending state, no changes to formal content during
prepare, reviewed publication, structural lint, preservation of unrelated files
and Obsidian preferences, read-only Unicode retrieval and exact-repeat no-op.
It leaves semantic compilation pending deliberately: no model calls or template
summaries are used to claim knowledge understanding or factual accuracy.

From the repository root, with Rust 1.88+ and Python 3.10+:

```bash
python -m pip install -r requirements-dev.txt
cargo build --manifest-path skills/anydoc-markdown/scripts/anydoc-md/Cargo.toml --locked --release
python -m unittest discover -s tests -p test_handoff.py -v
```

By default the test finds the release binary under the Rust crate's `target/release`
directory, including `.exe` on Windows. `ANYDOC_MD_BIN` can select an explicit
already-built binary. CI uses the test's absolute checkout path and native executable suffix.

The three native OS jobs build and test Rust once each, then run the discovered standalone Skill
regression suites and repository integration tests (including this handoff) with both Python 3.10 and 3.13. That covers macOS
ARM64, macOS Intel and Windows x64 without compiling Rust twice per machine.
No Obsidian GUI automation or model-accuracy evaluation is performed here.
