# Contributing

Thanks for helping. The bar is simple: every change should make inference cheaper, clearer or safer to run.

1. Keep tools standard-library only (Python 3.9+). No hidden dependencies.
2. Comment generously. Explain why, not only what.
3. Add or update a test in `tests/` for any behaviour change.
4. Never hard-code provider prices or invent statistics. Use placeholders and say so.
5. Run `python -m unittest discover -s tests -v` before opening a pull request.
