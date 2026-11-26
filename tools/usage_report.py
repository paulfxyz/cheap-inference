#!/usr/bin/env python3
"""
usage_report.py - find where your tokens actually go, from a usage log.

You cannot cut what you cannot see. Most providers and agent tools can export
per-request usage. This script reads a simple JSON-lines log, one request per
line, and ranks the biggest spenders so you can attack them first.

LOG FORMAT (one JSON object per line; extra fields are ignored)
    {"task": "weekly digest", "model": "mid-model", "input": 5200, "output": 410, "cached": 4000}

"cached" is optional (input tokens served from a cache). Group with --by task|model.

OUTPUT
------
A table of calls, total tokens, share of the total, average input and the
cache-hit rate per group, then the single most useful hint: the group with
the largest share. Prices are NOT assumed; pass --prices to convert tokens to
cost using the same JSON format as costcalc.py.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys


def aggregate(rows: list[dict], by: str = "task") -> list[dict]:
    """Group rows by a key and compute totals. Returns groups sorted by total tokens, descending."""
    g = collections.defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "cached": 0})
    for r in rows:
        k = str(r.get(by, "(none)"))
        g[k]["calls"] += 1
        g[k]["input"] += int(r.get("input", 0))
        g[k]["output"] += int(r.get("output", 0))
        g[k]["cached"] += int(r.get("cached", 0))
    grand = sum(v["input"] + v["output"] for v in g.values()) or 1
    out = []
    for k, v in g.items():
        total = v["input"] + v["output"]
        out.append({
            "group": k, **v, "total": total,
            "share": total / grand,
            "avg_input": v["input"] / v["calls"],
            "cache_hit": (v["cached"] / v["input"]) if v["input"] else 0.0,
        })
    return sorted(out, key=lambda x: -x["total"])


def hint(groups: list[dict]) -> str:
    """One actionable sentence about the biggest group."""
    if not groups:
        return "no data"
    top = groups[0]
    if top["cache_hit"] < 0.2 and top["avg_input"] > 2000:
        return f"'{top['group']}' sends ~{top['avg_input']:.0f} input tokens per call with little caching: reorder prompts stable-first (chapter 8)."
    if top["output"] > top["input"]:
        return f"'{top['group']}' is output-heavy: cap output length and ask for structured results."
    return f"'{top['group']}' is {top['share']:.0%} of all tokens: start there, one rung lower (chapter 6)."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rank token spend from a JSONL usage log.")
    ap.add_argument("log")
    ap.add_argument("--by", default="task", choices=["task", "model"])
    a = ap.parse_args(argv)
    rows = [json.loads(ln) for ln in pathlib.Path(a.log).read_text(encoding="utf-8").splitlines() if ln.strip()]
    groups = aggregate(rows, a.by)
    print(f"{a.by:<24}{'calls':>6}{'total':>10}{'share':>8}{'avg in':>9}{'cache':>7}")
    for g in groups:
        print(f"{g['group'][:23]:<24}{g['calls']:>6}{g['total']:>10}{g['share']:>8.0%}{g['avg_input']:>9.0f}{g['cache_hit']:>7.0%}")
    print("\nHint:", hint(groups))
    return 0


if __name__ == "__main__":
    sys.exit(main())
