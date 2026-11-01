# Combined-repository Skill evaluation

The repository contains independently invokable Skills; it is not being scored as a
plugin without a plugin manifest. Each Skill is assessed on its own complete
source-only distribution using the unmodified installed Plugin Eval rules.

All three Skills passed their independent static gate on unchanged complete source
snapshots. The [machine summary](summary.json) records each score and digest. This
is one part of the migration gate; native execution and backup/release verification
remain separate evidence.

| Skill | Static score | Official Agent Skills | Source files |
| --- | ---: | --- | ---: |
| [anydoc-markdown](anydoc-markdown/round-1/plugin-eval.md) | 95 / A | Pass | 60 |
| [obsidian-llm-wiki](obsidian-llm-wiki/round-1/plugin-eval.md) | 91 / B | Pass | 97 |
| [knowledge-pipeline](knowledge-pipeline/round-1/plugin-eval.md) | 95 / A | Pass | 5 |

Each component directory preserves the original `start.json`, `plugin-eval.json`,
`improvement-brief.json`, readable report, official validation result, complete
path/size/SHA-256 inventory and concise summary. Sources and frozen snapshots were
compared again after evaluation. Runtime code, tests and fixtures are included;
only compiled Rust `target`, Python caches, `.pyc`, `.DS_Store` and `.git` are excluded.
No useful fixture or documentation was removed to increase the score.

The original component histories and pre-migration reports remain separate from
these fresh assessments. See [component relocation](../../migration/component-relocation.json)
for the intentional repository-address updates and preserved source ancestry.
These evaluations cover the changed delivery bytes in the new directory layout.

## Method and scope

Commands, for each frozen Skill snapshot:

```text
node <installed-plugin-eval>/scripts/plugin-eval.js start <skill-snapshot> --request "Evaluate this skill." --format json --output start.json
node <installed-plugin-eval>/scripts/plugin-eval.js analyze <skill-snapshot> --format json --output plugin-eval.json --brief-out improvement-brief.json
node <installed-plugin-eval>/scripts/plugin-eval.js report plugin-eval.json --format markdown --output plugin-eval.md
skills-ref validate <skill-snapshot>
```

Plugin Eval is the installed `plugin-eval/0.1.2` package; its result schema reports
CLI version 0.1.0. No custom metric pack or score override was used. Official
`skills-ref` is pinned to Agent Skills source commit
`69ef37e9424c0a7ea9dd2293b559e43ec8176379`; it validates naming/frontmatter, not
runtime behavior or document meaning.

AnyDoc retains an extra-document heuristic warning because a nested fixture
`README.md` preserves the upstream test provenance. Obsidian Wiki retains deferred
resource-size and Python complexity warnings. Both have an informational coverage
artifact deduction. The coordinator retains a trigger-phrasing warning: the heuristic
does not recognize its clear "Use for ..." wording as the recommended "Use when ..."
form. It has no helper implementation, so missing code-coverage artifacts do not
establish a runtime defect. All unchanged-rule scores remain strictly above 90
without changing rules, dropping resources or hiding outstanding findings.

All scores and token figures are **static estimates**, not observed-token usage,
model accuracy, source fidelity, GUI rendering or successful maintenance rates.
Native execution, real conversion-to-Wiki handoff, backup preservation, Release
verification and migration/deletion state are recorded separately. A passing
static score alone does not establish that those other operations succeeded.

## Independent instruction-routing review

A separate [routing review](routing-review.json) inspected the new coordinator and
its declared child contracts. It checked conversion-only, preconverted intake,
end-to-end, read-only query/lint, requested answer archiving, preparation-only and
missing-child boundaries. This is a bounded review of the instructions, not an
executed Agent success rate. The migration's real Agent forward exercise is separate.

Final source tree digests:

- AnyDoc: `b17debb68fd1260fb05e24d5bc1994d41d760d8ca08299beeba5445020c0e3bd`
- Obsidian Wiki: `e3efc1e5a7432ae63fb30e456ad2d5cf07ea8afbe709efbeae0d27b35d6efbf1`
- Coordinator: `4186021404b09df3c2b602906ab4f399c4b1040d8ac1422ddf4621de33e40bb7`

Each complete working component was compared again with its source inventory after
all three evaluations. Any later Skill byte changes require another assessment and
updated inventory before using this static gate for migration completion.
