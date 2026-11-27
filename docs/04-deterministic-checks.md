# 4. Deterministic checks

> Principle: if a rule can be written as code, never pay a model to enforce it.

## 4.1 Why a model should not check its own work

A model asked to "check the wiki for errors" will often pass a false statement that sounds plausible, because the same biases that produced it also judge it. A script has no such bias. It is also cheaper by orders of magnitude: a lint over a small vault finishes well under a second and uses no tokens (larger vaults take longer; this has not been benchmarked).

The demonstration is in this repository. `examples/broken-kb` contains a planted false sentence. Run:

```bash
python tools/kb.py --root examples/broken-kb lint
```

and the output includes:

```
wiki/memex.md: QUOTE NOT IN SOURCE -> "The memex was first built in 1975" (raw/memex.md)
```

A model reviewer might have let it through. The script cannot.

## 4.2 The rules and what each protects

| Rule | Checks | Catches |
| --- | --- | --- |
| R1 | Frontmatter has `title`, `sources`, `updated` | Pages with no provenance |
| R2 | Every listed source exists | Dangling references |
| R3 | Every `[[link]]` resolves | Broken navigation |
| R4 | No orphans | Pages nobody can reach |
| R5 | No `TODO` / `FIXME` | Half-finished pages |
| R6 | Quoted claims appear verbatim in the cited source | Invented or distorted facts |
| R7 | Raw files unchanged since ingest | Pages built on outdated sources |
| R8 | `hot.md` stays small | Cache turning into an archive |
| R9 | Page under the token limit | Pages too big to read cheaply |
| R10 | Valid, non-future `updated` date | Typos and impossible dates |

## 4.3 What the linter cannot do

It checks structure and quotes, not truth. Be precise about what the quote rule (R6) proves: that a string exists in a source file. It does not prove the claim is entailed by that string, that the quote is in context, that a real quote is not attached to an unrelated claim, or that unquoted claims are supported. It narrows the space for fabrication; a semantic reviewer (or a person) still covers the rest. Quotes are compared after normalising whitespace, curly quotes and dashes, so typography never causes a false alarm.

Also note the honest cost of the hook loop: the linter itself is free, but when its error text is fed back to the model, the model spends tokens fixing it. "Zero tokens" describes the check, not the repair. If a raw source is wrong, the wiki will faithfully repeat it, and every quote will pass. Controls that remain human:

- Decide what enters `raw/`. Treat web clippings as untrusted text from strangers.
- Keep `raw/` read-only to the model (see 4.5).
- Review the git diff of each ingest.

## 4.4 Wiring the check into the loop

Hooks let a script run after the model edits a file and send its complaints back so it can fix them in the same turn:

```bash
# templates/post-edit-hook.sh
f=$(jq -r '.tool_input.file_path // empty')
case "$f" in
  */wiki/*) python3 tools/kb.py lint >&2 || exit 2 ;;
esac
exit 0
```

Exit code 2 does not undo the edit (the tool already ran); it routes the text on stderr back to the model. Exact hook configuration differs between agent tools, so check your tool's documentation, and treat the template as a pattern.

A second hook prints a short briefing at session start (`templates/session-start-hook.sh`): the hot cache and the pending-ingest list. Keep that output brief; it is paid for in tokens.

## 4.5 Keys, not prompts

"Please do not edit raw files" is a suggestion. A guide file is context, not enforcement. If something must never happen, enforce it with configuration:

- Deny write access to `raw/` in your agent's permission settings.
- Deny reading secrets files such as `.env`.
- Know the limit: permission rules usually cover the agent's own file tools and some recognised commands, not an arbitrary script that opens files itself. For a hard wall, use a sandbox.

## 4.6 More zero-token checks worth adding

These follow the same pattern and are easy extensions of `tools/kb.py`:

1. **Duplicate detection** with `tools/dedup.py` (shingles and Jaccard similarity).
2. **Staleness** with `kb.py stale --days 90`: pages whose `updated` date is old.
3. **Size budgets** with `tools/budget.py` for always-loaded files.
4. **Link rot** for external URLs: a script that issues HEAD requests on a schedule. (That one needs the network, so it is deliberately NOT in `tools/`; the tools stay offline and a test enforces it.)
5. **Glossary consistency**: a list of preferred terms, flagging banned variants.
6. **Date and number drift**: regular expressions for figures that must match a single source of truth.

## 4.7 Writing your own rule

Every rule in `kb.py` follows the same shape, so adding one takes minutes:

```python
# 1. Look at the text of a page.
# 2. If it violates the rule, append a readable message to `errs`.
if re.search(r"\bas an ai language model\b", t, re.I):
    errs.append(f"{r}: boilerplate phrase")
```

Keep messages specific: file, rule, and the offending text. The model will read them and act on them.

## 4.8 Exit codes are an interface

`lint` returns 0 when clean and 2 when not. Those numbers are what hooks, CI and schedulers key off. Do not change them casually.
