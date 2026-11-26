#!/usr/bin/env python3
"""
session_budget.py - when should you stop a long session and start fresh?

History is re-sent each turn, so the cost of turn N includes turns 1..N-1.
This model shows the cumulative input tokens of one long session versus the
same work split into fresh sessions that carry only a short summary.

  python tools/session_budget.py --turns 60 --per-turn 700 --base 1500 --summary 400

MODEL
  one long session : turn i sends  base + i * per_turn           input tokens
  split every K    : turn i sends  base + summary + (i mod K) * per_turn,
                     plus a one-off `restart` cost each time a new session starts
                     (re-reading files, re-establishing context). Without this term
                     the model would absurdly recommend a new session every turn.
The script prints both totals and the best K (turns per session) found by
brute force. It ignores caching on purpose, so you see the worst case;
caching lowers the price of the repeated part but not its size.

WORKED EXAMPLE
--------------
    $ python tools/session_budget.py --turns 60 --per-turn 700
    one long session : 1,371,000 input tokens
    best split (K=3) : 244,300 input tokens  (82% fewer)

CAVEAT: a worst-case model. It ignores prompt caching (which makes the repeated
history cheaper per token, not smaller) and assumes each restart costs 2,500
tokens to rebuild context. Change --restart and --summary to match your reality.
"""
from __future__ import annotations

import argparse
import sys


def long_session(turns: int, per_turn: int, base: int) -> int:
    """Total input tokens when the history is never reset."""
    # Turn i re-sends the base context plus the i turns of history accumulated so far,
    # so the total grows quadratically with the number of turns.
    return sum(base + i * per_turn for i in range(1, turns + 1))


def split_sessions(turns: int, per_turn: int, base: int, summary: int, k: int, restart: int = 2500) -> int:
    """Total input tokens when the session restarts every k turns with a summary."""
    total = 0
    for i in range(1, turns + 1):
        # `pos` is the turn's position inside its mini-session (1..k): history only
        # accumulates since the last restart.
        pos = (i - 1) % k + 1  # position inside the current mini-session
        carry = summary if i > k else 0
        if pos == 1 and i > 1:
            total += restart  # a fresh session must re-establish working context
        total += base + carry + pos * per_turn
    return total


def best_k(turns: int, per_turn: int, base: int, summary: int, restart: int = 2500) -> tuple[int, int]:
    """Brute-force the number of turns per session that minimises total input."""
    best = min(range(1, turns + 1), key=lambda k: split_sessions(turns, per_turn, base, summary, k, restart))
    return best, split_sessions(turns, per_turn, base, summary, best, restart)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, required=True)
    ap.add_argument("--per-turn", type=int, required=True, help="tokens added to history each turn")
    ap.add_argument("--base", type=int, default=1500, help="always-loaded tokens per request")
    ap.add_argument("--summary", type=int, default=400, help="tokens of carry-over summary")
    ap.add_argument("--restart", type=int, default=2500, help="one-off tokens to rebuild context in a new session")
    a = ap.parse_args(argv)
    lng = long_session(a.turns, a.per_turn, a.base)
    k, best = best_k(a.turns, a.per_turn, a.base, a.summary, a.restart)
    print(f"one long session : {lng:,} input tokens")
    print(f"best split (K={k}) : {best:,} input tokens  ({100 - round(100 * best / lng)}% fewer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
