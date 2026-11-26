# 14. Bold claims, with receipts

> A claim you cannot test is marketing. Each claim below ships with the command that checks it.

| # | Claim | Receipt |
| --- | --- | --- |
| 1 | The checks in this repo spend **zero tokens**. | They are plain Python with no network or model calls. Read `tools/*.py`; grep for `import requests` or `http` returns nothing. |
| 2 | A script catches a fabricated quote that a model reviewer may wave through. | `python tools/kb.py --root examples/broken-kb lint` prints `QUOTE NOT IN SOURCE`. |
| 3 | When nothing changed, the nightly ingest costs **nothing**. | `python tools/kb.py status` prints an empty list; the guard in recipe 13.2 exits before any model call. |
| 4 | One volatile line at the top of a prompt can cost you the entire cache. | `python tools/cache_sim.py`: stable-first 97%, timestamp-first 0% (toy model, real shape). |
| 5 | Always-loaded files are a monthly bill, not a one-off. | `python tools/budget.py examples/budget.json` prints tokens per month for loading alone. |
| 6 | Splitting a long session can beat continuing it. | `python tools/session_budget.py --turns 60 --per-turn 700` (a model that ignores caching, so read it as a worst case). |
| 7 | Compacting a log removes most of its characters without losing the failure. | `python tools/compact.py` on any noisy log prints the percentage saved to stderr. |
| 8 | Your guide probably contains filler. | `python tools/prompt_lint.py AGENTS.md` flags it for free. |
| 9 | The whole toolkit has **no required third-party dependencies**. | Every import in `tools/` is from the standard library; `tiktoken` is only tried optionally for an exact count and never needed. |
| 10 | Everything is tested. | `python -m unittest discover -s tests -v` (30 tests) and CI on two Python versions. |

## 14.1 What we do NOT claim

- We do not claim a specific percentage saving for your workload. It depends on your prompts, your caching and your volume. Measure with `usage_report.py` before and after.
- We do not ship real prices. Provider pricing changes; use your own table.
- We do not claim the linter proves facts. It proves that quotes exist in sources.
- We do not claim cheaper always means better. When a lower rung fails, climb.

## 14.2 How to falsify us

Run the receipts on your own data. If a claim does not hold for you, open an issue with the command and the output. A claim that survives is worth keeping; one that does not should be removed.
