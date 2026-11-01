# Independent pipeline verification

The [execution record](agent-forward-run.json) contains command arguments, JSON
results, complete prepared diffs, the reviewed proposal digests, lint output, and
query answers for one actual Agent-authored synthetic run on macOS ARM64. The
Agent read the complete relevant extracted documents and reports, inspected the
plain RTF source text, and wrote the summaries, three concepts, comparisons,
questions, decisions, and overview. The deterministic helper did not compose those
claims. This is bounded evidence from one run, not a model-accuracy benchmark.

The public input batches are in
[`obsidian-llm-wiki/tests/fixtures`](../../obsidian-llm-wiki/tests/fixtures/PROVENANCE.md).
They came from actual Rust AnyDoc conversion, have ten files each, and carry
converted/partial/needs_ocr/error/unsupported results. No private Downloads files
were used. The same-batch input tree hashes remained identical throughout.

| Observed result | First publication | Maintained publication |
| --- | --- | --- |
| Readable source identities | 7 | 9 (two changed originals) |
| Semantic notes, including source cards | 15 | 18 |
| Pending compilation markers | 0 | 0 |
| Current fictional retention rule | 30 days, revision 1 | 45 days, revision 2 |
| Earlier raw snapshots | Preserved | Every earlier byte preserved |
| Partial warnings | Visible | Visible; no extraction-status upgrade |
| Unreadable/unsupported inputs | 3 diagnostics, no knowledge source card | Still excluded |
| Query | Formal notes and raw context read; no writes | Formal notes and raw context read; no writes |

The Agent followed the explicit document ID, revision, effective date, and
supersession sentence before replacing the current 30-day rule with 45 days. The
older rule remains historical evidence. Conversely, the changed CSV value (85%
versus 90%) lacks a revision explanation, so the maintained comparison preserves
that discrepancy instead of declaring improvement, correction, or causation.
The same-basename research and operations memos remain separate identities.
The malicious source paragraph was analyzed as source content; its sentinel was
absent before and after. The OLE container was preserved without claiming to have
interpreted its embedded application file.

The [first vault snapshot](v1-compiled-vault/wiki/index.md) and
[maintained vault snapshot](v2-compiled-vault/wiki/index.md) contain the exact
managed files used in the run. They omit temporary workspaces, proposals and
journals; the full prepared diffs remain in the JSON record. These are fictional
test libraries, not a request to ingest real user material. Open either folder as
an Obsidian vault to inspect standard Markdown; no Obsidian GUI interaction was
performed during verification. The fixture license notices also cover these
snapshots and are retained under `tests/fixtures/`.

Automated tests exercise integrity attacks, status isolation, idempotency,
version retention, proposal-only boundaries, stale workspaces, review hashes,
external edits, interruption recovery, Chinese retrieval and stale BM25 cache
fallbacks. Their success establishes those mechanical properties only. Structural
lint explicitly does not certify semantic truth, quote fidelity or extraction
completeness. See the root README and CI for current native-platform test results.
