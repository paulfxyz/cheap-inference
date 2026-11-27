#!/usr/bin/env python3
"""
preflight.py - catch doomed requests BEFORE you pay for them.

A failed request is still often billed (input tokens were processed), and a retry
pays again. Cheap local checks stop the most common avoidable failures:

  F1  empty or whitespace-only prompt
  F2  prompt (estimated) larger than the model's context window minus the output you reserve
  F3  unresolved template placeholders such as {name} or {{user}} left in the text
  F4  max_tokens larger than the model allows, or zero/negative
  F5  suspicious repetition: the same line repeated many times (a looping agent's signature)
  F6  a secret-looking string (private key header, 'sk-...' style token) in the prompt

Each check is a pure function; run_all() returns the list of problems. Exit code 1 when any
problem is found, so it can sit in front of a job runner.

LIMITS: token counts here are estimates (chars/4). Keep a safety margin (default 10%).

WORKED EXAMPLE
--------------
    $ python tools/preflight.py prompt.txt --context 8000 --max-tokens 1000
    F3 unresolved placeholder: {customer_name}
    preflight: 1 problem(s)
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

PLACEHOLDER = re.compile(r"\{\{?\s*[A-Za-z_][\w.]*\s*\}?\}")
SECRET = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b)")


def run_all(prompt: str, context: int | None = None, max_tokens: int | None = None, max_output_limit: int | None = None, margin: float = 0.10) -> list[str]:
    """Return the list of problems found in a prompt/request."""
    problems = []
    if not prompt.strip():
        problems.append("F1 empty prompt")
    est = round(len(prompt) / 4)
    reserved = max_tokens or 0
    if context and est * (1 + margin) + reserved > context:
        problems.append(f"F2 ~{est} prompt tokens + {reserved} reserved output exceeds the {context}-token window (with {margin:.0%} margin)")
    for m in sorted(set(PLACEHOLDER.findall(prompt))):
        problems.append(f"F3 unresolved placeholder: {m}")
    if max_tokens is not None and (max_tokens <= 0 or (max_output_limit and max_tokens > max_output_limit)):
        problems.append(f"F4 max_tokens {max_tokens} is outside the allowed range")
    lines = collections.Counter(ln.strip() for ln in prompt.splitlines() if len(ln.strip()) > 20)
    for line, n in lines.items():
        if n >= 5:
            problems.append(f"F5 line repeated {n}x: \"{line[:40]}\" (looping agent?)")
    if SECRET.search(prompt):
        problems.append("F6 secret-looking string in the prompt")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-send checks for a prompt.")
    ap.add_argument("prompt_file")
    ap.add_argument("--context", type=int, help="model context window in tokens")
    ap.add_argument("--max-tokens", type=int, help="output tokens you will request")
    ap.add_argument("--max-output-limit", type=int, help="the model's maximum allowed output tokens")
    a = ap.parse_args(argv)
    probs = run_all(pathlib.Path(a.prompt_file).read_text(encoding="utf-8"), a.context, a.max_tokens, a.max_output_limit)
    for p in probs:
        print(p)
    print(f"preflight: {len(probs)} problem(s)")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
