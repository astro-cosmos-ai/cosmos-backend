---
description: Print the end-to-end chart creation + analysis pipeline so you know which layer owns what before touching code.
allowed-tools: Read, Grep
model: inherit
---

Explain, with live file:line references, the full pipeline:

```
Birth input
  → POST /api/charts                    (app/api/charts.py)
  → AstrologyAPI client                 (app/services/astrology_api/client.py — Semaphore(5))
  → Assembler                           (app/services/astrology_api/assembler.py — normalizes + computes whole-sign)
  → Parashari harness                   (app/services/harness/parashari.py — significators)
  → Yoga detection                      (app/services/harness/yogas.py)
  → Persist to charts table             (app/db/queries.py → save_chart)
  → Return chart row

Analysis request
  → POST /api/charts/{id}/analyze/{section}   (app/api/analyses.py)
  → Cache lookup by (chart_id, section, hash) (app/db/queries.py → get_cached_analysis)
  → Cache miss → dispatch via registry         (app/agents/registry.py)
  → LangGraph 5-node graph                     (app/agents/base_agent.py)
     LOAD → EXTRACT (context_builder)
          → COMPUTE (no-op, harness pre-computed)
          → SYNTHESIZE (Anthropic claude-sonnet-4-6, cached system prompt)
          → VALIDATE (position_validator, max 2 retries)
  → Persist cached result
  → Return analysis text
```

For each arrow, open the referenced file and quote the 3–5 key lines. The user should come away knowing exactly where to edit for a given change.
