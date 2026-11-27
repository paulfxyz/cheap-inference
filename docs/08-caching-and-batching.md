# 8. Caching, ordering and batching

> Principle: do not make the provider recompute text that has not changed.

## 8.1 Prompt caching in one paragraph

Some providers can reuse the work they did on the beginning of your previous request. Matching goes from the first token and stops at the first difference. Cached tokens are typically billed at a lower rate and processed faster. Details (minimum prompt size, how long the cache lives, how you opt in, the discount) vary by provider and change over time, so read their current documentation. Everything here is about arranging your prompts so that you benefit when it is available.

## 8.2 Order is everything

Put stable text first and changing text last:

```
GOOD:  [rules][tools][reference docs] | [today's question]
BAD:   [timestamp][rules][tools][reference docs] | [today's question]
```

One changing token at the start invalidates the entire prefix after it. Run the simulator:

```bash
$ python tools/cache_sim.py
stable-first order : 97% of tokens cacheable
timestamp-first    : 0% of tokens cacheable
```

The numbers come from a toy model with made-up segment sizes, but the shape is real: a single volatile token near the top can cost you the whole benefit.

## 8.2b Caching is not always a win

- Some providers charge a PREMIUM to write to the cache. A prefix that is written and never reused costs more than not caching.
- Caches expire (a time-to-live) and ignore prefixes under a minimum size. A guide trimmed to 255 tokens may be too small to cache at all; trimming and caching pull in different directions.
- Break-even: caching wins when the prefix is reused enough times inside the TTL. `python tools/cache_breakeven.py --prefix-tokens 5000 --write 1.25 --read 0.1` does the arithmetic with your ratios.
- If hundreds of requests share a big prefix, do not start them all at once: nothing is cached yet. Send one warm-up request first and the rest in waves (`tools/wave_plan.py`).

## 8.3 Checklist for cache-friendly prompts

1. Stable instructions first, then stable reference material, then the changing part.
2. No timestamps, request IDs or random order of examples near the top.
3. Keep the order of tools and examples fixed between requests.
4. Append to conversations; do not rewrite earlier turns.
5. Do not edit the system prompt mid-session. Put per-request facts in the user message.
6. If you must include the current date, place it after the stable block.

## 8.4 Estimating the effect on cost

`tools/costcalc.py` models cached tokens with a separate price:

```bash
python tools/costcalc.py examples/prices.example.json \
  --calls 2000 --input 3000 --output 400 --cache-hit 0.6
```

The example prices are placeholders. The point is the relationship: as the cache-hit rate rises, input cost falls; output cost does not change.

## 8.5 Batching

If a job does not need an immediate answer (nightly classification, bulk translation, backfills), many providers offer an asynchronous batch endpoint at a reduced rate in exchange for slower turnaround. Check availability and terms with your provider. In `costcalc.py`, model it with `"multiplier"` on a route.

Good candidates: anything you would run overnight anyway. Poor candidates: interactive work, anything with a human waiting.

## 8.6 Fewer, better calls

- Combine related small questions into one structured request.
- Ask for the answer in the shape you will use (JSON, a table) so no second call is needed to reformat. Note that JSON is often NOT shorter in tokens (keys, quotes and braces repeat) and strict formats can reduce reasoning quality on some tasks; for tabular data compare with `tools/payload_compact.py` and test quality first.
- Cache your own results. If the same input can reasonably reuse the same output (a translation of a fixed string, a classification of a stored record), store it and look it up next time. A dictionary lookup is cheaper than any model, but model output is NOT strictly deterministic, so the cache freezes one sample, good or bad.

## 8.7 A local result cache in 15 lines

```python
import hashlib, json, pathlib

CACHE = pathlib.Path(".cache"); CACHE.mkdir(exist_ok=True)

def cached(fn_name: str, payload: dict, compute):
    """Return a stored result for identical input; compute and store otherwise."""
    key = hashlib.sha256(json.dumps([fn_name, payload], sort_keys=True).encode()).hexdigest()[:20]
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    result = compute()
    f.write_text(json.dumps(result))
    return result
```

Include the model name, sampling settings and prompt version in `payload`, so changing any of them invalidates the stored answers. The full version, with a TTL and atomic writes, is `tools/response_cache.py`.
