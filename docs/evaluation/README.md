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
| [6, final](round-6.json) | 91 | Re-evaluated after tests explicitly adopted UTF-8 for portability |

Every round retains its original JSON, Markdown report, improvement brief,
`start` routing output and official-validator result. Early rounds sampled an
implementation in progress; this history is not a controlled model A/B benchmark.
[The round 1–2 comparison](compare-round-1-round-2.md) records the trigger-cost fix.
Rounds 4–6 used complete copies of the skill, including tests, fixtures, licenses,
Markdown references and templates; only Python caches, `.pyc` and `.DS_Store` were
excluded. No useful source, test or fixture was removed to obtain the score.

## Final evaluated bytes

- [Final original report](final.json), [readable report](final.md),
  [improvement brief](final-brief.json), and [official validation](final-agent-skills.json).
- [Exact source inventory](final-source-inventory.json): 96 files, including the
  origin notice and UTF-8 portability fix. The local source-only snapshot stays in
  the ignored repository `.work/` directory; it is not an additional release payload.
- Tree digest: `5f0848fd63cddd8562cf5bef3e107743247155f0cf02021b2ac404902028c3e2`.
  The inventory documents the canonical path/size/SHA-256 JSON-array digest method.
- After evaluation, the working skill tree was checked byte-for-byte against the
  inventory. Subsequent skill-tree edits require another evaluation and inventory.
  Repository-level README and evidence docs are outside the evaluated skill subtree.

Plugin Eval used the installed CLI at
`openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js`, with its default
metrics and scoring. No custom metric pack, altered rule or score override was used.
The official `skills-ref` validator comes from Agent Skills source commit
`69ef37e9424c0a7ea9dd2293b559e43ec8176379`; it validates frontmatter and naming only.

## Remaining static findings and actual verification

The final report retains two warnings: aggregate deferred resources (including helper
source and test fixtures), and the evaluator's Python complexity heuristic. Both cost
4.5 points. Missing coverage artifacts add a 0.25-point informational deduction; the
reported score rounds 90.75 to 91. The complexity check counts decision words at both
file and function levels, so its number is not a measured runtime complexity bound.
Do not interpret 91 as warning-free or as the evaluator's A grade (which starts at 93).

Estimated discovery/invocation costs are 39/723 tokens. The aggregate deferred estimate
is 47,641 tokens across supporting files; these files are loaded or executed as needed,
not necessarily read together. All budget figures are **static estimates**. No observed
API token-usage dataset or model-accuracy score was attached or claimed.

Actual helper tests and the bounded Agent-authored semantic maintenance exercise are
separate evidence under [verification](../verification/README.md). Consult those
records for executed commands, fixture provenance, coverage limits and platform
results. Passing tests do not convert the static score into semantic accuracy, and
no Obsidian desktop GUI execution is claimed by this evaluation.
