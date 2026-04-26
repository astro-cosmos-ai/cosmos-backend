---
description: Scaffold a new analysis section — system prompt, context builder, registry entry, VALID_SECTIONS update. Delegates to prompt-engineer + harness-builder + agent-author subagents.
argument-hint: <section_name> "<one-line description>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
model: inherit
---

Add a new analysis section named **$1** covering: $2.

Before writing anything, verify:
1. Run `!grep -n "VALID_SECTIONS" app/models/analysis.py` to confirm the section doesn't already exist.
2. Run `!ls app/agents/prompts/` to confirm no existing prompt file collides.

Then perform the four edits that make `POST /api/charts/{id}/analyze/$1` work end-to-end — do **not** add a new route, the generic dispatcher handles it.

### 1. System prompt → `app/agents/prompts/$1.py`

Delegate to the `prompt-engineer` subagent via the Agent tool. Brief it with:
- Section name: $1
- Scope: $2
- Pair this prompt with the context builder being added in step 2
- Follow the standard skeleton and the sub-topic grid in its instructions

### 2. Context builder → append to `app/services/harness/context_builder.py`

Delegate to the `harness-builder` subagent. Brief it with:
- Add `build_$1_context(chart_json: dict) -> str`
- Decide which houses, planets, and significators are relevant to "$2"
- Reuse the existing `_planet_line`, `_significators_for_houses`, `_current_dasha`, `_kp_cusp_info` helpers
- Keep total output under ~800 tokens

### 3. Registry entry → `app/agents/registry.py`

Edit both the `from app.agents.prompts import (...)` block and `from app.services.harness.context_builder import (...)` to include the new names, then add the dict entry:

```python
"$1": {
    "context_builder": build_$1_context,
    "system_prompt": $1.SYSTEM_PROMPT,
},
```

### 4. VALID_SECTIONS → `app/models/analysis.py`

Append `"$1"` to the `VALID_SECTIONS` list.

### Verify

After all four edits:
- `!uv run python -c "from app.agents.registry import AGENT_REGISTRY; assert '$1' in AGENT_REGISTRY; print('registered OK')"`
- `!uv run python -c "from app.models.analysis import VALID_SECTIONS; assert '$1' in VALID_SECTIONS; print('whitelist OK')"`

If both pass, report the four changed files and recommend the user hit `POST /api/charts/<id>/analyze/$1` on a live chart to smoke-test.
