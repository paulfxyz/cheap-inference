#!/usr/bin/env python3
"""
long_doc_qa.py - answer a question about a long document without loading all of it.

CHAINS: chunker (passages) -> topk (BM25) -> token estimate

Selects the few passages that matter, prints them as a ready-to-paste context block, and reports
how much of the document you avoided sending. If the best passage scores low, it WARNS and
suggests widening the budget: lexical search cannot see synonyms, so low scores are a signal
to load more, not to trust the pick.

USAGE
    python workflows/long_doc_qa.py handbook.md "what is the refund policy" --budget 800
"""
import argparse
import pathlib

from _common import capture
import topk


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Select passages for a question.")
    ap.add_argument("doc")
    ap.add_argument("question")
    ap.add_argument("--budget", type=int, default=800)
    ap.add_argument("--min-score", type=float, default=2.0, help="below this the match is weak")
    a = ap.parse_args(argv)

    text = pathlib.Path(a.doc).read_text(encoding="utf-8")
    chosen = topk.pick(text, a.question, a.budget)
    full = round(len(text) / 4)
    used = sum(round(len(p) / 4) for _, p in chosen)
    if not chosen:
        print("no passage matched: load the document (or ask a human); do not guess")
        return 1
    print(f"selected {len(chosen)} passage(s): ~{used} of ~{full} tokens ({100 - round(100 * used / max(1, full))}% not sent)")
    if chosen[0][0] < a.min_score:
        print(f"WARNING: best score {chosen[0][0]:.2f} < {a.min_score}: weak match. Widen --budget or load more.")
    print("\n--- context block ---")
    for i, (_, p) in enumerate(chosen, 1):
        print(f"[{i}] {p}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
