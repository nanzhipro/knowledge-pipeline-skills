# Contract and maintenance design

The first skill extracts documents. This second skill consumes only a complete `anydoc-markdown/1` batch, validates it independently, and lets an Agent compile an evolving local Wiki. It adds no OKF container or claim-level schema. A standard Markdown editor can read the same files as Obsidian.

## Identities

| Identity | Meaning | Consequence |
| --- | --- | --- |
| `s-` + first 24 hex of original SHA-256 | Original file bytes | Full digest remains in state; collisions reject. Copies do not corroborate one another. |
| `v-` + first 16 hex of canonical report SHA-256 | Extraction snapshot including artifact hashes and source path | Same source can retain multiple extractions. Old raw files never change. |
| `b-` + first 24 hex of original manifest SHA-256 | Observed conversion batch | Exact manifest bytes preserved; same batch + collection is a no-op. |
| Explicit collection + source-relative path | Candidate lineage | Changed bytes are possible revisions; the Agent must establish semantic replacement. |

Snapshots include `document.md`, `report.json`, preserved original and all declared assets, keeping the exact relative layout. Undeclared files are ignored. Failed/unsupported/OCR diagnostics remain in the batch receipt and ledger, without source cards. A partial readable extraction can be used only within its observed coverage. Batch traversal errors remain warnings about incomplete discovery.

## Changes

1. `workspace` copies every managed file and records the complete content inventory. It does not copy `.obsidian` or unrelated root files. Human pages already under `wiki/` are included and must satisfy the declared note contract when publishing.
2. `import` modifies only the workspace. It validates the input before copying; a copy-time change is detected by checking copied bytes. A failed workspace should be discarded and recreated. Do not overlap input and output directories.
3. The Agent reads sources sequentially, reuses concepts, preserves conditions and disagreements, updates source summaries, metadata and overview, and states unread coverage. No minimum page or concept count is imposed.
4. `prepare` compares the original full baseline with the actual formal inventory, refuses old raw/rule/receipt changes, preserves source history and log prefix, refreshes navigation, audits the prospective library, then freezes a proposal. A source is cleared from `pending` only when explicitly declared `--compiled` and its unfinished marker is absent. This is an Agent attestation.
5. `diff` includes text changes and binary hashes, returning the digest of the exact plan plus bound candidate digests. Review is a workflow action; a matching digest does not establish authorization or truth.
6. `apply` locks managed writers, rechecks the full baseline, saves verified before/after images, sets an active journal, applies checked individual writes, writes the state last and clears the marker after the resulting inventory matches.
7. Interrupted apply blocks normal operations. `recover --rollback` preflights all affected bytes, refuses unknown external edits and restores the recorded baseline. Stale locks require explicit `--clear-lock` only after the old process has stopped. Retrying an old rolled-back proposal is unnecessary; create a fresh workspace/proposal.

Each file publication uses native no-replace creation for new paths and checked replacement for existing paths. Multiple files are **not** atomically visible together. External editors ignore the lock and a time-of-check/time-of-use window remains. Recovery is bounded to the recorded operation; journal integrity and retained filesystem contents matter. Ordinary backups remain useful.

Normal publication cannot change SCHEMA, AGENTS or EXTEND. Deliberate contract/preference migrations should be planned and performed separately, then a fresh workspace created. Page deletion requires `--allow-delete`; existing raw and receipts cannot be removed through that flag. Unrelated root files and `.obsidian` are outside the managed inventory and are never deleted by a proposal.

## Lint and retrieval

Lint verifies registry, source/snapshot/receipt linkage, actual raw hashes, YAML shape, source IDs, portable names, local Markdown targets, explicit wiki/raw-root wikilinks, index membership, concept-map membership and log headings. It excludes raw Markdown's retained authored links from knowledge-link checks. It does not verify heading anchors, ambiguous Obsidian basename lookup, complex plugin syntax, rendering, source completeness, citations' semantic support or factual correctness. Generated links use relative Markdown paths with encoded destinations.

Text search performs Unicode case-insensitive substring matching in formal `wiki/**/*.md`; result scope includes navigation. Read full relevant pages and raw context before answering. `index-search` explicitly builds a disposable local SQLite FTS5 cache. A path+content fingerprint detects modifications, additions and deletions. `search --bm25` opens the cache read-only, falls back for missing/stale/no lexical matches, and does not silently rebuild. SQLite without FTS5 cannot build the optional index; text search remains available.

The Agent reads EXTEND preferences; helper runtime flags and state are explicit. No background daemon, automatic folder watcher, remote model service, OCR fallback, Obsidian GUI integration or vector semantic search is shipped. Invoke the Skill for each new batch, query or maintenance task.
