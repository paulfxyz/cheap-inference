#!/usr/bin/env python3
"""
cascade.py - try the cheap model first, accept only if a CHECK passes, else escalate.

THE IDEA
--------
A cascade runs a list of "routes" from cheapest to most capable. After each
answer a deterministic VALIDATOR decides whether to accept it. Cheap and
accepted = you saved money. Cheap and rejected = you paid for a failed try and
still need the next route. So a cascade only pays off when the cheap route is
accepted often enough. `break_even()` computes that threshold.

BREAK-EVEN MATH
---------------
Let c1 = cost of the cheap attempt, c2 = cost of the strong route, p = the
probability the cheap answer is accepted.
    cascade expected cost = c1 + (1 - p) * c2          (you always pay c1)
    direct strong cost    = c2
The cascade wins when  c1 + (1-p)*c2 < c2   <=>   p > c1 / c2.
Example: cheap costs 10% of strong => the cheap route must be accepted more than
10% of the time. Add `validator_cost` if your check itself costs money.

THE VALIDATOR IS THE SAFETY NET
-------------------------------
Without a good validator a cascade just accepts bad answers cheaply. Use checks
that code can do: JSON parses, schema matches, placeholders preserved, the
answer cites a quote that exists, tests pass, length within bounds.

This module is provider-agnostic: a route is any callable `prompt -> str`.
Plug in your own client; the logic here never makes a network call.

WORKED EXAMPLE
--------------
    >>> routes = [("small", lambda p: "not json"), ("big", lambda p: '{"ok": true}')]
    >>> run_cascade("q", routes, validator=is_json, costs={"small": 1, "big": 10})
    {'answer': '{"ok": true}', 'route': 'big', 'spent': 11, 'attempts': ['small:rejected', 'big:accepted']}
    >>> break_even(cheap_cost=1, strong_cost=10)
    0.1
"""
from __future__ import annotations

import json
import sys
from typing import Callable


def is_json(text: str) -> bool:
    """A tiny reusable validator: does the answer parse as JSON?"""
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def break_even(cheap_cost: float, strong_cost: float, validator_cost: float = 0.0) -> float:
    """Minimum acceptance rate p at which cascading beats going straight to the strong route.

    Derivation: c1 + v + (1-p)*c2 < c2  =>  p > (c1 + v) / c2. Capped at 1.0:
    a value of 1.0 means 'never worth it' (the cheap attempt costs as much as the strong one).
    """
    return min(1.0, (cheap_cost + validator_cost) / strong_cost) if strong_cost > 0 else 1.0


def run_cascade(prompt: str, routes: list[tuple[str, Callable[[str], str]]],
                validator: Callable[[str], bool], costs: dict[str, float] | None = None) -> dict:
    """Run routes in order; return the first answer the validator accepts.

    The last route's answer is returned even if rejected (flagged in `attempts`),
    because there is nowhere left to escalate: the caller must decide what to do.
    """
    costs = costs or {}
    spent, attempts = 0.0, []
    answer, name = "", ""
    for i, (name, fn) in enumerate(routes):
        answer = fn(prompt)
        spent += costs.get(name, 0.0)  # every attempt is paid for, accepted or not
        ok = bool(validator(answer))
        attempts.append(f"{name}:{'accepted' if ok else 'rejected'}")
        if ok:
            break
    return {"answer": answer, "route": name, "spent": spent, "attempts": attempts}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Break-even acceptance rate for a model cascade.")
    ap.add_argument("--cheap", type=float, required=True, help="cost of one cheap attempt")
    ap.add_argument("--strong", type=float, required=True, help="cost of one strong attempt")
    ap.add_argument("--validator", type=float, default=0.0, help="cost of one validation")
    ap.add_argument("--accept", type=float, help="your measured acceptance rate, 0..1")
    a = ap.parse_args(argv)
    be = break_even(a.cheap, a.strong, a.validator)
    print(f"break-even acceptance rate: {be:.0%}")
    if a.accept is not None:
        exp = a.cheap + a.validator + (1 - a.accept) * a.strong
        verdict = "cascade wins" if exp < a.strong else "go straight to the strong route"
        print(f"at {a.accept:.0%} acceptance: expected {exp:.3f} vs direct {a.strong:.3f} -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
