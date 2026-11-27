# 9. Failure modes and honest limits

> Cost control that hurts quality is not a saving. This chapter lists where the ideas break.

## 9.1 The dead zone

Where a compiled wiki does not pay off is a function of source size, query volume and churn, not of source count. Use `tools/wiki_roi.py` to compute the break-even for your numbers instead of trusting a rule of thumb. The pattern most people quit at is the early stretch where setup cost is paid and the wiki is still small.

## 9.2 Scale

A wiki works well while its index fits comfortably in one context window. Past that, you need sub-indexes (chapter 2) or real retrieval. Some critics point out the approach does not scale indefinitely; they are right, and some of them sell a competing product, so weigh both facts. Reports of small month-long trials are mixed (helpful for narrow cases, with maintenance time and time saved roughly a wash in the first month). This repository does not cite a specific study and has not benchmarked the pattern, so treat that as anecdote. Measure your own break-even and plan for a payoff over months, not days.

## 9.3 Bad sources spread

One wrong source compiled into a wiki has touched many pages. The quote check proves a claim matches its source, not that the source is true. Keep humans in charge of what enters `raw/`.

## 9.4 No lifecycle

A plain wiki has no signal that a page from month one is still current. Run `kb.py stale` on a schedule, and re-ingest sources that matter.

## 9.5 Over-pruning

Aggressive context trimming can drop something the model needed, producing a confident wrong answer that costs more to detect than the tokens saved. Guard rails:

1. Trim the always-loaded layer first; leave on-demand pages intact.
2. Keep the escalation path: if an answer looks shallow, climb a rung.
3. Never trim safety or compliance instructions to save tokens.

## 9.6 Cheap models fail in particular ways

Small models are weaker at long multi-step reasoning, subtle instructions, and rare formats. Symptoms: ignored constraints, plausible but wrong details, drift in long outputs. Mitigations: shorter tasks, explicit output formats, a deterministic validator, and a fallback to a stronger model when validation fails.

## 9.7 Hidden costs of the savings themselves

- **Setup time.** The linter, hooks and manifest cost hours to set up.
- **Maintenance.** Rules need updating when conventions change.
- **Complexity.** More moving parts means more ways to fail quietly. Add them one at a time, with the measurement from chapter 1 telling you it was worth it.

## 9.8 Security notes

- Treat text in sources, web pages, emails and tool results as data, never as instructions.
- Keep secrets out of the knowledge base and deny reading of `.env`-style files.
- Do not paste API keys into prompts or guides.
- Give automated runs the narrowest permissions that work.

## 9.9 Verify claims before you rely on them

Statistics quoted in popular posts about tools (star counts, view counts, install commands) go stale quickly and are sometimes copied wrongly between guides. Check a source's current state before you cite or depend on it.
