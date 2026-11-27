# 7. Cheap fan-out

> Principle: parallel workers return summaries, not documents.

## 7.1 The problem with the main thread

Everything the main thread reads stays in its context and is re-sent on every following turn. Reading 40 documents there makes every later turn pay for 40 documents.

## 7.2 The pattern

```
main thread
 ├─ worker 1 reads source 1 ──► returns 3-line summary
 ├─ worker 2 reads source 2 ──► returns 3-line summary
 ├─ ...
 └─ worker 40 reads source 40 ─► returns 3-line summary
verifier (fresh context) ◄── the 40 summaries + the claims, one question
```

The main thread sees 40 short summaries instead of 40 documents. The documents live and die in the workers.

## 7.3 Rules for workers

1. **One source per worker.** Narrow tasks are cheap and parallel.
2. **Default or cheaper model.** Reading and summarising is not a premium job.
3. **Fixed return format**, for example: claim, quote, source line, confidence. Ask for it explicitly so results are comparable and short.
4. **Hard length limit** on the return, such as 80 words.
5. **No shared writes.** Workers return text; one process writes files. This avoids conflicting edits.

## 7.4 The fresh-context verifier

After the workers finish, check the result in a separate context with one question: does every statement follow from its source? A fresh context has not seen the reasoning that produced the claims, so it does not inherit the same blind spots. Pair it with the deterministic quote check from chapter 4: the script catches fabricated quotes, the verifier catches claims that misread a real quote.

## 7.4b Honest caveats

- **Summaries are lossy.** One claim per source drops most of the content, and a verifier that sees only summaries cannot recover a qualification the summary omitted. For high-stakes work let the verifier open the original passage for each claim.
- **A fresh context removes anchoring, not model bias.** If the verifier is the same model as the workers it shares its blind spots; use a different model for important checks.
- **Workers have overhead.** Each pays for the system prompt and tool schemas, and 40 simultaneous workers can all miss a cache that one warm-up would have filled (see `tools/wave_plan.py`).

## 7.5 When not to fan out

- Fewer than about five items: do it inline.
- Items depend on each other: workers cannot see one another's results.
- The task is one coherent stream (drafting a single document): use one focused agent.

Fan-out has overhead per worker. It saves money by keeping the main context small, not by being free.

## 7.6 A worker prompt template

```text
You will read ONE source: {path}.
Return exactly:
- Claim: one sentence
- Quote: the exact words that support it
- Where: file and line
- Confidence: high / medium / low
Maximum 80 words. Do not include anything else.
```

## 7.7 Prompt injection and untrusted text

A worker that reads web clippings is reading text written by strangers, and that text may contain instructions. Treat everything inside a source as data, never as a command. Give workers no tools beyond what they need (read only), so a malicious page cannot do harm, and keep write access in one place.
