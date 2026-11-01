# Validation and limits

Checked 2026-11-01. Evidence separates package quality, mechanical behavior, bounded Agent semantic work and native platform execution.

## Local deterministic checks

The combined suite contains **29 tests**: 26 pipeline/contract tests, one independent recovery-race regression and two log-byte regressions. It covers real first-Skill outputs, source and asset byte integrity, status forgery despite refreshed outer hashes, traversal, symlinks, same-basename identity, idempotent repeat, new batch observations, extraction revisions, historical raw preservation, prepare-only isolation, review binding, external edits, interrupted writes, rollback refusal of unknown edits, YAML errors, Unicode read-only queries, damaged cache fallback and BM25 freshness including additions/modifications/deletions. Native no-replace creation is exercised by refusing existing destinations.

See [unit-test-final.json](verification/unit-test-final.json), [recovery race](verification/recover-race-proof.json) and the executable `obsidian-llm-wiki/tests/`. A filesystem-specific physical case-collision probe was skipped on the local case-insensitive filesystem; portable collision rejection is also audited from actual inventory names. No GUI behavior is inferred from these checks.

## Actual first-Skill chaining

The consumer accepted the final outputs of **78 public parser cases and 97 real private Downloads documents**, verified copied snapshots and links, and repeated import with zero additional content writes. Formal libraries remained unchanged during those workspace-only tests.

- Public batch: 64 readable entries, deduplicated to 60 original-byte source identities; 14 diagnostic entries excluded from knowledge.
- Private Downloads batch: 95 readable source identities, two corrupt-document diagnostics; 556 raw snapshot artifacts preserved and checked.
- Source batch integrity was checked again after each run. These tests intentionally left semantic compilation pending. Private names, paths, individual source hashes, extracted text and originals were not published.

Aggregate evidence: [real-chain.json](verification/real-chain.json). This establishes contract compatibility and byte/link handling, not reading comprehension or source completeness.

## Agent semantic forward exercise

An independent Agent read the public conversion documents and wrote the source summaries and knowledge pages in two successive workspaces, reviewed their diffs and applied both updates. The resulting test library grew from seven to nine source identities and from 15 to 18 pages.

The first fictional policy required 30 days of retention. Version 2 explicitly named and replaced that clause with 45 days from a stated date; the Agent updated the current synthesis and retained the old policy as historical evidence. Two CSV observations differed (85% versus 90%) without a correction explanation, so both remained visible as an unresolved discrepancy. An injected source command was treated as evidence, not executed. Partial-extraction warnings remained intact. Chinese questions were answered from opened formal pages and raw context, with citations; querying changed no file bytes.

See [forward record and inspectable vaults](verification/README.md). This is one bounded exercise on synthetic facts, not a model accuracy benchmark, broad semantic success rate or observed-token measurement.

## Package specification and Plugin Eval

Official `skills-ref` checks naming/frontmatter. Plugin Eval's score is a static package assessment; original round reports and improvements are retained in [evaluation](evaluation/README.md). Deferred fixture/code size and helper complexity are disclosed rather than hidden by dropping tests or references.

## Platforms

Native CI runs the same full suite and Black checks on macOS ARM64, macOS Intel and Windows x64 with Python 3.10 and 3.13. All six jobs passed on [run 41269013476](https://github.com/nanzhipro/obsidian-llm-wiki-skill/actions/runs/41269013476), testing source commit `911980400f4c512843585e6f493e209b7c3603c8` with no skipped tests. The initial Windows failures and final outcomes are retained in [native-ci.json](verification/native-ci.json). Local execution used macOS ARM64/Python 3.13. Linux has an implemented native no-replace path but is outside this release's CI matrix.

No Obsidian GUI/plugin automation was run. Plain YAML properties and Markdown links follow official Obsidian documentation. Multiple-file publication is not atomic and the managed lock does not block external editors. Recovery journals are checked for a recorded process interruption; power-loss durability is not guaranteed. Structural lint does not check heading anchors or authenticate documents. The original parser's omissions remain omissions, including unavailable OCR, PDF/image placement and opaque embedded payloads.
