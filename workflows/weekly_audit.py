#!/usr/bin/env python3
"""
weekly_audit.py - the 20-minute weekly cost review, as one command.

CHAINS: usage_report -> output_audit -> waste_finder -> budget -> prompt_lint -> kb stale -> dedup

WHY A WORKFLOW
--------------
Savings decay: prompts grow, new tools get added, a loop sneaks in. A short, regular
review catches that early. This script gathers every signal in one Markdown report so the
review is reading, not assembling. It changes nothing; it only reports.

USAGE
    python workflows/weekly_audit.py --log usage.jsonl --budget budget.json --kb ./knowledge --prompts AGENTS.md
Every input is optional; sections without input are skipped. Output: weekly-audit.md
"""
import argparse
import pathlib
import datetime as dt

from _common import ROOT, capture, section
import usage_report, output_audit, waste_finder, budget, prompt_lint, kb, dedup


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Weekly cost review report.")
    ap.add_argument("--log", help="JSONL usage log")
    ap.add_argument("--budget", help="budget.json for always-loaded files")
    ap.add_argument("--base", default=".", help="folder the budget file paths are relative to")
    ap.add_argument("--kb", help="knowledge-base root (raw/ and wiki/)")
    ap.add_argument("--prompts", nargs="*", default=[], help="prompt/guide files to lint")
    ap.add_argument("--out", default="weekly-audit.md")
    a = ap.parse_args(argv)

    parts = [f"# Weekly cost audit - {dt.date.today().isoformat()}\n"]
    if a.log:
        parts.append(section("Where tokens go (usage_report)", capture(usage_report.main, a.log)))
        parts.append(section("Output and reasoning (output_audit)", capture(output_audit.main, a.log)))
        parts.append(section("Repeats, retries, loops (waste_finder)", capture(waste_finder.main, a.log)))
    if a.budget:
        parts.append(section("Always-loaded budget (budget)", capture(budget.main, a.budget, "--base", a.base)))
    if a.prompts:
        parts.append(section("Prompt hygiene (prompt_lint)", capture(prompt_lint.main, *a.prompts)))
    if a.kb:
        parts.append(section("Stale pages (kb stale)", capture(kb.main, "--root", a.kb, "stale", "--days", "90")))
        parts.append(section("Near-duplicates (dedup)", capture(dedup.main, str(pathlib.Path(a.kb) / "wiki"))))
    parts.append("## This week's one change\n\nPick the single biggest finding above, change one thing, and re-run next week.\n")
    pathlib.Path(a.out).write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {a.out} ({len(parts) - 2} sections)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
