# Plugin Eval Report: obsidian-llm-wiki

## At a Glance
- Score: 68/100
- Grade: D
- Risk: high
- Checks: 1 fail, 4 warn, 2 info
- Active budget: 799 tokens (moderate)
- Observed usage: not supplied

## Why It Matters
- 1 failing error check are driving the highest-confidence problems.
- 4 warning signals still need cleanup before this feels polished.
- budget is the largest source of score loss at -18.5 points.
- Active budget pressure is high enough that token cost may dominate the user experience.
- No observed usage is attached yet, so budget conclusions are still based on static estimates.

## Fix First
- [fail/error] trigger_cost_tokens is excessive relative to the current Codex baseline. Why: Budget pressure matters because always-loaded or frequently-loaded text can make the workflow feel expensive fast. Fix: Reduce repeated instruction text and move detail into deferred supporting files.
- [warn/warning] deferred_cost_tokens is heavy relative to the current Codex baseline. Why: Budget pressure matters because always-loaded or frequently-loaded text can make the workflow feel expensive fast. Fix: Reduce repeated instruction text and move detail into deferred supporting files.
- [warn/warning] Python source files were found without matching test files. Why: Best-practice gaps usually do not break the workflow immediately, but they make the skill harder to understand and improve. Fix: Add `test_*.py` or `tests/` coverage for the main Python logic.

## Recommended Next Step
- Measure real token usage next
- Why: The static budget looks heavy, so live usage is the fastest way to confirm whether the cost is acceptable.
- Chat request: "Measure the real token usage of this skill."
- Local command: `plugin-eval start ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --request 'Measure the real token usage of this skill.' --format markdown`

## Details
<details>
<summary>Watch next</summary>

- [warn/warning] At least one Python function has high cyclomatic complexity. Why: Complexity findings matter because they increase review cost and make generated or helper code harder to change safely. Fix: Split complex functions into smaller helpers or guard clauses.
- [warn/warning] Some Python lines exceed 120 characters. Why: Readability issues slow engineers down during review, debugging, and follow-up edits. Fix: Wrap long expressions and keep docstrings or SQL fragments easier to scan.
</details>
<details>
<summary>Improvement brief</summary>

- Raise the evaluation from grade D (68/100) with a focus on the highest-signal structural and budget issues first.
- Goal: Reduce repeated instruction text and move detail into deferred supporting files.
- Goal: Split complex functions into smaller helpers or guard clauses.
- Goal: Wrap long expressions and keep docstrings or SQL fragments easier to scan.
- Goal: Add `test_*.py` or `tests/` coverage for the main Python logic.
- Measure: token-usage-observer
- Measure: task-outcome-scorecard
- Measure: latency-efficiency
- Suggested prompt: Use the skill-creator guidance to improve obsidian-llm-wiki. Keep the structure compact and move bulky details into references or scripts. Define success measures with these toolsets: token-usage-observer, task-outcome-scorecard, latency-efficiency. Address trigger_cost_tokens-budget-high: trigger_cost_tokens is excessive relative to the current Codex baseline. Address deferred_cost_tokens-budget-high: deferred_cost_tokens is heavy relative to the current Codex baseline. Address py-complexity-high: At least one Python function has high cyclomatic complexity. Address py-long-lines: Some Python lines exceed 120 characters. Address py-tests-missing: Python source files were found without matching test files.
</details>
<details>
<summary>Budgets and observed usage</summary>

- trigger_cost_tokens: 59 (excessive)
- invoke_cost_tokens: 740 (moderate)
- deferred_cost_tokens: 22890 (heavy)
- total_tokens: 23689 (excessive)

- No observed usage supplied.
</details>
<details>
<summary>Measurement plan</summary>

Combine cost, outcome, and trust signals so you can tell whether the skill or plugin is genuinely helping instead of only looking well-structured on paper.

- Token Usage Observer [high] Measure how many tokens the skill or plugin actually burns in representative runs. Signals: observed_usage_sample_count, observed_input_tokens_avg, observed_total_tokens_avg, estimate_vs_observed_input_ratio. Evidence: Responses API usage logs, Codex-like session exports, JSONL traces captured from local benchmarking harnesses.
- Task Outcome Scorecard [high] Measure whether the skill helps users finish the intended job with fewer retries and less cleanup. Signals: task_success_rate, first_pass_success_rate, retry_rate, human_override_rate. Evidence: Task run logs, Structured user acceptance checklist, Before/after comparison runs on the same prompts.
- Tool Call Audit [medium] Check whether the agent uses the right tools, arguments, and sequencing when the skill is active. Signals: tool_call_success_rate, invalid_tool_argument_rate, recoverable_tool_failure_rate. Evidence: Tool invocation traces, Recorded sessions, Golden-path scenario replays.
- Latency And Efficiency [high] Track whether the skill speeds users up enough to justify its cost. Signals: p50_time_to_first_acceptable_answer_seconds, p95_time_to_task_completion_seconds, tokens_per_successful_run. Evidence: Benchmark harness timings, Manual stopwatch runs on canonical tasks, Responses API timestamps combined with usage logs.
- Human Rubric Review [medium] Capture clarity, trust, and usefulness signals that automated checks will miss. Signals: clarity_score_avg, confidence_score_avg, follow_up_question_rate. Evidence: Reviewer scorecards, Team rubric sheets, Annotated transcripts.
- Regression Suite [medium] Protect the repository behavior that the skill is supposed to improve. Signals: test_pass_rate, lint_pass_rate, regression_escape_count. Evidence: Unit and integration test runs, Coverage deltas, Snapshot or golden-file checks.
</details>
<details>
<summary>Use From Codex Chat</summary>

Start with a natural chat request, then let plugin-eval show the exact local command sequence behind it.

Start with this chat request: "Evaluate this skill."
Why this path: Plugin Eval recommended Evaluate Skill from the current local state for this skill.
Quick local entrypoint: plugin-eval start ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --request 'Evaluate this skill.' --format markdown
Plugin Eval will run first: plugin-eval analyze ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --format markdown

Other chat requests you can use:
- Full Skill Analysis: say "Give me a full analysis of this skill, including benchmark setup." -> plugin-eval analyze ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --format markdown
- Evaluate Skill: say "Evaluate this skill." -> plugin-eval analyze ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --format markdown
- Explain Token Budget: say "Explain the token budget for this skill." -> plugin-eval explain-budget ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --format markdown
- Measure Real Token Usage: say "Measure the real token usage of this skill." -> plugin-eval init-benchmark ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki
- Benchmark With Starter Scenarios: say "Help me benchmark this skill." -> plugin-eval init-benchmark ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki
- Start Here: say "What should I run next?" -> plugin-eval analyze ~/Downloads/知本设计研究/obsidian-llm-wiki-skill/obsidian-llm-wiki --format markdown
</details>
<details>
<summary>Checks</summary>

- [FAIL] trigger_cost_tokens-budget-high: trigger_cost_tokens is excessive relative to the current Codex baseline. Evidence: Value: 59 tokens Baseline samples: skills=12, plugins=60 Remediation: Reduce repeated instruction text and move detail into deferred supporting files.
- [WARN] deferred_cost_tokens-budget-high: deferred_cost_tokens is heavy relative to the current Codex baseline. Evidence: Value: 22890 tokens Baseline samples: skills=12, plugins=60 Remediation: Reduce repeated instruction text and move detail into deferred supporting files.
- [WARN] py-complexity-high: At least one Python function has high cyclomatic complexity. Evidence: Max complexity: 101 Remediation: Split complex functions into smaller helpers or guard clauses.
- [WARN] py-long-lines: Some Python lines exceed 120 characters. Evidence: Long lines: 58 Remediation: Wrap long expressions and keep docstrings or SQL fragments easier to scan.
- [WARN] py-tests-missing: Python source files were found without matching test files. Evidence: Source files: 11 Remediation: Add `test_*.py` or `tests/` coverage for the main Python logic.
- [INFO] coverage-artifacts-unavailable: No coverage artifacts were found for this target. Evidence: obsidian-llm-wiki-skill/obsidian-llm-wiki Remediation: Generate `lcov.info`, `coverage.xml`, or an Istanbul coverage JSON file if you want coverage scoring.
</details>
<details>
<summary>Metrics</summary>

- skill_line_count: 52 lines (good)
- description_length_chars: 214 chars (good)
- relative_link_count: 3 links (good)
- code_fence_count: 0 blocks (good)
- support_file_count: 16 files (good)
- trigger_cost_tokens: 59 tokens (excessive)
- invoke_cost_tokens: 740 tokens (moderate)
- deferred_cost_tokens: 22890 tokens (heavy)
- py_file_count: 11 files (good)
- py_function_count: 6 functions (good)
- py_max_cyclomatic_complexity: 101 score (heavy)
- py_average_function_length: 8.67 lines (good)
- py_max_nesting_depth: 4 levels (moderate)
- py_comment_ratio: 0.001 ratio (moderate)
- py_test_file_count: 0 files (moderate)
- coverage_artifact_count: 0 files (info)
</details>
<details>
<summary>Score details</summary>

- Starting score: 100
- Total deductions: -32.25
- Final score: 68
- Risk: Contains 1 failing error check (trigger_cost_tokens-budget-high).
- Risk: Overall score is below 70, which the evaluator treats as high risk.

- -14 points: trigger_cost_tokens-budget-high [fail/error] trigger_cost_tokens is excessive relative to the current Codex baseline.
- -4.5 points: deferred_cost_tokens-budget-high [warn/warning] deferred_cost_tokens is heavy relative to the current Codex baseline.
- -4.5 points: py-complexity-high [warn/warning] At least one Python function has high cyclomatic complexity.
- -4.5 points: py-long-lines [warn/warning] Some Python lines exceed 120 characters.
- -4.5 points: py-tests-missing [warn/warning] Python source files were found without matching test files.
- -0.25 points: coverage-artifacts-unavailable [info/info] No coverage artifacts were found for this target.

- budget: -18.5 points across 2 checks
- best-practice: -4.5 points across 1 check
- complexity: -4.5 points across 1 check
- readability: -4.5 points across 1 check
- coverage: -0.25 points across 1 check
</details>
