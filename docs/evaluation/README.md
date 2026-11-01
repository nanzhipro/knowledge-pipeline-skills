# Skill evaluation evidence

The final unchanged-rule Plugin Eval score is **91/100 (B)**. The official Agent
Skills reference validator also passes. These results describe static structure,
instruction budgets and heuristic Python checks. They are not a model-quality,
source-fidelity, runtime-correctness or Obsidian-rendering score.

| Round | Static score | Change represented |
| --- | ---: | --- |
| [1](round-1.json) | 68 | Initial instruction surface and helpers still under development |
| [2](round-2.json) | 82 | Narrowed the trigger description; kept workflow constraints and resources |
| [3](round-3.json) | 86 | Meaningful test files became available to the evaluator |
| [4](round-4.json) | 91 | Source-only snapshot after Python formatting and CLI/documentation alignment |
| [5](round-5.json) | 91 | Re-evaluated the snapshot including the standalone skill origin notice |
| [6](round-6.json) | 91 | Re-evaluated after tests explicitly adopted UTF-8 for portability |
| [7, final](round-7.json) | 91 | Native Windows failures prompted byte-preserving logs, LF initialization, explicit SQLite closing, and two regression tests |

Every round retains its original JSON, Markdown report, improvement brief,
`start` routing output and official-validator result. Early rounds sampled an
implementation in progress; this history is not a controlled model A/B benchmark.
[The round 1–2 comparison](compare-round-1-round-2.md) records the trigger-cost fix.
Rounds 4–7 used complete copies of the skill, including tests, fixtures, licenses,
Markdown references and templates; only Python caches, `.pyc` and `.DS_Store` were
excluded. No useful source, test or fixture was removed to obtain the score.

## Final evaluated bytes

- [Final original report](final.json), [readable report](final.md),
  [improvement brief](final-brief.json), and [official validation](final-agent-skills.json).
- [Exact source inventory](final-source-inventory.json): 97 files, including the
  origin notice, UTF-8 portability fix, byte-preserving log regressions and SQLite
  connection-lifecycle fixes. [Round 6 inventory](round-6-source-inventory.json)
  remains as historical evidence. The local source-only snapshot stays in
  the ignored repository `.work/` directory; it is not an additional release payload.
- Tree digest: `edc2e4eb9111c9e13dc43bec20558950b129c85500b77e0a842b7b00c224f82f`.
  The inventory documents the canonical path/size/SHA-256 JSON-array digest method.
- After evaluation, the working skill tree was checked byte-for-byte against the
  inventory. Subsequent skill-tree edits require another evaluation and inventory.
  Repository-level README and evidence docs are outside the evaluated skill subtree.

Plugin Eval used the installed CLI at
`openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js`, with its default
metrics and scoring. No custom metric pack, altered rule or score override was used.
The official `skills-ref` validator comes from Agent Skills source commit
`69ef37e9424c0a7ea9dd2293b559e43ec8176379`; it validates frontmatter and naming only.

## Windows evidence and the seventh round

The [first native CI run](https://github.com/nanzhipro/obsidian-llm-wiki-skill/actions/runs/41268874679)
at commit `ee91eb0c5ffe43190e61b7e7a050236609c860c3` failed on Windows Python
3.10/3.13. Those runtime findings prompted LF-only generated initialization text,
raw-byte-preserving append-only logs (including existing CRLF), and explicit closing
of SQLite connections before file replacement. Two new log-byte regression tests
are included in the final evaluated source. [Round 6–7 comparison](compare-round-6-round-7.md)
records a fresh unchanged-rule evaluation of the modified bytes rather than reusing
the previous score. This static result does not itself establish that the corrected
code passes Windows; native rerun results belong in the separate verification record.

## Remaining static findings and actual verification

The final report retains two warnings: aggregate deferred resources (including helper
source and test fixtures), and the evaluator's Python complexity heuristic. Both cost
4.5 points. Missing coverage artifacts add a 0.25-point informational deduction; the
reported score rounds 90.75 to 91. The complexity check counts decision words at both
file and function levels, so its number is not a measured runtime complexity bound.
Do not interpret 91 as warning-free or as the evaluator's A grade (which starts at 93).

Estimated discovery/invocation costs are 39/723 tokens. The aggregate deferred estimate
is 48,617 tokens across supporting files; these files are loaded or executed as needed,
not necessarily read together. All budget figures are **static estimates**. No observed
API token-usage dataset or model-accuracy score was attached or claimed.

Actual helper tests and the bounded Agent-authored semantic maintenance exercise are
separate evidence under [verification](../verification/README.md). Consult those
records for executed commands, fixture provenance, coverage limits and platform
results. Passing tests do not convert the static score into semantic accuracy, and
no Obsidian desktop GUI execution is claimed by this evaluation.
