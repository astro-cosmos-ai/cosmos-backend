from functools import lru_cache
from supabase import create_client, Client
from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Service-role client — for auth validation and admin ops only. Never use for user data queries."""
    return create_client(settings.supabase_url, settings.supabase_service_key)


def get_user_supabase(token: str) -> Client:
    """Per-request user-scoped client — respects RLS. Use for all user data queries."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(token)
    return client
