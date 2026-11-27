#!/usr/bin/env python3
"""
session_hygiene.py - decide when to trim, checkpoint or restart a long session.

CHAINS: history_trim -> session_budget

For a saved history (JSON list of messages) it:
  1. trims stale tool outputs (history_trim) and reports the saving,
  2. models whether a fresh session would be cheaper from here (session_budget),
  3. prints a three-way recommendation: keep going / trim and continue / checkpoint and restart.

Rule of thumb implemented here (all thresholds are flags you can change):
  - history under --soft tokens                      -> keep going
  - over --soft, trimming gets it under --soft       -> trim and continue
  - still over --hard after trimming                 -> write a checkpoint and start fresh
"""
import argparse
import json
import pathlib

from _common import capture
import history_trim, session_budget


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Trim, checkpoint or restart a long session.")
    ap.add_argument("history")
    ap.add_argument("--soft", type=int, default=20000, help="tokens: start caring")
    ap.add_argument("--hard", type=int, default=60000, help="tokens: restart with a checkpoint")
    ap.add_argument("--per-turn", type=int, default=700)
    ap.add_argument("--remaining-turns", type=int, default=30)
    a = ap.parse_args(argv)

    msgs = json.loads(pathlib.Path(a.history).read_text())
    before = history_trim.est(msgs)
    trimmed = history_trim.trim(msgs)
    after = history_trim.est(trimmed)
    print(f"history: ~{before:,} tokens; after trimming stale tool outputs: ~{after:,}")
    if before < a.soft:
        print("recommendation: keep going (history is small)")
    elif after < a.soft:
        print("recommendation: trim and continue (trimming is enough)")
    elif after > a.hard:
        print("recommendation: write a 200-word checkpoint and start a fresh session")
    else:
        print("recommendation: trim now; plan a checkpoint if the task keeps growing")
    print(capture(session_budget.main, "--turns", str(a.remaining_turns), "--per-turn", str(a.per_turn), "--base", str(after)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
