---
description: Start the FastAPI dev server with uv + uvicorn, reload on change. Verifies env first.
allowed-tools: Bash, Read
model: inherit
---

Before starting, confirm the env is complete.

```
!test -f .env && echo "env present" || echo "MISSING .env — copy .env.example and fill in keys"
!grep -E "^(SUPABASE_URL|SUPABASE_SERVICE_KEY|ASTROLOGY_API_KEY|ANTHROPIC_API_KEY)=" .env | awk -F= '{print $1, ($2 ? "set" : "EMPTY")}'
```

If any key is empty or missing, stop and ask the user to fill them before proceeding.

Then start the server:

```
!uv run uvicorn app.main:app --reload --port 8000
```

Remind the user:
- Swagger UI at `http://localhost:8000/docs`
- Auth requires a Supabase JWT — use the frontend or `supabase auth sign-in` to get one
- Stop with Ctrl+C
