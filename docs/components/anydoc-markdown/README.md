> Historical component snapshot. Current installation and release: [repository README](../../../README.md). Old repository URLs below are historical; use the migration mapping and portable backup.

# AnyDoc Markdown Skill

[![Native Rust checks](https://github.com/nanzhipro/anydoc-markdown-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/nanzhipro/anydoc-markdown-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An [Agent Skill](https://agentskills.io/) that converts document files or entire folders into local, auditable Markdown bundles using **Rust anydoc 0.2.4**. Designed for Windows and macOS. No Python/Node conversion binding, cloud OCR, API key, OKF, or Wiki installation is required.

[中文说明](README.zh-CN.md) · [Skill instructions](anydoc-markdown/SKILL.md) · [Output contract](anydoc-markdown/references/output-contract.md) · [Validation evidence](docs/validation.md)

## What you get

Each discovered regular file receives its own directory with readable Markdown (or an explicit failure page), a preserved original, available extracted assets, and a machine-readable conversion report. A batch index and manifest map inputs to outputs. Input directories are scanned recursively; existing outputs are never overwritten.

```text
output/
├── index.md
├── manifest.json
└── documents/
    └── doc-report.docx--<path-hash>/
        ├── document.md
        ├── source/original.docx
        ├── assets/asset-0001-<hash>.png
        └── report.json
```

This is document extraction. Knowledge synthesis, translation and Wiki maintenance belong in later steps.

## Install the skill

```sh
npx skills add nanzhipro/anydoc-markdown-skill@anydoc-markdown
```

Or copy the entire `anydoc-markdown/` folder into your agent's skills directory. The folder is self-contained, including its Rust helper and lockfile. See [Agent Skills integration](https://agentskills.io/integrate-skills) for compatible hosts.

Then ask your agent:

> Use $anydoc-markdown to convert this document folder into a new Markdown output directory. Preserve originals and report anything that could not be fully extracted.

## Run without an agent

Install [Rust/Cargo 1.88+](https://rustup.rs/), then clone this repository. The same commands work in macOS shells and Windows PowerShell:

```text
git clone https://github.com/nanzhipro/anydoc-markdown-skill.git
cd anydoc-markdown-skill
cargo run --locked --release --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml -- convert "PATH_TO_INPUT" --output "NEW_OUTPUT_DIRECTORY"
cargo run --locked --release --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml -- verify "NEW_OUTPUT_DIRECTORY"
```

First build fetches Rust dependencies. Conversion itself makes no network calls. Windows may require Microsoft C++ Build Tools; macOS may require Xcode Command Line Tools. A local executable can be installed with `cargo install --locked --path anydoc-markdown/scripts/anydoc-md`.

Optional flags: `--include-hidden` includes hidden input entries; `--max-file-mb 256` raises the default per-file 128 MiB limit. Symlinks are skipped and input/output directory overlap is refused. Use a new output directory for reruns.

## Supported input

DOC, DOCX/DOCM, PPT/PPS/POT, PPTX/PPTM/PPSX/PPSM, XLS/XLSX/XLSM/XLSB, ODT, ODS, ODP, RTF, EPUB, CSV and PDF. Detection uses content signatures before filename extensions. CSV uses its extension as a fallback. Unsupported files still receive a status page/report and, when readable and within the size limit, a source copy.

| Outcome | Meaning |
| --- | --- |
| `converted` | Readable extraction with no recorded warning; not a losslessness guarantee |
| `partial` | Readable extraction requiring review; includes conservative format-wide limitations |
| `needs_ocr` | Scanned/image-only PDF pages detected; no text extraction or remote fallback |
| `unsupported` / `error` | An explicit failure page, preserved source when available, and diagnostic report |

Conversion exits **0** for a clean batch, **2** when any document needs attention, and **1** for a CLI/setup failure. `verify` exits 0 when recorded artifacts match their hashes; it does not turn failed documents into successful conversions.

## Fidelity and assets

The helper uses the published anydoc parser and a small, attributed copy of its matching MIT Markdown serializer to render localized image references. Exposed asset bytes are saved unchanged. Known package media omitted by the shared model are recovered to an attachment appendix with placement marked unknown. Archive paths never become output filesystem paths.

Arbitrary documents cannot be represented losslessly as Markdown. Text PDFs do not expose embedded figures through this Rust API; scanned PDFs require a separate OCR workflow. Spreadsheet formulas are not recalculated, slide layout/animation is not preserved, and some legacy objects remain only in the original. External image references are retained without fetching. See [format limits](anydoc-markdown/references/formats-and-limits.md).

Markdown is UTF-8/LF GFM with flat YAML provenance and relative local asset links. Source snapshots and hashes support inspection; they do not certify factual correctness.

## Verification and development

```text
cargo test --locked --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml
cargo clippy --locked --all-targets --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml -- -D warnings
cargo fmt --check --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml
```

Native CI runs the Rust tests on macOS ARM64, macOS Intel and Windows. The public fixture corpus covers 14 file extensions, embedded images, a scanned PDF and a truncated PDF. Local Downloads documents are tested separately; their contents and private paths are not committed. Exact results and limitations are in [validation](docs/validation.md), [development history](docs/development-log.md), and [Plugin Eval records](docs/evaluation/README.md). A Plugin Eval static score is not a conversion-accuracy score.

Backend version policy: latest stable anydoc was checked on **2026-11-01** and pinned to `=0.2.4`. `Cargo.lock` also pins transitive dependencies, including PDF handling. [Upstream releases](https://github.com/firecrawl/anydoc/releases) and [Agent Skills specification](https://agentskills.io/specification) are the reference sources. Updating the backend requires rerunning the native and corpus checks.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Include a redistributable minimal fixture and the expected failure or content difference; do not submit confidential source documents. Report the CLI/anydoc version and operating system. Maintained by [nanzhipro](https://github.com/nanzhipro); use [GitHub Issues](https://github.com/nanzhipro/anydoc-markdown-skill/issues) for questions or reproducible bugs.

## License

[MIT](LICENSE). Upstream renderer and public fixtures retain their original MIT notices; see [NOTICE](NOTICE). The conversion of a document does not change that document's copyright or license.
