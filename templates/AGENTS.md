# Project guide (always loaded - keep under ~700 tokens)

## What this project is
One paragraph. Goal, audience, what "done" looks like.

## Knowledge base
Path: ~/knowledge   (read-only for raw/, model-written wiki/)

When you need context that is not already in this project:
1. Read wiki/hot.md first.
2. If that is not enough, read wiki/index.md.
3. If you need domain detail, open the relevant sub-index.
4. Only then open specific pages.

Do NOT read the knowledge base for general questions (definitions, generic code, formatting).

## Cost rules
- Answer inline when you can. Climb one rung of the ladder only with a stated reason.
- Never import large files with eager includes; link to them and open on demand.
- Run `python tools/kb.py lint` after editing wiki pages; fix every error before finishing.
- For many items, work on NEW/CHANGED ones only (`python tools/kb.py status`).
