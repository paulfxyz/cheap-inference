#!/usr/bin/env python3
"""
output_audit.py - find where OUTPUT (and hidden reasoning) tokens go.

Output tokens are usually the priciest tokens, and "thinking" or "reasoning"
tokens are billed as output on most providers even though you never read them.
A task that returns 20 words can still burn thousands of reasoning tokens.

LOG FORMAT (JSON lines; same file as usage_report.py, plus two optional fields)
    {"task":"summary","input":3000,"output":900,"reasoning":700,"max_output":1000}

WHAT IT REPORTS, per task
    avg output, avg reasoning, the share of output that is hidden reasoning,
    and 'near cap' = how often output hit >= 95% of max_output (a sign the
    answer was cut off OR the cap is far too generous, depending on context).
It then prints one suggestion per task.

WORKED EXAMPLE
--------------
    $ python tools/output_audit.py examples/usage.sample.jsonl
    task             calls  avg out  avg reason  reason%   suggestion
    weekly digest        2      395           0       0%   ok
    translate            1      700           0       0%   ok
    support triage       1      150           0       0%   ok
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys


def audit(rows: list[dict]) -> list[dict]:
    """Group by task and compute averages. Pure function for easy testing."""
    g = collections.defaultdict(list)
    for r in rows:
        g[str(r.get("task", "(none)"))].append(r)
    out = []
    for task, rs in g.items():
        n = len(rs)
        out_tok = sum(int(r.get("output", 0)) for r in rs) / n
        reason = sum(int(r.get("reasoning", 0)) for r in rs) / n
        # Reasoning is billed as output, so its share of total output spend is reason / (output + reasoning).
        # NOTE: some providers already include reasoning inside `output`; adjust the log to match yours.
        pct = reason / (out_tok + reason) if (out_tok + reason) else 0.0
        near = sum(1 for r in rs if r.get("max_output") and int(r.get("output", 0)) >= 0.95 * int(r["max_output"]))
        if pct > 0.5:
            tip = "mostly hidden reasoning: lower reasoning effort for this task"
        elif near / n > 0.3:
            tip = "often hits the cap: raise it or ask for a shorter format"
        elif out_tok > 800:
            tip = "long outputs: ask for answer-first, a table, or a diff"
        else:
            tip = "ok"
        out.append({"task": task, "calls": n, "avg_out": out_tok, "avg_reason": reason, "reason_pct": pct, "suggestion": tip})
    return sorted(out, key=lambda x: -(x["avg_out"] + x["avg_reason"]) * x["calls"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit output and reasoning token spend per task.")
    ap.add_argument("log")
    a = ap.parse_args(argv)
    rows = [json.loads(ln) for ln in pathlib.Path(a.log).read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"{'task':<22}{'calls':>6}{'avg out':>9}{'avg reason':>12}{'reason%':>9}   suggestion")
    for r in audit(rows):
        print(f"{r['task'][:21]:<22}{r['calls']:>6}{r['avg_out']:>9.0f}{r['avg_reason']:>12.0f}{r['reason_pct']:>9.0%}   {r['suggestion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
