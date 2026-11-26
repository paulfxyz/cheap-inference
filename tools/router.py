#!/usr/bin/env python3
"""
router.py - a tiny, transparent "cheap-first" router.

It maps a task description to the lowest rung of the ladder that can plausibly
do the job. It is deliberately rule-based (keywords and size hints) so it costs
ZERO tokens and so you can read, argue with and change every rule. It is a
starting point for your own policy, not an oracle.

THE LADDER (see docs/06-routing-ladder.md)
  0 inline answer          3 one focused agent
  1 one search/fetch       4 parallel fan-out / deep research
  2 a few parallel calls   5 premium model / high effort

Escalation rule: climb one rung at a time, and only with a stated reason.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# Each rule: (rung, reason, regex). Rules are checked from the HIGHEST rung
# downward so that an explicit "deep research" request is never under-served.
RULES = [
    (5, "explicit premium/quality request", r"\b(premium|best model|highest quality|investor|legal review|contract)\b"),
    (4, "wide or deep multi-source work", r"\b(deep research|literature review|compare \d{2,}|all competitors|hundreds of|every (page|file|source))\b"),
    (3, "multi-step single stream", r"\b(draft|write (a|the) (report|brief|spec)|refactor|investigate|audit|plan)\b"),
    (2, "a few lookups", r"\b(compare|versus|vs\.?|check (a )?claim|cross-?check)\b"),
    (1, "single lookup", r"\b(latest|current|today|price of|who is|when did|news|look ?up|search)\b"),
]


def pick_rung(task: str, size_hint: int = 0) -> dict:
    """Return {rung, reason}. size_hint = number of items (files, pages, rows)."""
    text = task.lower()
    for rung, reason, pattern in RULES:
        if re.search(pattern, text):
            # Many items push even a "simple" verb up the ladder.
            if size_hint >= 50 and rung < 4:
                return {"rung": 4, "reason": f"{reason}; {size_hint} items => fan-out"}
            return {"rung": rung, "reason": reason}
    if size_hint >= 50:
        return {"rung": 4, "reason": f"{size_hint} items => fan-out"}
    # Nothing matched: answer inline. Climbing needs a reason; absence of one is the reason to stay.
    return {"rung": 0, "reason": "no escalation signal; answer inline"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Suggest the cheapest viable rung for a task.")
    ap.add_argument("task", help="task description in plain words")
    ap.add_argument("--items", type=int, default=0, help="how many items the task touches")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = pick_rung(args.task, args.items)
    print(json.dumps(out) if args.json else f"rung {out['rung']}: {out['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
