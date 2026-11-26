# 10. Checklist and quick wins

Copy this into your own notes. Items are ordered from cheapest-to-do and highest-impact to more involved.

## 10.1 Ten-minute wins

- [ ] Add the "when not to read the knowledge base" line to every project guide.
- [ ] Replace eager imports of large files with "read X if needed".
- [ ] Measure always-loaded context: `python tools/tokens.py <guide> <hot cache>`.
- [ ] Shorten the guide to under about 700 tokens; move detail into on-demand pages.
- [ ] Cap the hot cache at about a dozen lines.
- [ ] Start a fresh session for unrelated work instead of continuing a long thread.
- [ ] Ask for a short, structured output instead of an essay when you will process it.

## 10.2 One-hour wins

- [ ] Write a budget file and run `tools/budget.py` in CI or a pre-commit hook.
- [ ] Add a manifest and use `kb.py status` so ingest is incremental.
- [ ] Add `kb.py lint` as a post-edit hook.
- [ ] Put stable text first in your prompts; remove timestamps from the top.
- [ ] Make the cheap-first ladder part of the guide, with "explicit instructions win".
- [ ] Deny write access to `raw/` and read access to secrets.

## 10.3 Weekly habits

- [ ] `kb.py stale --days 90` and refresh what matters.
- [ ] `tools/dedup.py wiki/` to merge near-duplicates.
- [ ] Read the diff of the week's ingests.
- [ ] Check which route you used for repeated tasks; keep the cheapest that worked.

## 10.4 Before a big batch

- [ ] Is it pure text in, text out? If yes, price it on cheaper routes with `costcalc.py`.
- [ ] Can it run as a batch (no one waiting)?
- [ ] Can workers read one source each and return three lines?
- [ ] Is there a deterministic validator for the output?
- [ ] Is there a commit before and after, so a bad run is one revert away?

## 10.5 Red flags

- A guide that grows every week.
- An agent opening the knowledge base for a generic question.
- A nightly job that costs the same on days nothing changed.
- A review step that is always "looks good".
- Timestamps or IDs at the top of a prompt.
- A single expensive model used for everything.

## 10.6 Glossary

| Term | Meaning |
| --- | --- |
| Token | The unit models read and write; roughly three quarters of an English word |
| Context window | The maximum text a model can consider at once |
| Always-loaded | Text sent in every session regardless of the task |
| Hot cache | A short file of current focus, loaded first |
| Index | A one-line-per-page map of the knowledge base |
| Manifest | A record of which sources were ingested, at which hash |
| Ingest | Turning a raw source into linked wiki pages |
| Lint | Deterministic checks over the wiki |
| Prompt caching | Provider reuse of an identical prompt prefix |
| Fan-out | Splitting work across parallel workers |
| Rung | A step on the cheap-first ladder |
| Dead zone | The corpus size at which a wiki is not yet worth building |
