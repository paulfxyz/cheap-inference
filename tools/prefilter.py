#!/usr/bin/env python3
"""
prefilter.py - do the free part in code BEFORE paying a model: normalise, dedupe, rule-match.

THE IDEA
--------
In bulk jobs (classification, extraction, translation of many rows) a large
share of rows are (a) exact duplicates after trivial normalisation, or
(b) decidable by a simple rule (an empty string, a known keyword, a number).
Sending those to a model is pure waste. This tool splits your rows into:

  * RULED    - answered by a rule you wrote; no model needed
  * UNIQUE   - needs a model, but only ONE representative per distinct input
  * the map from every original row back to its answer, so results can be
    expanded to the full list afterwards (`expand`).

RULES FILE (JSON): a list of {"pattern": regex, "label": str}. First match wins.

WORKED EXAMPLE
--------------
    $ python tools/prefilter.py rows.txt --rules rules.json
    rows: 1000  ruled: 220  duplicates collapsed: 410  to send to a model: 370
    (63% fewer model calls)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


def normalise(s: str) -> str:
    """Canonical form used ONLY for matching duplicates: lower-case, collapsed whitespace."""
    return " ".join(s.lower().split())


def split(rows: list[str], rules: list[dict]) -> dict:
    """Partition rows into ruled / unique-to-send, and keep an index map for expansion."""
    compiled = [(re.compile(r["pattern"], re.I), r["label"]) for r in rules]
    ruled: dict[int, str] = {}        # row index -> label from a rule
    first_seen: dict[str, int] = {}   # normalised text -> index of its representative row
    rep_of: dict[int, int] = {}       # duplicate row index -> representative index
    for i, row in enumerate(rows):
        for rx, label in compiled:
            if rx.search(row):
                ruled[i] = label
                break
        else:  # no rule matched: candidate for the model, but dedupe first
            key = normalise(row)
            if key in first_seen:
                rep_of[i] = first_seen[key]
            else:
                first_seen[key] = i
    to_send = sorted(first_seen.values())
    return {"ruled": ruled, "rep_of": rep_of, "to_send": to_send, "n": len(rows)}


def expand(plan: dict, answers: dict[int, str]) -> list[str]:
    """Rebuild one answer per original row from rule labels + answers for the sent rows."""
    out = []
    for i in range(plan["n"]):
        if i in plan["ruled"]:
            out.append(plan["ruled"][i])
        else:
            out.append(answers[plan["rep_of"].get(i, i)])  # a duplicate reuses its representative's answer
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Collapse duplicates and apply rules before a bulk model job.")
    ap.add_argument("rows", help="text file, one row per line")
    ap.add_argument("--rules", help="JSON list of {pattern,label}")
    a = ap.parse_args(argv)
    rows = pathlib.Path(a.rows).read_text(encoding="utf-8").splitlines()
    rules = json.loads(pathlib.Path(a.rules).read_text()) if a.rules else []
    p = split(rows, rules)
    sent = len(p["to_send"])
    saved = 100 - round(100 * sent / max(1, len(rows)))
    print(f"rows: {len(rows)}  ruled: {len(p['ruled'])}  duplicates collapsed: {len(p['rep_of'])}  to send to a model: {sent}")
    print(f"({saved}% fewer model calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
