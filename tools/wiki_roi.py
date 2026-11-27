#!/usr/bin/env python3
"""
wiki_roi.py - should you build a knowledge base, or just search? A formula, not a folklore number.

Earlier versions of this repository said "below roughly 50 to 100 sources a wiki
is not worth it". Independent review rightly called that threshold arbitrary:
the real answer depends on how big the sources are, how often you ask, and how
often the sources change. This tool replaces the rule of thumb with arithmetic.

MODEL (per month, in tokens)
----------------------------
WITHOUT a wiki, every question loads raw material:
    cost_raw  = questions * tokens_loaded_per_question_from_raw
WITH a wiki, you pay to maintain it and a smaller read per question:
    cost_wiki = changed_sources * ingest_tokens_per_source
              + questions * tokens_loaded_per_question_from_wiki
              + lint_tokens (usually ~0: lint is a script, but fixing errors costs)
The wiki wins when cost_wiki < cost_raw. The tool also prints the break-even
number of questions per month.

All inputs are YOUR measurements or estimates; nothing here is a benchmark.

WORKED EXAMPLE
--------------
    $ python tools/wiki_roi.py --questions 200 --raw-per-q 6000 --wiki-per-q 1500 --changed 20 --ingest 12000
    raw   : 1,200,000 tokens/month
    wiki  :   540,000 tokens/month
    verdict: wiki wins (55% fewer tokens). Break-even: 54 questions/month.
"""
from __future__ import annotations

import argparse
import math
import sys


def compare(questions: int, raw_per_q: int, wiki_per_q: int, changed: int, ingest: int, lint: int = 0) -> dict:
    raw = questions * raw_per_q
    wiki = changed * ingest + questions * wiki_per_q + lint
    saving_per_q = raw_per_q - wiki_per_q
    # Break-even: changed*ingest + lint = q * saving_per_q  =>  q = fixed / saving_per_q
    be = math.ceil((changed * ingest + lint) / saving_per_q) if saving_per_q > 0 else None
    return {"raw": raw, "wiki": wiki, "wins": wiki < raw, "pct": 100 - round(100 * wiki / raw) if raw else 0, "break_even": be}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Knowledge base vs plain search: break-even calculator.")
    ap.add_argument("--questions", type=int, required=True, help="questions per month")
    ap.add_argument("--raw-per-q", type=int, required=True, help="tokens loaded per question without a wiki")
    ap.add_argument("--wiki-per-q", type=int, required=True, help="tokens loaded per question with a wiki")
    ap.add_argument("--changed", type=int, required=True, help="sources that change or arrive per month")
    ap.add_argument("--ingest", type=int, required=True, help="tokens to ingest one source")
    ap.add_argument("--lint", type=int, default=0, help="monthly tokens spent fixing lint errors")
    a = ap.parse_args(argv)
    r = compare(a.questions, a.raw_per_q, a.wiki_per_q, a.changed, a.ingest, a.lint)
    print(f"raw   : {r['raw']:>10,} tokens/month")
    print(f"wiki  : {r['wiki']:>10,} tokens/month")
    if r["wins"]:
        print(f"verdict: wiki wins ({r['pct']}% fewer tokens). Break-even: {r['break_even']} questions/month.")
    else:
        be = f" You would need about {r['break_even']} questions/month." if r["break_even"] else " Even per-question reads are not smaller."
        print(f"verdict: plain search wins at this volume.{be}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
