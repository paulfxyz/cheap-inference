#!/usr/bin/env python3
"""
budget.py - audit your ALWAYS-LOADED context against a budget.

THE IDEA
--------
Some files are loaded into the model on every single session: the project
guide (AGENTS.md / CLAUDE.md), a hot cache, memory summaries, skill
descriptions. Their cost is multiplied by the number of requests, so a
2,000-token guide that is read 500 times costs the same as a 1,000,000-token
document read once.

This script reads a small JSON "budget file" that lists those files with a
per-file limit and a total limit, then reports which ones are over budget and
what the loading bill looks like for N sessions.

BUDGET FILE FORMAT (see examples/budget.json)
---------------------------------------------
{
  "total_limit_tokens": 1500,
  "sessions_per_month": 300,
  "files": [ {"path": "AGENTS.md", "limit_tokens": 700}, ... ]
}

EXIT CODE
---------
0 when everything fits, 2 when anything is over budget. That makes it usable
as a CI check or a git pre-commit hook.

WORKED EXAMPLE
--------------
    $ python tools/budget.py examples/budget.json
    ok       templates/AGENTS.md        223 / 700
    ok       templates/hot.md            32 / 250
    ok       TOTAL                      255 / 1500
    Loading cost: ~76,500 tokens/month over 300 sessions

How to read it: 255 tokens x 300 sessions = 76,500 tokens per month spent on
loading alone. Shrinking the guide by 100 tokens saves 30,000 tokens a month
here, with no change in the quality of any single answer.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Reuse the estimator so numbers agree across tools.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tokens import estimate_tokens  # noqa: E402


def audit(budget: dict, base: pathlib.Path) -> dict:
    """Compute per-file and total usage. Pure function: easy to unit test."""
    rows, total = [], 0
    for entry in budget.get("files", []):
        path = base / entry["path"]
        if not path.exists():
            # A missing file costs nothing, but silently ignoring it would hide typos.
            rows.append({"path": entry["path"], "tokens": 0, "limit": entry.get("limit_tokens"), "status": "MISSING"})
            continue
        tokens = estimate_tokens(path.read_text(encoding="utf-8"))["tokens_by_chars"]
        limit = entry.get("limit_tokens")
        # Per-file limits catch one bloated file even when the total still fits.
        status = "OVER" if (limit is not None and tokens > limit) else "ok"
        total += tokens
        rows.append({"path": entry["path"], "tokens": tokens, "limit": limit, "status": status})

    total_limit = budget.get("total_limit_tokens")
    sessions = budget.get("sessions_per_month", 0)
    return {
        "rows": rows,
        "total_tokens": total,
        "total_limit": total_limit,
        "total_status": "OVER" if (total_limit is not None and total > total_limit) else "ok",
        # The number that actually matters: tokens re-sent every month just to
        # load static context, before any real work happens.
        "monthly_loading_tokens": total * sessions,
        "sessions_per_month": sessions,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check always-loaded files against a token budget.")
    ap.add_argument("budget", help="path to budget JSON")
    ap.add_argument("--base", default=".", help="folder the file paths are relative to")
    args = ap.parse_args(argv)

    budget = json.loads(pathlib.Path(args.budget).read_text(encoding="utf-8"))
    report = audit(budget, pathlib.Path(args.base))

    for r in report["rows"]:
        lim = "-" if r["limit"] is None else r["limit"]
        print(f"{r['status']:<8} {r['path']:<40} {r['tokens']:>7} / {lim}")
    print(f"{report['total_status']:<8} {'TOTAL':<40} {report['total_tokens']:>7} / {report['total_limit']}")
    print(f"Loading cost: ~{report['monthly_loading_tokens']:,} tokens/month over {report['sessions_per_month']} sessions")

    # Exit code 2 = something is over budget; CI and pre-commit hooks key off this.
    bad = report["total_status"] == "OVER" or any(r["status"] in ("OVER", "MISSING") for r in report["rows"])
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
