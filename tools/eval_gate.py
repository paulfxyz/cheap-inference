#!/usr/bin/env python3
"""
eval_gate.py - never ship a cost change without a (tiny) quality check.

THE RULE
--------
Every cost cut (cheaper model, shorter prompt, fewer examples, lower reasoning
effort) is a bet that quality will not drop. Place the bet against a small
GOLDEN SET: inputs with known good answers or a pass/fail check. Run the old
and the new setup on the same set and compare.

THE STATISTICS, KEPT HONEST
---------------------------
With few examples a difference of a couple of points is noise. This tool uses
the Wilson score interval for each pass rate and only says "safe to adopt" when
the NEW setup's lower bound is not meaningfully below the OLD one (a margin you
choose, default 5 points). It says "inconclusive" when the set is too small to
tell, instead of pretending.

INPUT: two JSON files with a list of 0/1 results per golden example (same order):
    baseline.json  -> [1,1,0,1,...]     candidate.json -> [1,1,1,0,...]

OUTPUT: pass rates with 95% intervals, the paired differences (how often new
wins/loses on the same example), and a verdict: ADOPT, REJECT or INCONCLUSIVE.

WORKED EXAMPLE
--------------
    $ python tools/eval_gate.py baseline.json candidate.json --margin 0.05
    baseline : 92% (95% CI 81%-97%, n=50)
    candidate: 90% (95% CI 79%-96%, n=50)
    paired: candidate better on 2, worse on 3, same on 45
    verdict: INCONCLUSIVE (need more examples to rule out a 5-point drop)
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys


def wilson(passes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a pass rate. Better than +/- sqrt(p(1-p)/n) at small n."""
    if n == 0:
        return 0.0, 1.0
    p = passes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def verdict(base: list[int], cand: list[int], margin: float = 0.05) -> dict:
    """Compare two equal-length 0/1 result lists."""
    if len(base) != len(cand):
        raise ValueError("result lists must have the same length (same golden set, same order)")
    n = len(base)
    pb, pc = sum(base) / n, sum(cand) / n
    lb, ub = wilson(sum(base), n)
    lc, uc = wilson(sum(cand), n)
    better = sum(1 for b, c in zip(base, cand) if c > b)
    worse = sum(1 for b, c in zip(base, cand) if c < b)
    # Adopt only if even the candidate's pessimistic bound is within `margin` of the baseline's pass rate.
    if lc >= pb - margin:
        v = "ADOPT"
    elif uc < pb - margin:
        v = "REJECT"   # even the candidate's optimistic bound is clearly below the baseline
    else:
        v = "INCONCLUSIVE"  # the interval straddles the margin: need more examples
    return {"n": n, "base": (pb, lb, ub), "cand": (pc, lc, uc), "better": better, "worse": worse, "same": n - better - worse, "verdict": v}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Quality gate for a cost-saving change.")
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    ap.add_argument("--margin", type=float, default=0.05, help="largest acceptable drop in pass rate")
    a = ap.parse_args(argv)
    r = verdict(json.loads(pathlib.Path(a.baseline).read_text()), json.loads(pathlib.Path(a.candidate).read_text()), a.margin)
    for name in ("base", "cand"):
        p, lo, hi = r[name]
        print(f"{'baseline' if name == 'base' else 'candidate':<10}: {p:.0%} (95% CI {lo:.0%}-{hi:.0%}, n={r['n']})")
    print(f"paired: candidate better on {r['better']}, worse on {r['worse']}, same on {r['same']}")
    print(f"verdict: {r['verdict']}")
    return {"ADOPT": 0, "INCONCLUSIVE": 1, "REJECT": 2}[r["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
