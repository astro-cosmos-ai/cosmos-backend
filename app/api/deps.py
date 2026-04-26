"""FastAPI dependencies: auth, chart lookup."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.core.supabase import get_supabase, get_user_supabase
from app.db import queries

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    token = credentials.credentials
    try:
        user = get_supabase().auth.get_user(token)
        if user and user.user:
            return {"id": user.user.id, "email": user.user.email, "token": token}
    except Exception:
        pass
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_db(current_user: dict = Depends(get_current_user)) -> Client:
    """Returns a user-scoped Supabase client that enforces RLS."""
    return get_user_supabase(current_user["token"])


async def get_chart_or_404(
    chart_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict:
    chart = queries.get_chart_by_id(db, chart_id, current_user["id"])
    if not chart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chart {chart_id} not found")
    return chart
