#!/usr/bin/env python3
"""
topk.py - pick the few passages that matter, instead of loading a whole document.

THE IDEA
--------
For a question about a long document you rarely need all of it. Split it into
passages, score each against the question with a classic lexical formula
(BM25), and send only the top few that fit a token budget. No embeddings, no
model call, no network: the retrieval itself costs zero tokens.

BM25 IN ONE PARAGRAPH
---------------------
A passage scores higher when it contains rare query words (inverse document
frequency, IDF) many times, with diminishing returns for repetition and a
penalty for very long passages. Constants: k1 = 1.5 (repetition saturation),
b = 0.75 (length normalisation).

WHEN IT HURTS
-------------
Lexical search misses synonyms ("car" vs "automobile") and needs the question's
words to appear in the text. Keep a fallback: if the best score is low, widen
the budget or load more.

WORKED EXAMPLE
--------------
    $ python tools/topk.py big-doc.md "refund policy for delayed activation" --budget 600
    picked 3 of 41 passages (~540 tokens, 7% of the document)
    [1] score 7.42  ## Refunds
    ...
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re
import sys


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def passages(text: str, max_words: int = 120) -> list[str]:
    """Split on blank lines, then cut long paragraphs so one passage stays small."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        w = para.split()
        for i in range(0, len(w), max_words):
            chunk = " ".join(w[i : i + max_words])
            if chunk.strip():
                out.append(chunk)
    return out


def bm25(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """BM25 score of every passage for the query."""
    toks = [words(d) for d in docs]
    n = len(docs)
    avg = sum(len(t) for t in toks) / max(1, n)
    q = set(words(query))
    # document frequency: in how many passages does each query word appear?
    df = {w: sum(1 for t in toks if w in t) for w in q}
    scores = []
    for t in toks:
        s = 0.0
        for w in q:
            tf = t.count(w)
            if not tf:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))  # rare words weigh more
            s += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(t) / avg))
        scores.append(s)
    return scores


def pick(text: str, query: str, budget_tokens: int = 600) -> list[tuple[float, str]]:
    """Greedy: best-scoring passages first until the token budget is used. Returns [(score, passage)]."""
    ps = passages(text)
    ranked = sorted(zip(bm25(query, ps), ps), key=lambda x: -x[0])
    chosen, used = [], 0
    for score, p in ranked:
        cost = round(len(p) / 4)
        if score <= 0 or used + cost > budget_tokens:
            continue
        chosen.append((score, p))
        used += cost
    return chosen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Select the most relevant passages under a token budget.")
    ap.add_argument("file")
    ap.add_argument("query")
    ap.add_argument("--budget", type=int, default=600, help="max tokens to select")
    a = ap.parse_args(argv)
    text = pathlib.Path(a.file).read_text(encoding="utf-8")
    total = len(passages(text))
    chosen = pick(text, a.query, a.budget)
    used = sum(round(len(p) / 4) for _, p in chosen)
    share = 100 * used * 4 / max(1, len(text))
    print(f"picked {len(chosen)} of {total} passages (~{used} tokens, {share:.0f}% of the document)")
    for i, (score, p) in enumerate(chosen, 1):
        print(f"[{i}] score {score:.2f}  {p[:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
