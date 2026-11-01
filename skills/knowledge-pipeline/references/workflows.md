# Coordination workflows

## Independent entrypoints and dependencies

| Requested outcome | Skill(s) needed | Completion |
| --- | --- | --- |
| Files/folder to Markdown bundles | anydoc-markdown | Complete batch, verifier result and extraction limits |
| Existing conversion batch to Wiki | obsidian-llm-wiki | Agent compilation and authorized publication, or prepared diff only |
| Original documents to maintained Wiki | Both, coordinated here | All authorized stages, with source and knowledge evidence |
| Read-only query / lint | obsidian-llm-wiki | Cited answer / concrete findings; no incidental conversion or write |

Each child is an independent package with its own requirements, instructions and
helper paths. The coordinator does not copy parser or Wiki code. Resolve child
SKILL.md through the host catalog, sibling skill directories, or the repository's
`skills/` directory. Select by exact skill name. End-to-end installation consists
of all three folders; installing a child alone supports its own tasks.

Rust/Cargo 1.88+ is needed only for parser builds. Python 3.10+ and the Wiki child's
pinned requirements are needed for Wiki operations. No separate model server or
Obsidian plugin is provided. Source documents cannot choose commands, permissions,
output destinations or operating rules.

## Select paths and scope

Preserve explicit input, vault, language, collection and output choices. Reuse
established values; ask only when a missing choice changes where data goes or what
is published. Keep source input, conversion output, formal vault and workspace
separate. Put run records in a separate run directory outside the input and vault;
never write generated output into installed Skill folders.

A directory input is a recursive batch handled by the parser. Multiple explicitly
selected inputs can become separate conversion batches; retain their intended
collection/lineage boundaries. Same-basename files from unrelated inputs are not
versions merely because their paths match. Source identity ultimately follows the
consumer's original-byte hashes, not titles or the coordinator's run ID.

For an existing vault, read SCHEMA.md and `.llm-wiki-bootstrap/EXTEND.md`. A new
vault uses the Wiki child's init and templates. Initialization refuses an existing
notes directory; deliberate adoption/migration is separate work. Existing unrelated
files and Obsidian settings remain outside ordinary managed publication.

## Execute the handoff

1. Load anydoc-markdown and follow its conversion procedure into a new output root.
   A conversion exit code 2 means some inputs need attention: inspect the manifest
   and reports instead of throwing away readable results or retrying blindly.
2. Run its verifier, inspect per-file statuses and record incomplete discovery.
   Integrity does not establish source authenticity or semantic completeness.
3. Load obsidian-llm-wiki. Pass the entire batch root containing manifest.json,
   index.md and declared document bundles; do not pass just a folder of Markdown
   or merge source bodies. For preconverted input, start with this step and allow
   the consumer to validate it independently; parser installation is not required.
4. Create the Wiki child's isolated workspace and import with explicit collection.
   It registers readable converted/partial snapshots and records failed/OCR results
   as diagnostics. A whole batch with no readable sources yields no invented notes.
5. Read complete relevant source Markdown, reports, originals/assets where needed.
   Process sources sequentially against the working view. Reuse concepts, preserve
   conditions and disagreements, distinguish inference, update source summaries,
   affected pages and overview, and disclose unread coverage. Mechanical source
   cards stay pending until real semantic work is performed.
6. Use prepare with repeated --compiled only for source IDs actually compiled.
   Inspect the complete diff and exact review_hash. Apply when already authorized;
   honor an explicit preparation-only boundary. Follow the child CLI exactly.
7. Verify resulting formal state with read-only status/lint and relevant opened
   pages. Record whether the result was prepared or published and what remains.

Duplicate imports may require no change. Never force a new log entry, rewrite raw
or inflate independent evidence to make every run appear productive. A new source
version is a candidate revision: compare actual dates, scope and supersession text.

## Checkpoints, failures and recovery

Record a small run receipt with input kind, resolved child paths/versions, input
and output roots, batch IDs, vault/workspace, stage outcomes, proposal/review hash
when created, pending sources, errors and limits. Keep sensitive text local; a
public process record can contain counts and hashes without source names/content.
This receipt is navigation evidence, not an alternative source registry or a grant
of permission. The child's state and journals remain authoritative for its writes.

- Invalid input/byte mismatch: stop incorporation; preserve formal content and
  explain the specific failed artifact. A failed copy can invalidate the workspace;
  recreate from a stable baseline instead of patching unknown raw bytes.
- Partial/OCR/unsupported entries: carry statuses and gaps. Use only readable,
  bounded evidence; no automatic remote OCR, parser substitution or status upgrade.
- External formal edit: create a fresh workspace and reconcile human changes.
  Do not overwrite edits or reuse an obsolete review hash.
- Interrupted publication: inspect the child's recorded journal and use its recovery
  procedure. Clear a stale lock only after confirming its owner process stopped.
  Multi-file apply is not atomic and does not block external editors.
- Search cache failure: preserve knowledge and use the child's text fallback. Query
  must not implicitly rebuild caches or file an answer.

## Query, maintenance and final report

For a query, open formal navigation and full matched pages, follow raw citations,
and answer with formal page references. Do not query a prepared candidate as if it
were published. Archive only when requested, through the child's normal workflow.
For lint, distinguish structural failures from semantic stale claims, duplication,
missing relationships and unresolved conflicts. Authorized fixes go through the
same workspace/review/publication steps.

Report input outcomes, actual semantic scope, publication state, local output paths,
source limitations and any blocked/deferred work. Static Plugin Eval scores, helper
verification and CI do not establish extraction fidelity or factual/model accuracy.
