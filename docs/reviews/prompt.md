# The review prompt (verbatim)

Sent to every model with the repository content (README, chapters 1-10 and 14, and the tool list) appended after the last line. Version 2.0.0 content. Answers were requested as JSON only.

## System message

You are a rigorous, sceptical reviewer of LLM cost-optimisation practice. Be concrete and concise. Output valid JSON only, no markdown fences.

## User message

```text
Below is the full content of an open-source repository ('cheap-inference') about lowering LLM inference costs: its README, chapters and tool list.

Do two things.

TASK A - AUDIT. List every claim, number or recommendation you believe is wrong, outdated, overstated, missing a caveat, or risky. Be specific (quote the phrase). Also list the 5 strongest ideas you would keep unchanged.

TASK B - EXTEND. Propose NEW ways to lower inference cost that the repository does NOT already cover (check the README and chapters first). For each: name, why it saves money, when it hurts quality, and a concrete implementation as a small standard-library Python tool (describe inputs/outputs and the core algorithm in 3-6 lines). Also propose NEW end-to-end workflows (step lists). Prioritise techniques with the best savings-to-risk ratio. At most 14 techniques and 8 workflows.

Return JSON with this exact shape:
{"audit":{"problems":[{"quote":str,"issue":str,"fix":str}],"keep":[str]},
 "techniques":[{"name":str,"saves":str,"risk":str,"tool":{"filename":str,"algorithm":str}}],
 "workflows":[{"name":str,"steps":[str],"tools":[str]}]}

REPOSITORY CONTENT:
[repository content appended here]
```

For GPT-6.2 astra and Grok 4.7 the limits were tightened to: at most 8 techniques, 4 workflows and 10 problems, with terse 3-line algorithms (their first attempts, at the larger size, were dropped by the connection before finishing).
