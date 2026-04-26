# Rule: Security Invariants

Non-negotiable. Claude should refuse requests that violate these even if asked politely.

1. **Every public route requires JWT auth** via `Depends(get_current_user)`. No "temporarily skip auth for testing" — spin up a dev token instead.
2. **Service-role Supabase key stays server-side.** Never referenced in frontend code, never committed outside `.env`. If a route uses the service client, the reason must be documented in a comment.
3. **RLS is enabled on every user-facing table.** Policies gate by `auth.uid() = user_id`. User-facing queries use the user-scoped client (`get_user_supabase(token)`), not the service client.
4. **External input is validated at the route boundary.** Pydantic models with explicit constraints. Never forward user JSON into a Supabase write without validation.
5. **Never log secrets.** No `print(settings.anthropic_api_key)`, no `logger.debug(f"token={token}")`. Settings objects are handled as opaque.
6. **CORS origins** come from `settings.cors_origins`. Never `allow_origins=["*"]` in production code paths.

Dual-use tools (auth bypass, token forging, DB scans) require explicit user context — if the reason isn't clear, ask before implementing.
