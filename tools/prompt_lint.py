#!/usr/bin/env python3
"""
prompt_lint.py - find token-wasting patterns in prompts, guides and skills.

A prompt is code you pay for on every run. This linter flags patterns that
inflate cost or hurt cache hits, using only regular expressions and counts, so
it spends no tokens itself.

CHECKS
------
  P1  volatile text near the top (dates, timestamps, UUIDs) - breaks prefix caching
  P2  filler phrases that add tokens and no instruction ("please", "I would like you to")
  P3  repeated lines (same sentence written twice)
  P4  shouting (ALL-CAPS runs): usually a sign of an unclear rule, and it tokenizes poorly
  P5  eager imports of other files (@file.md) that load at session start
  P6  oversized always-loaded text (> --max-tokens)
  P7  long unbroken paragraphs (> 120 words): hard to skim, easy to ignore
  P8  vague output instructions: no length or format limit anywhere in the prompt
  P9  duplicated boilerplate across files (same long line in 2+ files)

Exit code is 1 if any finding is reported, 0 otherwise.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

# Phrases that cost tokens and change nothing about model behaviour.
FILLER = [
    r"\bplease\b", r"\bkindly\b", r"\bi would like you to\b", r"\bit is (very )?important that you\b",
    r"\bmake sure (that )?you\b", r"\bas an ai\b", r"\bin order to\b", r"\bat the end of the day\b",
]
# Things that change on every request; harmful when they sit near the top of a prompt.
VOLATILE = re.compile(
    r"(\b20\d\d-\d\d-\d\d\b|\b\d{1,2}:\d\d(:\d\d)?\b|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\btoday is\b|\bcurrent (date|time)\b)",
    re.I,
)
EAGER_IMPORT = re.compile(r"(^|\s)@[\w./-]+\.(md|txt|json|ya?ml)\b")
OUTPUT_LIMIT = re.compile(r"\b(max(imum)?|at most|no more than|under|exactly|limit)\b.{0,40}\b(words?|lines?|bullets?|sentences?|tokens?|chars?|characters?)\b|\bjson\b|\btable\b|\bformat\b", re.I)


def lint_text(name: str, text: str, max_tokens: int = 1500) -> list[str]:
    """Return findings for one prompt/guide. Each finding is a readable string."""
    out: list[str] = []
    lines = text.splitlines()

    # P1: look only at the first 15 non-empty lines - that is the cache-critical prefix.
    head = [ln for ln in lines if ln.strip()][:15]
    for i, ln in enumerate(head, 1):
        if VOLATILE.search(ln):
            out.append(f"{name}: P1 volatile text in the first lines (line ~{i}): move it below the stable block")
            break

    # P2: filler phrases
    hits = sum(len(re.findall(p, text, re.I)) for p in FILLER)
    if hits >= 3:
        out.append(f"{name}: P2 {hits} filler phrases; delete them, the instruction works without them")

    # P3: repeated lines (ignore very short lines like '---')
    counts = collections.Counter(ln.strip().lower() for ln in lines if len(ln.strip()) > 25)
    for line, n in counts.items():
        if n > 1:
            out.append(f"{name}: P3 line repeated {n}x: \"{line[:60]}\"")

    # P4: shouting
    caps = re.findall(r"\b[A-Z]{5,}(?:\s+[A-Z]{3,}){1,}\b", text)
    if caps:
        out.append(f"{name}: P4 {len(caps)} ALL-CAPS run(s), e.g. \"{caps[0][:40]}\"; state the rule plainly once")

    # P5: eager imports
    for ln in lines:
        if EAGER_IMPORT.search(ln) and not ln.lstrip().startswith("```"):
            out.append(f"{name}: P5 eager import \"{ln.strip()[:60]}\"; link it and read on demand instead")
            break

    # P6: size
    tok = round(len(text) / 4)
    if tok > max_tokens:
        out.append(f"{name}: P6 ~{tok} tokens exceeds {max_tokens}; move detail into on-demand pages")

    # P7: long paragraphs
    for para in re.split(r"\n\s*\n", text):
        if len(para.split()) > 120 and not para.lstrip().startswith(("```", "|", "-")):
            out.append(f"{name}: P7 paragraph of {len(para.split())} words; split or tabulate")
            break

    # P8: nothing constrains the output
    if len(text.split()) > 40 and not OUTPUT_LIMIT.search(text):
        out.append(f"{name}: P8 no output length/format limit; output is the most expensive token")
    return out


def lint_files(paths: list[pathlib.Path], max_tokens: int) -> list[str]:
    findings, seen = [], collections.defaultdict(set)
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        findings += lint_text(str(p), text, max_tokens)
        for ln in text.splitlines():
            if len(ln.strip()) > 80:
                seen[ln.strip()].add(str(p))
    # P9: the same long line in more than one file is boilerplate to factor out.
    for line, files in seen.items():
        if len(files) > 1:
            findings.append(f"{', '.join(sorted(files))}: P9 duplicated line \"{line[:50]}...\"")
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint prompts for token waste.")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--max-tokens", type=int, default=1500)
    a = ap.parse_args(argv)
    files: list[pathlib.Path] = []
    for raw in a.paths:
        p = pathlib.Path(raw)
        files += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    res = lint_files(files, a.max_tokens)
    for r in res:
        print(r)
    print(f"prompt_lint: {len(res)} finding(s) in {len(files)} file(s)")
    return 1 if res else 0


if __name__ == "__main__":
    sys.exit(main())
