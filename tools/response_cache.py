#!/usr/bin/env python3
"""
response_cache.py - a safe local cache for model answers (exact-match, with a TTL).

The cheapest model call is the one you do not make. If the SAME request arrives
again you can serve the stored answer. But a careless cache serves WRONG
answers, so the key must include everything that can change the result:

  * the model name and version alias
  * the full prompt text (after normalisation of trivial whitespace)
  * the sampling settings (temperature, top_p, max_tokens, reasoning effort)
  * your own PROMPT_VERSION string: bump it when you edit instructions

Model output is not strictly deterministic, so a cache freezes ONE sample
(including a bad one). Use it for tasks where any good answer is fine
(classification, extraction, translation of fixed strings) and set a TTL so
stale answers expire. Never cache answers that depend on live data.

STORAGE: one JSON file per key under a folder (default .cache/responses),
plus hit/miss counters, so you can report the real hit rate.

WORKED EXAMPLE
--------------
    >>> c = ResponseCache(".cache/demo", ttl_seconds=3600)
    >>> c.get("small", "classify: hello", {"temperature": 0}, "v1")     # miss -> None
    >>> c.put("small", "classify: hello", {"temperature": 0}, "v1", "greeting")
    >>> c.get("small", "classify:   hello", {"temperature": 0}, "v1")   # whitespace-insensitive hit
    'greeting'
    >>> c.stats()
    {'hits': 1, 'misses': 1, 'hit_rate': 0.5}
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time


class ResponseCache:
    def __init__(self, folder: str = ".cache/responses", ttl_seconds: int = 7 * 86400):
        self.dir = pathlib.Path(folder)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(model: str, prompt: str, params: dict, prompt_version: str) -> str:
        """Stable hash of everything that can change the answer."""
        norm = " ".join(prompt.split())  # collapse whitespace so cosmetic edits still hit
        blob = json.dumps([model, norm, params, prompt_version], sort_keys=True)  # sort_keys: dict order must not matter
        return hashlib.sha256(blob.encode()).hexdigest()[:24]

    def get(self, model: str, prompt: str, params: dict, prompt_version: str, now: float | None = None):
        f = self.dir / f"{self.key(model, prompt, params, prompt_version)}.json"
        now = time.time() if now is None else now
        if f.exists():
            rec = json.loads(f.read_text(encoding="utf-8"))
            if now - rec["t"] <= self.ttl:  # fresh enough
                self.hits += 1
                return rec["answer"]
            f.unlink()  # expired: remove so it cannot be served later
        self.misses += 1
        return None

    def put(self, model: str, prompt: str, params: dict, prompt_version: str, answer: str, now: float | None = None) -> None:
        f = self.dir / f"{self.key(model, prompt, params, prompt_version)}.json"
        # Write to a temp file then rename: os.replace is atomic, so a concurrent reader can never see a
        # half-written file (a race found in review).
        tmp = f.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"t": time.time() if now is None else now, "answer": answer}), encoding="utf-8")
        os.replace(tmp, f)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses, "hit_rate": (self.hits / total) if total else 0.0}
