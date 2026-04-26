# Rule: FastAPI Route Conventions

All routes live in `app/api/`. They are thin — they do not compute, call AIs, or hit Supabase directly.

## Every route:

- `async def` handler.
- `Depends(get_current_user)` or `Depends(get_chart_or_404)` for auth. No inline JWT parsing.
- Pydantic request body + `response_model=` on the decorator. No raw `dict`.
- Delegates to `app/services/<x>.py` or `app/agents/<x>.py` for work.
- Database access goes through `app/db/queries.py` — never `supabase.table(...)` inline.
- Errors via `HTTPException(status_code=status.HTTP_4XX_*, detail=...)`.
- Config via `app.core.config.settings`, never `os.environ`.

## Router mounting

Routers are declared with a `prefix` and `tags`, then included in `app/main.py` under the `/api` root prefix. Follow the existing pattern; do not invent new mounting.

## Caching pattern (analyses, varshaphal, compatibility)

```
key = hash(chart_subset + params)
cached = queries.get_cached_<thing>(...)
if cached: return cached (cached=True)
result = await <agent_or_service>(...)
queries.save_<thing>(..., result)
return result (cached=False)
```

## Streaming (chat)

`StreamingResponse` + `media_type="text/event-stream"`. Each chunk `f"data: {json.dumps(payload)}\n\n"`. Terminate with `data: [DONE]\n\n`. Wrap `yield` in try/except to handle client disconnects gracefully.
