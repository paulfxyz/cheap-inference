#!/usr/bin/env python3
"""
schema_diet.py - weigh the tool/function schemas you send on every request.

WHY THIS MATTERS
----------------
Agent setups often send dozens of tool (function / MCP) definitions with EVERY
request. Each definition is JSON: a name, a description and a parameter schema.
A modest set can weigh thousands of tokens, which is more than a whole project
guide, and it is paid for on every single call, used or not. Two cheap fixes:

  1. Remove tools the task never needs (load tool sets per task, not globally).
  2. Shorten verbose descriptions and drop optional parameters nobody uses.

WHAT THIS TOOL DOES
-------------------
Reads a JSON file that is a list of tool definitions (OpenAI-style
{"type":"function","function":{...}} or flat {"name","description","parameters"}),
estimates the tokens of each, and (optionally) reads a usage log to flag tools
that were never called. It prints a table ranked by weight and the tokens you
would save per request by dropping the unused ones.

USAGE LOG FORMAT (optional, JSON lines): {"tool": "search_web"} per call.

WORKED EXAMPLE
--------------
    $ python tools/schema_diet.py examples/tools.sample.json --calls examples/tool-calls.sample.jsonl
    tool               ~tokens   calls   verdict
    run_sql                 66       0   unused: drop or load on demand
    search_web              52       3   keep
    Total: 118 tokens per request; 66 saved by dropping 1 unused tool(s)
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys


def tool_name(t: dict) -> str:
    """Return the tool's name for both the nested and the flat schema styles."""
    return (t.get("function") or t).get("name", "?")


def tool_tokens(t: dict) -> int:
    """Estimate tokens of one definition by serialising it compactly (chars / 4).

    Compact separators matter: providers tokenise the JSON they receive, so
    whitespace you add for readability can be real cost if you send it as-is.
    """
    return round(len(json.dumps(t, separators=(",", ":"))) / 4)


def analyse(tools: list[dict], calls: collections.Counter | None = None) -> dict:
    """Rank tools by weight and mark never-called ones. Pure function: easy to test."""
    rows = []
    for t in tools:
        name = tool_name(t)
        n = calls.get(name, 0) if calls is not None else None
        if n is None:
            verdict = "no usage data"
        elif n == 0:
            verdict = "unused: drop or load on demand"
        else:
            verdict = "keep"
        rows.append({"tool": name, "tokens": tool_tokens(t), "calls": n, "verdict": verdict})
    rows.sort(key=lambda r: -r["tokens"])
    total = sum(r["tokens"] for r in rows)
    saved = sum(r["tokens"] for r in rows if r["verdict"].startswith("unused"))
    return {"rows": rows, "total": total, "saved": saved, "unused": sum(1 for r in rows if r["verdict"].startswith("unused"))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Weigh tool schemas and flag unused ones.")
    ap.add_argument("tools", help="JSON file: a list of tool definitions")
    ap.add_argument("--calls", help="JSONL usage log with one {'tool': name} per call")
    a = ap.parse_args(argv)
    tools = json.loads(pathlib.Path(a.tools).read_text(encoding="utf-8"))
    calls = None
    if a.calls:
        # Counter tallies how many times each tool name appears in the log.
        calls = collections.Counter(json.loads(ln)["tool"] for ln in pathlib.Path(a.calls).read_text().splitlines() if ln.strip())
    rep = analyse(tools, calls)
    print(f"{'tool':<20}{'~tokens':>8}{'calls':>8}   verdict")
    for r in rep["rows"]:
        print(f"{r['tool']:<20}{r['tokens']:>8}{str(r['calls']) if r['calls'] is not None else '-':>8}   {r['verdict']}")
    print(f"Total: {rep['total']} tokens per request; {rep['saved']} saved by dropping {rep['unused']} unused tool(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
