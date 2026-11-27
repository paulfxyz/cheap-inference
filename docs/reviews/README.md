# Review artefacts

The raw (parsed) answers of the four models that audited cheap-inference 2.0.0, so every finding in [chapter 15](../15-multi-model-review.md) can be checked.

| File | Model (via OpenRouter) |
| --- | --- |
| [`claude-fable-5.2.json`](claude-fable-5.2.json) | anthropic/claude-fable-5.2 |
| [`gemini-4-neon.json`](gemini-4-neon.json) | google/gemini-4-neon |
| [`gpt-6.2-astra.json`](gpt-6.2-astra.json) | openai/gpt-6.2-astra |
| [`grok-4.7.json`](grok-4.7.json) | x-ai/grok-4.7 |
| [`prompt.md`](prompt.md) | the prompt every model received |

Each file has the shape `{audit: {problems, keep}, techniques, workflows}`. Model output is evidence to weigh, not authority: several findings are summarised as accepted, partly accepted or declined in chapter 15.
