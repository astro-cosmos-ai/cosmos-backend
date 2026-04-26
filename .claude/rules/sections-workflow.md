# Rule: Adding a New Analysis Section

Four edits. No new route. The generic `POST /api/charts/{id}/analyze/{section}` dispatches via the registry.

1. **System prompt** → `app/agents/prompts/<section>.py` — exports `SYSTEM_PROMPT: str`. Use the `prompt-engineer` subagent.
2. **Context builder** → `app/services/harness/context_builder.py` — add `build_<section>_context(chart_json) -> str`. Use the `harness-builder` subagent.
3. **Registry** → `app/agents/registry.py` — update both import blocks and the `AGENT_REGISTRY` dict.
4. **Whitelist** → `app/models/analysis.py` — append to `VALID_SECTIONS`.

Preferred: invoke `/add-section <name> "<description>"` which does all four with the right subagents.

## Verify

```
uv run python -c "from app.agents.registry import AGENT_REGISTRY; print(list(AGENT_REGISTRY.keys()))"
uv run python -c "from app.models.analysis import VALID_SECTIONS; print(VALID_SECTIONS)"
```

Both should contain the new name.
