#!/usr/bin/env python3
"""
safe_downgrade.py - move a task to a cheaper model WITHOUT guessing.

CHAINS: eval_gate -> cascade.break_even -> costcalc

THE DECISION IN THREE QUESTIONS
-------------------------------
1. Is quality safe?   eval_gate compares pass/fail results of the old and new setup on the
                      same golden set and says ADOPT, REJECT or INCONCLUSIVE.
2. Is a cascade worth it?  if the new route is only sometimes good enough, cascade.break_even
                      tells you the minimum acceptance rate at which "try cheap first" wins.
3. What does it save?  costcalc compares the routes on your workload with YOUR prices.

INPUTS
    --baseline / --candidate  JSON lists of 0/1 results on the same golden set
    --prices                  price table JSON (see examples/prices.example.json)
    --old / --new             route names in that table
    --calls --input --output  the workload
Output: downgrade-decision.md with the verdict and the numbers behind it.
"""
import argparse
import json
import pathlib

from _common import capture, section
import cascade, costcalc, eval_gate


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Evidence-based model downgrade decision.")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--calls", type=int, required=True)
    ap.add_argument("--input", type=int, required=True)
    ap.add_argument("--output", type=int, required=True)
    ap.add_argument("--margin", type=float, default=0.05)
    ap.add_argument("--out", default="downgrade-decision.md")
    a = ap.parse_args(argv)

    base = json.loads(pathlib.Path(a.baseline).read_text())
    cand = json.loads(pathlib.Path(a.candidate).read_text())
    gate = eval_gate.verdict(base, cand, a.margin)

    prices = json.loads(pathlib.Path(a.prices).read_text())
    old_c = costcalc.call_cost(prices["routes"][a.old], a.input, a.output, 0.0)
    new_c = costcalc.call_cost(prices["routes"][a.new], a.input, a.output, 0.0)
    be = cascade.break_even(new_c, old_c)
    saving = 100 - round(100 * new_c / old_c) if old_c else 0

    if gate["verdict"] == "ADOPT":
        rec = f"Switch to '{a.new}': quality held within {a.margin:.0%} and it costs about {saving}% less per call."
    elif gate["verdict"] == "REJECT":
        rec = f"Do not switch outright. Consider a cascade only if '{a.new}' is accepted by your validator more than {be:.0%} of the time."
    else:
        rec = "Inconclusive: add golden examples before deciding (the interval is too wide to rule out a drop)."

    body = [f"# Downgrade decision: {a.old} -> {a.new}\n", f"**Recommendation:** {rec}\n"]
    body.append(section("Quality gate (eval_gate)", capture(eval_gate.main, a.baseline, a.candidate, "--margin", str(a.margin))))
    body.append(section("Cascade break-even", f"new route must be accepted > {be:.0%} of the time to beat going straight to '{a.old}'"))
    body.append(section("Cost comparison (costcalc)", capture(costcalc.main, a.prices, "--calls", str(a.calls), "--input", str(a.input), "--output", str(a.output))))
    pathlib.Path(a.out).write_text("\n".join(body), encoding="utf-8")
    print(rec)
    return {"ADOPT": 0, "INCONCLUSIVE": 1, "REJECT": 2}[gate["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
