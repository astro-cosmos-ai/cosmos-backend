# Rule: LangGraph 5-Node Agent Pattern

Every analysis agent in `app/agents/` uses the same graph. Do not invent new shapes.

```
LOAD → EXTRACT → COMPUTE → SYNTHESIZE → VALIDATE
                               ↑              |
                               └──── retry ───┘  (max 2)
```

## Node contracts

| Node | Owns | Must NOT |
|------|------|----------|
| LOAD | `db_fn(chart_id)` → `chart_json` | Make HTTP calls |
| EXTRACT | `context_builder_fn(chart_json)` → string | Call the LLM |
| COMPUTE | Passthrough (harness pre-computed) | Add astrological computation here — put it in the harness |
| SYNTHESIZE | Single Anthropic call, system prompt cached ephemerally | Stream to client (use chat route for that) |
| VALIDATE | `validate_output(text, chart_json)` + retry decision | Ever be removed or bypassed |

## Configuration, not forking

New sections go through `build_analysis_graph(context_builder_fn, system_prompt, db_fn)`. Do not copy `base_agent.py` and tweak it.

## Model choice

- `claude-sonnet-4-6` → analyses, event predictor narrative.
- `claude-haiku-4-5` → chat / streaming / short-form.

## Retry

Max 2 retries. On final failure the response is prefixed with `[UNVERIFIED — ...]` and returned. Never increase the cap — fix the prompt instead.
