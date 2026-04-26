# Rule: Testing Conventions

Tests live in `cosmos-backend/tests/`. Runner: `uv run pytest`. Async tests use `pytest-asyncio` (mark with `@pytest.mark.asyncio`).

## What to test, by layer

| Layer | Target |
|-------|--------|
| Harness (`app/services/harness/`) | Unit tests with a fixture `chart_json`. Assert exact strings / lists / dicts. No mocks — feed real data shapes. |
| Services (`app/services/`) | Integration-ish. Mock the AstrologyAPI HTTP client at the `httpx.AsyncClient` boundary, nothing inside that. Never mock Supabase — use a test schema or RLS-safe execute_sql. |
| Agents (`app/agents/`) | Mock **only** the Anthropic client response. The LangGraph wiring and validator must be real. |
| Routes (`app/api/`) | Use FastAPI's `TestClient` with a stubbed `get_current_user` dep override. |

## Do not

- Mock the harness. Its correctness is the whole value prop — run it for real.
- Mock Supabase with a dict. Use a fresh test chart row or a scoped schema.
- Write tests against live AstrologyAPI. Record a fixture once, feed it repeatedly.
- Skip validator assertions in agent tests — the retry loop is part of the contract.

## Fixtures

Keep a canonical `chart_json` fixture (known birth data) in `tests/fixtures/`. New fixtures only when a test needs a specific edge case (e.g., Kemadruma Yoga, debilitated Sun). Reuse aggressively.
