# 16. Advanced techniques (version 2.1.0)

Twenty-one new tools, one per technique. All use only the Python standard library, none calls a model or the network (a test proves it), and every file starts with a worked example you can run. For each technique: the problem, how the tool works, the risk, and the command.

Every command below runs from the repository root. Prices are always passed in by you; the repository ships no real prices.

## 16.1 Shrink what is sent on every request

### Tool schema diet: `schema_diet.py`
- **Problem.** Function and tool definitions are sent with every request. Fifty tools with long descriptions can outweigh the prompt itself, and most are never called.
- **How.** Estimates the tokens of each schema, ranks them, and (with a call log) flags tools that were never called.
- **Risk.** A rarely used tool may be critical when it is needed. Keep a short list of never-remove tools, and prefer loading a tool on demand over deleting it.
- **Run.** `python tools/schema_diet.py examples/tools.sample.json --calls examples/tool-calls.sample.jsonl`

### Payload compaction: `payload_compact.py`
- **Problem.** JSON repeats every key on every row.
- **How.** Converts a list of records to a header plus delimited rows and compares token estimates of both forms.
- **Risk.** Values with delimiters or nested structure need quoting. The tool reports the saving; it can be small or negative for short lists, so measure before switching.
- **Run.** `python tools/payload_compact.py records.json`

### Few-shot pruning: `fewshot_prune.py`
- **Problem.** Examples in a prompt are paid for on every request, and ten are rarely better than three.
- **How.** Takes a matrix of which test cases each example fixes, then greedily keeps the smallest set with the same coverage.
- **Risk.** Coverage is measured on YOUR test cases. If they are thin, the pruning is blind. Re-run the eval gate (16.6) after pruning.
- **Run.** `python tools/fewshot_prune.py matrix.json --max 4`

### History trimming: `history_trim.py`
- **Problem.** Old tool outputs sit in the history and are re-sent every turn.
- **How.** Keeps the last N turns intact, replaces older large tool results with a one-line stub, and can write the dropped detail to a checkpoint file so nothing is lost.
- **Risk.** The model may need a stubbed result later. The checkpoint makes it recoverable; keep it.
- **Run.** `python tools/history_trim.py chat.jsonl --keep-last 6 --checkpoint dropped.md --out trimmed.jsonl`

### Better token estimates: `tokens.py`, `token_calibrate.py`
- **Problem.** `chars / 4` suits English prose and under-counts code, JSON and non-Latin text.
- **How.** `tokens.py` now picks a ratio by content kind. `token_calibrate.py` measures your own ratio from a log that holds both characters and provider-reported tokens, and saves it for `tokens.py --calibration`.
- **Risk.** Still an estimate. Your provider's usage numbers are the truth.
- **Run.** `python tools/token_calibrate.py examples/calibration.sample.jsonl --out calib.json`

## 16.2 Pay a model only for what needs a model

### Prefilter: `prefilter.py`
- **Problem.** Bulk jobs often contain exact duplicates and rows a rule can answer.
- **How.** Normalises text, collapses exact duplicates, applies simple rules (contains, regex, equals) and returns only the rows left for the model, plus a table of answers to copy back.
- **Risk.** A rule that is too greedy answers wrongly for free. Spot-check a sample of rule-answered rows.
- **Run.** `python tools/prefilter.py rows.jsonl --rules rules.json`

### Model cascade: `cascade.py`
- **Problem.** "Cheap first, strong if it fails" only pays when the cheap model passes often enough.
- **How.** Given the two prices, the cost of validating, and the acceptance rate, prints the break-even acceptance rate and the expected cost per task.
- **Risk.** The validator must be deterministic and real. A cascade without a check is just a cheap model.
- **Run.** `python tools/cascade.py --cheap 0.4 --strong 6 --validator 0.05 --accept 0.7`

### Lexical top-k: `topk.py`
- **Problem.** The model needs three passages, not the whole document.
- **How.** Splits the document, scores passages with BM25 against the question, and returns the best ones under a token budget, with their positions.
- **Risk.** Lexical search misses paraphrases. If the best score is low, load more or switch method (the workflow in 17.6 warns).
- **Run.** `python tools/topk.py handbook.md "how long is the refund window" --budget 1500`

### Micro-batches: `batch_pack.py`
- **Problem.** One request per tiny item repeats the instructions each time.
- **How.** Packs items into batches under an item and token limit and writes an ID-keyed batch format, so a failed item can be retried alone.
- **Risk.** Very large batches lower accuracy and a malformed response loses the batch. Keep batches small and key by ID.
- **Run.** `python tools/batch_pack.py items.jsonl --size 20 --instructions "Label each item."`

### Repair only broken fields: `repair_plan.py`
- **Problem.** A model fills 500 records, 12 fields are invalid, and the usual fix re-runs everything.
- **How.** Validates records against a small schema, builds a request containing only the invalid fields, and merges the answers back by record ID and field.
- **Risk.** A field may be wrong because of another field. Allow a bounded number of repair rounds, then send the record to a human or the strong model.
- **Run.** `python tools/repair_plan.py plan records.json schema.json`

## 16.3 Do not pay twice

### Response cache: `response_cache.py`
- **Problem.** The cheapest call is the one you do not make.
- **How.** An exact-match local cache. The key covers model, prompt, and sampling settings, entries expire (TTL), and writes are atomic so concurrent writers cannot corrupt the file.
- **Risk.** A cache freezes one sample, so use it for deterministic tasks, never for tasks where variety is the point. Never cache anything personal or secret.
- **Run.** `python tools/response_cache.py get --model m --prompt-file p.txt`

### Single flight: `singleflight.py`
- **Problem.** Ten identical requests in flight cost ten calls.
- **How.** The first caller makes the call; identical callers wait for its result. It also offers a debounce helper, so a superseded request is dropped.
- **Risk.** If the leader fails, followers must retry or fail together; the helper propagates the error rather than hiding it.
- **Run.** See the worked example at the top of `tools/singleflight.py`.

### Cache break-even and warm-up: `cache_breakeven.py`, `wave_plan.py`
- **Problem.** Cache writes may cost more than normal input, entries expire, and a prefix under the provider minimum is not cached at all. Firing 50 requests at once also means none of them reads a cache that no one has written yet.
- **How.** `cache_breakeven.py` finds the number of reuses at which caching wins. `wave_plan.py` plans one warm-up request, then waves, and checks that the gap stays inside the cache lifetime you give it.
- **Risk.** Provider rules change. Pass the numbers from your provider's current pricing page.
- **Run.** `python tools/cache_breakeven.py --prefix-tokens 8000 --write 1.25 --read 0.1 --reuses 12`

## 16.4 Find the leaks

### Output and reasoning audit: `output_audit.py`
- **Problem.** Output tokens are the dearest tokens, and hidden reasoning is billed as output.
- **How.** Reads a usage log and ranks tasks by output tokens, output-to-input ratio and reasoning share, and flags requests that hit their cap.
- **Risk.** Cutting reasoning can lower quality. Run the eval gate after any cut.
- **Run.** `python tools/output_audit.py examples/usage.sample.jsonl`

### Waste finder: `waste_finder.py`
- **Problem.** Retries, loops and repeated identical requests are tokens paid for twice.
- **How.** Finds identical requests, bursts of retries and the same error repeating, and totals the tokens involved.
- **Risk.** An intentional repeat (such as a poll) looks like waste. Read the output; do not auto-delete.
- **Run.** `python tools/waste_finder.py examples/waste.sample.jsonl`

### Preflight: `preflight.py`
- **Problem.** A request that will fail (too long, output cap above the model limit, an empty prompt) can still be billed, and its retry is billed again.
- **How.** Checks the prompt file against context and output limits you pass in, and flags common structural problems.
- **Risk.** It only knows the limits you give it.
- **Run.** `python tools/preflight.py prompt.txt --context 200000 --max-tokens 4000 --max-output-limit 8192`

### Wiki ROI: `wiki_roi.py`
- **Problem.** Earlier versions gave a fixed source-count threshold. It was not sourced.
- **How.** Compares the cost of answering from raw sources against the cost of maintaining a wiki, using your question volume, tokens per answer, changed sources and ingest cost, and prints the break-even.
- **Risk.** The inputs are estimates; try the pessimistic and the optimistic case.
- **Run.** `python tools/wiki_roi.py --questions 200 --raw-per-q 30000 --wiki-per-q 3000 --changed 20 --ingest 12000`

## 16.5 Edit safely

### Diff-only edits: `edit_guard.py`
- **Problem.** Asking for a whole rewritten file spends output tokens on every unchanged line, and risks silent changes.
- **How.** The model returns SEARCH/REPLACE blocks. The tool applies them all-or-nothing and refuses a block that matches zero or several places.
- **Risk.** A strict match fails if the model misquotes a line. That is the safe failure; the model retries with the exact text.
- **Run.** `python tools/edit_guard.py file.py patch.txt --dry-run`

## 16.6 Gate and choose

### Eval gate: `eval_gate.py`
- **Problem.** Every saving can quietly cost quality.
- **How.** Compares pass/fail results of the baseline and candidate on the same cases and reports the pass rates with Wilson confidence intervals. It says "do not ship" when the candidate's interval falls below the baseline minus your margin, and "inconclusive" when there are too few cases.
- **Risk.** A small set cannot prove equality. The honest outcome is often "inconclusive: add cases".
- **Run.** `python tools/eval_gate.py baseline.jsonl candidate.jsonl --margin 0.05`

### Lane picker: `lane_picker.py`
- **Problem.** The same model is sold in lanes: standard, batch and flex, with different price and speed.
- **How.** Given lane prices and latencies, and your deadline, picks the cheapest lane that fits.
- **Risk.** Lane terms (rate limits, completion windows) change; keep the lane file current.
- **Run.** `python tools/lane_picker.py examples/lanes.example.json --deadline-minutes 90`

## 16.7 Upgrades to older tools

| Tool | Change |
| --- | --- |
| `session_budget.py` | `--cached-share`, `--cache-price`: the saving of restarting a session is computed with caching in the model; `--restart` cost included |
| `compact.py` | Keeps error-like lines found in the cut middle |
| `budget.py` | `requests_per_session`, `tool_schema_tokens` fields |
| `ladder_log.py` | `should_probe`: occasionally tries one rung lower so the floor can fall again |
| `kb.py` | `lint --skip-stale` for the mid-ingest pass; quote matching ignores curly quotes and dash variants |
