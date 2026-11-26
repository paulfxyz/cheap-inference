#!/usr/bin/env python3
"""
dedup.py - find near-duplicate pages before a model reads them twice.

Duplicated notes are a hidden tax: the model reads both, may reconcile them
inconsistently, and you pay for both. This script finds likely duplicates with
plain set maths - no model, no tokens.

METHOD: word shingles + Jaccard similarity
------------------------------------------
1. Normalise a page (lower-case, strip Markdown punctuation).
2. Cut it into overlapping windows of k words ("shingles").
3. Jaccard similarity of two shingle sets = |A & B| / |A | B|.
   1.0 means identical, 0.0 means nothing in common.
Pairs above a threshold (default 0.6) are reported.

WORKED EXAMPLE
--------------
    $ python tools/dedup.py wiki/ --threshold 0.6
    0.912  wiki/pricing.md  <->  wiki/prices-old.md
    1 near-duplicate pair(s) among 48 page(s)

Tip: the exit code is 1 when pairs are found, so it works as a CI gate.
Lower --threshold (0.4) to find looser overlaps; raise -k to be stricter.
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import re
import sys


def shingles(text: str, k: int = 4) -> set[str]:
    """Return the set of k-word windows of the normalised text."""
    # [a-z0-9']+ drops punctuation and Markdown syntax, so '**Cost**:' and 'cost' match.
    words = re.findall(r"[a-z0-9']+", text.lower())
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two sets; defined as 0.0 when both are empty."""
    if not a and not b:
        return 0.0
    # Intersection over union: 1.0 = identical sets, 0.0 = nothing shared.
    return len(a & b) / len(a | b)


def find_duplicates(files: dict[str, str], threshold: float = 0.6, k: int = 4):
    """Return [(score, name_a, name_b)] for every pair at or above threshold, best first."""
    # Pre-compute each page's shingle set once; comparing sets is then cheap set arithmetic.
    sets = {name: shingles(text, k) for name, text in files.items()}
    pairs = []
    # combinations() gives each unordered pair exactly once: O(n^2), fine for
    # a few thousand notes; use MinHash if you ever reach hundreds of thousands.
    for (na, sa), (nb, sb) in itertools.combinations(sets.items(), 2):
        score = jaccard(sa, sb)
        if score >= threshold:
            pairs.append((round(score, 3), na, nb))
    return sorted(pairs, reverse=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Report near-duplicate Markdown pages.")
    ap.add_argument("folder")
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("-k", type=int, default=4, help="shingle size in words")
    args = ap.parse_args(argv)
    files = {str(p): p.read_text(encoding="utf-8") for p in sorted(pathlib.Path(args.folder).rglob("*.md"))}
    pairs = find_duplicates(files, args.threshold, args.k)
    for score, a, b in pairs:
        print(f"{score:.3f}  {a}  <->  {b}")
    print(f"{len(pairs)} near-duplicate pair(s) among {len(files)} page(s)")
    return 1 if pairs else 0


if __name__ == "__main__":
    sys.exit(main())
