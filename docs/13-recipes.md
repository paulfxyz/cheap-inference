# 13. Recipes

> End-to-end workflows that combine the tools. Each recipe lists the goal, the steps, the commands and how to know it worked.

## 13.1 Recipe: put your guides on a budget (15 minutes)

Goal: stop paying for bloated always-loaded files.

1. `python tools/tokens.py AGENTS.md wiki/hot.md` - get a baseline.
2. `python tools/prompt_lint.py AGENTS.md` - fix every finding.
3. Write `budget.json` with limits (guide 700, hot 250, total 1,500).
4. `python tools/budget.py budget.json` - must exit 0.
5. Add step 4 to CI or a pre-commit hook.

Success: the monthly loading figure printed by `budget.py` dropped, and the check is automatic.

## 13.2 Recipe: an incremental nightly ingest

Goal: cost proportional to change.

1. Create `raw/`, `wiki/`, run `python tools/kb.py index`.
2. Copy `templates/ingest-skill.md` and the two hooks.
3. Nightly job:

```bash
#!/bin/bash
cd ~/knowledge || exit 1
set -eo pipefail
out=$(python3 tools/kb.py status 2>/dev/null) || { echo "status failed" >&2; exit 1; }
[ -z "$out" ] && exit 0           # nothing changed: spend nothing (a failure above is NOT a quiet night)
# start your agent here with the ingest skill and a narrow allow-list
```

4. Review the diff each morning; `git revert` bad runs.

Success: on quiet nights the job exits in milliseconds and no model call happens.

## 13.3 Recipe: audit last month's spend

Goal: find the top three sinks.

1. Export per-request usage to JSONL (`task`, `model`, `input`, `output`, `cached`).
2. `python tools/usage_report.py usage.jsonl --by task`
3. Take the top group; read its hint; apply P41 to the report.
4. Fix one thing, re-run next week, compare.

Success: the top group's share or average input fell, or you can say why it should not.

## 13.4 Recipe: tame a runaway log

Goal: debug without flooding the context.

```bash
./run-tests.sh 2>&1 | python tools/compact.py --head 20 --tail 40
python tools/compact.py build.log --grep "error|fail|panic" --context 3
```

Then use P32. Success: the model sees dozens of lines, not tens of thousands.

## 13.5 Recipe: a 40-source research batch

Goal: synthesis without flooding the main thread.

1. Put sources in `raw/`; `kb.py status` lists them.
2. One worker per source with P21, default or cheaper model.
3. Merge with P22 in the main thread (it only sees summaries).
4. Verify with P23 in a fresh context.
5. Write pages with quote lines; `kb.py lint` must exit 0.
6. Commit.

Success: the main thread contains 40 short summaries, not 40 documents, and every claim has a verified quote.

## 13.6 Recipe: split a giant document

1. `python tools/chunker.py big.md --out wiki/big --target 800`
2. `python tools/kb.py index`
3. `python tools/kb.py lint`

Success: each part is under the page-size rule, neighbours link to each other, and a query opens one part instead of the whole.

## 13.7 Recipe: should I split this session?

```bash
python tools/session_budget.py --turns 60 --per-turn 700 --base 1500 --summary 400
```

Use your own numbers. If the best K is far below your actual turns per session, split earlier and use P31 for the handoff.

## 13.8 Recipe: decide a route for a bulk job

1. `python tools/router.py "translate 400 strings" --items 400`
2. Fill `prices.example.json` with your providers' current prices.
3. `python tools/costcalc.py prices.json --calls 400 --input 800 --output 600`
4. If nobody waits, add a batch route with `"multiplier"`.
5. Add a deterministic validator (placeholders preserved, JSON parses) before accepting results.

## 13.9 Recipe: make prompts cache-friendly

1. Split each prompt into segments: rules, tools, reference, question.
2. Move anything volatile below the stable block.
3. Model it in `tools/cache_sim.py` by editing `demo()`.
4. Re-check `usage_report.py` for a higher cache-hit rate next week.

## 13.10 Recipe: weekly 20-minute habit

1. `python tools/kb.py stale --days 90`
2. `python tools/dedup.py wiki/`
3. `python tools/usage_report.py usage.jsonl`
4. `python tools/budget.py budget.json`
5. Apply P41, pick one change, write it down.

## 13.11 Recipe: safely move a task to a cheaper model

1. Collect 40 or more real inputs and a pass/fail check for each.
2. Record pass/fail for the current model and the cheaper one in two JSONL files.
3. `python workflows/safe_downgrade.py --baseline a.jsonl --candidate b.jsonl --prices prices.json --old big --new small --calls 10000 --input 1500 --output 300`
4. Ship only on "pass". On "inconclusive", add cases and repeat.

## 13.12 Recipe: plan a 10,000-item labelling job

1. `python workflows/bulk_job_planner.py rows.jsonl --prices prices.json --rules rules.json`
2. Run a 50-item pilot, gate it with `eval_gate.py`.
3. Run the packed batches; retry failed IDs with `repair_plan.py`.

## 13.13 Recipe: tame a long agent session

1. `python workflows/session_hygiene.py history.jsonl`
2. Trim stale tool outputs; keep the checkpoint file.
3. Restart with P50 when the workflow says the hard limit is reached.
