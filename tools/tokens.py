#!/usr/bin/env python3
"""
tokens.py - estimate how many tokens a file or folder will cost when loaded.

WHY THIS EXISTS
---------------
Every file that is always loaded into a model's context (a guide, a memory
summary, a hot cache) is paid for again on EVERY request. You cannot manage
what you do not measure, so this script gives a fast, offline, dependency-free
estimate.

HOW THE ESTIMATE WORKS
----------------------
Real tokenizers differ per model, so no offline number is exact. We use two
well-known rules of thumb and report both:

  * chars / 4      - the usual rule for English prose and Markdown.
  * words * 1.33   - the usual rule of thumb from words (about 3/4 word/token).

Code, JSON, URLs and non-Latin scripts usually tokenize WORSE (more tokens per
character), so treat the result as a lower-leaning estimate for those. If the
optional `tiktoken` package is installed we also print an exact count for a
common encoding; it is never required.

USAGE
-----
    python tools/tokens.py README.md docs/            # files and folders
    python tools/tokens.py --ext .md,.py src/         # filter by extension
    python tools/tokens.py --json docs/               # machine-readable

WORKED EXAMPLE
--------------
    $ python tools/tokens.py templates/AGENTS.md
    file                      kind     chars  ~tok(kind)   ~tok(c/4)  ~tok(w*1.33)
    templates/AGENTS.md       prose       892         223         223           195
    TOTAL                                             223

How to read it: the file would add roughly 223 tokens to every session that
loads it. If it is loaded in 300 sessions a month, that is ~67,000 tokens of
pure overhead before any work happens (budget.py does this multiplication).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # so sibling tools can be imported

# Extensions we treat as text when walking a folder. Binary files are skipped
# because their "token count" is meaningless and reading them can fail.
DEFAULT_EXTS = {".md", ".txt", ".py", ".json", ".yml", ".yaml", ".toml", ".html", ".css", ".js", ".ts"}


# Starting characters-per-token ratios by content kind. English prose is ~4; code, JSON and
# CJK scripts pack fewer characters into each token, so chars/4 UNDER-counts them. These
# are rules of thumb: run tools/token_calibrate.py on your own logs to replace them.
KIND_RATIO = {"prose": 4.0, "code": 3.0, "json": 2.8, "logs": 3.0, "cjk": 1.5}


def estimate_tokens(text: str, ratios: dict | None = None) -> dict:
    """Return the two heuristic estimates (and an exact count if tiktoken exists).

    The two heuristics usually land within ~15% of each other on prose. When
    they diverge a lot the text is probably code or heavy markup.
    """
    chars = len(text)
    words = len(text.split())
    # Content-aware estimate: pick the ratio for this kind of text (see token_calibrate.detect_kind).
    from token_calibrate import detect_kind  # local import keeps the tools independent files
    kind = detect_kind(text)
    ratio = (ratios or KIND_RATIO).get(kind, 4.0)
    result = {
        "kind": kind,
        "tokens_by_kind": round(chars / ratio),
        "chars": chars,
        "words": words,
        "tokens_by_chars": round(chars / 4),
        "tokens_by_words": round(words * 4 / 3),
    }
    # Optional exact count. We import lazily so the script has zero hard
    # dependencies; failing to import is the normal case and is not an error.
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        result["tokens_exact_cl100k"] = len(enc.encode(text))
    except Exception:
        pass
    return result


def iter_files(paths: list[str], exts: set[str]):
    """Yield every text file under the given files/folders, sorted for stable output."""
    for raw in paths:
        p = pathlib.Path(raw)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                # Skip hidden folders such as .git; they are never prompt material.
                if any(part.startswith(".") for part in f.relative_to(p).parts):
                    continue
                if f.is_file() and f.suffix.lower() in exts:
                    yield f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Estimate token cost of files.")
    ap.add_argument("paths", nargs="+", help="files or folders")
    ap.add_argument("--ext", default="", help="comma-separated extensions, e.g. .md,.py")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    ap.add_argument("--calibration", help="JSON from token_calibrate.py (chars per token by kind)")
    args = ap.parse_args(argv)  # argv=None means 'read sys.argv'; tests pass a list instead

    # Normalise user input: accept both 'md' and '.md'; fall back to the default set.
    exts = {e if e.startswith(".") else "." + e for e in args.ext.split(",") if e} or DEFAULT_EXTS
    ratios = json.loads(pathlib.Path(args.calibration).read_text()) if args.calibration else None
    rows = []  # one dict per readable file; reused for both the table and the JSON output
    for f in iter_files(args.paths, exts):
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # unreadable or binary: ignore quietly
        rows.append({"file": str(f), **estimate_tokens(text, ratios)})

    # The chars/4 figure is the headline number; it is the one the budget tools use too.
    total = sum(r["tokens_by_kind"] for r in rows)  # kind-aware figure is the headline now
    if args.json:
        print(json.dumps({"files": rows, "total_tokens_by_chars": total}, indent=2))
        return 0

    width = max((len(r["file"]) for r in rows), default=10)
    print(f"{'file'.ljust(width)}  {'kind':>6}  {'chars':>8}  {'~tok(kind)':>10}  {'~tok(c/4)':>10}  {'~tok(w*1.33)':>12}")
    for r in rows:
        print(f"{r['file'].ljust(width)}  {r['kind']:>6}  {r['chars']:>8}  {r['tokens_by_kind']:>10}  {r['tokens_by_chars']:>10}  {r['tokens_by_words']:>12}")
    print(f"{'TOTAL'.ljust(width)}  {'':>6}  {'':>8}  {total:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
