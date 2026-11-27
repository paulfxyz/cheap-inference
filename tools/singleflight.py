#!/usr/bin/env python3
"""
singleflight.py - make identical in-flight requests share ONE model call.

THE PROBLEM
-----------
Three users (or three retries, or three agent branches) ask the same thing within
the same second. A naive client makes three model calls. A single-flight guard
makes ONE call and hands the same answer to all three waiters ("coalescing").
A related trick, DEBOUNCING, drops requests that were superseded before they
started: if the user keeps editing a field, only the last version deserves a
model call.

HOW IT WORKS (threads, standard library only)
---------------------------------------------
  Group.do(key, fn)   the first caller for a key runs fn(); callers arriving while
                      it runs wait for that result instead of starting their own.
                      When it finishes the key is forgotten, so the NEXT request
                      after completion makes a fresh call (this is not a cache;
                      pair it with response_cache.py for that).
  Debouncer(delay)    schedule(key, fn): a new schedule for the same key cancels
                      the previous pending one; only the last runs after `delay`.

CAVEATS
-------
Coalescing assumes that the callers are happy with the SAME answer. Do not
coalesce requests that depend on per-user data; include everything that affects
the answer in the key. If fn raises, every waiter gets the same exception.

WORKED EXAMPLE
--------------
    >>> g = Group(); calls = []
    >>> def work(): calls.append(1); time.sleep(0.2); return "answer"
    >>> results = parallel(lambda: g.do("q", work), n=5)
    >>> results, len(calls)
    (['answer', 'answer', 'answer', 'answer', 'answer'], 1)
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable


class Group:
    """Coalesce concurrent calls that share a key."""

    def __init__(self):
        self._lock = threading.Lock()
        self._inflight: dict[str, dict] = {}  # key -> {"event": Event, "result": ..., "error": ...}

    def do(self, key: str, fn: Callable[[], object]):
        with self._lock:
            slot = self._inflight.get(key)
            leader = slot is None
            if leader:
                slot = {"event": threading.Event(), "result": None, "error": None}
                self._inflight[key] = slot
        if not leader:
            slot["event"].wait()  # a call is already running: wait for its result
            if slot["error"]:
                raise slot["error"]
            return slot["result"]
        try:
            slot["result"] = fn()
        except Exception as e:  # share the failure with every waiter
            slot["error"] = e
            raise
        finally:
            with self._lock:
                del self._inflight[key]  # forget the key: later requests start fresh
            slot["event"].set()
        return slot["result"]


class Debouncer:
    """Run only the LAST scheduled function per key, after `delay` seconds of quiet."""

    def __init__(self, delay: float):
        self.delay = delay
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def schedule(self, key: str, fn: Callable[[], None]) -> None:
        with self._lock:
            old = self._timers.pop(key, None)
            if old:
                old.cancel()  # superseded: this call never reaches the model
            t = threading.Timer(self.delay, fn)
            self._timers[key] = t
            t.start()


def parallel(fn: Callable[[], object], n: int = 5) -> list:
    """Helper for demos and tests: run fn in n threads and collect results."""
    with ThreadPoolExecutor(n) as ex:
        return [f.result() for f in [ex.submit(fn) for _ in range(n)]]
