# 17. Workflows

A tool does one thing. A workflow chains several tools into a routine you run when a real situation comes up. Eight workflows live in [`workflows/`](../workflows/), each with `--help`, a printed Markdown report, and zero model calls. Two of them also run as GitHub Actions.

## 17.1 Weekly audit
- **When.** Once a week, 20 minutes. Chain: usage report, output audit, waste finder, budget, prompt lint, stale pages, duplicates.
- **Run.** `python workflows/weekly_audit.py --log examples/usage.sample.jsonl --budget examples/budget.json --kb examples/sample-kb --out audit.md`
- **Automate.** `.github/workflows/weekly-audit.yml` runs it every Monday and uploads the report.
- **Then.** Pick the single biggest finding and fix only that one.

## 17.2 Safe downgrade
- **When.** You want to move a task to a cheaper model.
- **Chain.** Eval gate on both models' results, cascade break-even, cost compare.
- **Run.** `python workflows/safe_downgrade.py --baseline a.jsonl --candidate b.jsonl --prices examples/prices.example.json --old big --new small --calls 10000 --input 1500 --output 300`
- **Then.** Ship only if the gate says pass; "inconclusive" means add test cases.

## 17.3 Bulk job planner
- **When.** Thousands of items to classify, label or extract.
- **Chain.** Prefilter (duplicates and rules), micro-batch packing, cost estimate.
- **Run.** `python workflows/bulk_job_planner.py rows.jsonl --prices prices.json --rules rules.json`
- **Then.** Run a 50-item pilot with the eval gate before the full job.

## 17.4 Session hygiene
- **When.** A long agent session is getting heavy.
- **Chain.** History trim, then the restart decision with caching accounted for.
- **Run.** `python workflows/session_hygiene.py history.jsonl --soft 40000 --hard 80000`
- **Then.** Trim first, checkpoint at the soft limit, restart at the hard limit.

## 17.5 Context diet
- **When.** The baseline on every request feels too big.
- **Chain.** Token counts of guide files, tool schema weights, prompt lint, per-month budget with requests per session.
- **Run.** `python workflows/context_diet.py --guide AGENTS.md --tools examples/tools.sample.json --tool-calls examples/tool-calls.sample.jsonl --sessions 300 --requests 20`

## 17.6 Long document Q and A
- **When.** One question about a long document.
- **Chain.** Chunker, BM25 top-k, token estimate against loading it whole.
- **Run.** `python workflows/long_doc_qa.py handbook.md "what is the notice period" --budget 1500`
- **Warning.** If the best passage score is low the workflow says so; load more or use a different method.

## 17.7 Repair failed fields
- **When.** A model filled records and some fields are invalid.
- **Chain.** Validate, build a minimal repair request, merge, repeat a bounded number of times.
- **Run.** `python workflows/repair_failed_fields.py records.json schema.json --max-attempts 2`

## 17.8 Cache decision
- **When.** Deciding whether a large prompt prefix should be cached and how to warm it.
- **Chain.** Token count, cache break-even, wave plan.
- **Run.** `python workflows/cache_decision.py --prefix prompt-prefix.txt --requests 40 --write 1.25 --read 0.1`

## 17.9 GitHub Actions

| File | Trigger | What it does |
| --- | --- | --- |
| `.github/workflows/ci.yml` | push, pull request | Runs the unit tests on Python 3.10 and 3.12 |
| `.github/workflows/cost-gate.yml` | pull request | Fails the pull request if always-loaded files exceed the budget, prompts contain token waste, the knowledge base fails lint, or pages are near duplicates |
| `.github/workflows/weekly-audit.yml` | every Monday, manual | Runs the weekly audit workflow and uploads the report as an artifact |
