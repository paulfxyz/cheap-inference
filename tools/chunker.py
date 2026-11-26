#!/usr/bin/env python3
"""
chunker.py - split a big Markdown file into small, self-contained pages.

Small pages mean small reads: a model that needs one section should not have to
open a 30,000-token document. The splitter cuts on headings (the natural
boundaries), then merges tiny neighbours and splits oversized sections on
paragraph breaks, so every output file is close to --target tokens.

Each output page gets frontmatter pointing back to the original source and
a link to its neighbours, so the result drops straight into a kb.py wiki.

USAGE
-----
    python tools/chunker.py big-report.md --out wiki/ --target 800

WORKED EXAMPLE
--------------
    $ python tools/chunker.py big-report.md --out wiki/ --target 800
    wrote 14 page(s) to wiki/
    # wiki/big-report-01-introduction.md ... each ~800 tokens, with
    # frontmatter (title, sources, updated) and "Previous / Next" links, so
    # `kb.py lint` accepts the pages as they are.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import datetime as dt


def tok(s: str) -> int:
    return round(len(s) / 4)


def split_sections(text: str) -> list[str]:
    """Split before every heading line (# to ###). Keeps each heading with its body."""
    # The lookahead (?=...) splits BEFORE each heading without consuming it, so every
    # heading stays attached to the text that follows it.
    parts = re.split(r"(?m)^(?=#{1,3}\s)", text)
    return [p for p in parts if p.strip()]


def split_paragraphs(block: str, target: int) -> list[str]:
    """Break one oversized block on blank lines into pieces of about `target` tokens."""
    pieces, cur = [], ""
    for para in re.split(r"\n\s*\n", block):
        if cur and tok(cur + para) > target:
            pieces.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        pieces.append(cur.strip())
    return pieces


def chunk(text: str, target: int = 800) -> list[str]:
    """Return a list of chunks of roughly `target` tokens each (never empty)."""
    pieces: list[str] = []
    for sec in split_sections(text):
        pieces += split_paragraphs(sec, target) if tok(sec) > target * 1.5 else [sec.strip()]
    # Merge neighbours that are too small to be worth a file.
    # Pass 2: glue tiny sections to a neighbour so we do not create hundreds of 20-token files.
    merged: list[str] = []
    for p in pieces:
        if merged and tok(merged[-1]) < target * 0.4 and tok(merged[-1] + p) <= target * 1.3:
            merged[-1] += "\n\n" + p
        else:
            merged.append(p)
    return merged


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "part"


def write_pages(src: pathlib.Path, out: pathlib.Path, target: int) -> list[pathlib.Path]:
    """Write chunks as wiki pages with frontmatter and prev/next links."""
    out.mkdir(parents=True, exist_ok=True)
    chunks = chunk(src.read_text(encoding="utf-8"), target)
    names = []
    for i, c in enumerate(chunks, 1):
        first = next((ln for ln in c.splitlines() if ln.strip()), "part")
        names.append(f"{slug(src.stem)}-{i:02d}-{slug(first.lstrip('# '))}")
    paths = []
    for i, (c, name) in enumerate(zip(chunks, names)):
        nav = []
        if i > 0:
            nav.append(f"Previous: [[{names[i-1]}]]")
        if i < len(names) - 1:
            nav.append(f"Next: [[{names[i+1]}]]")
        fm = f"---\ntitle: {src.stem} part {i+1}\nsources: {src}\nupdated: {dt.date.today().isoformat()}\n---\n"
        p = out / f"{name}.md"
        p.write_text(fm + c + "\n\n" + " | ".join(nav) + "\n", encoding="utf-8")
        paths.append(p)
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Split a Markdown file into small pages.")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=800, help="target tokens per page")
    a = ap.parse_args(argv)
    paths = write_pages(pathlib.Path(a.source), pathlib.Path(a.out), a.target)
    print(f"wrote {len(paths)} page(s) to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
