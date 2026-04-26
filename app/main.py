from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import charts, significators, analyses, timeline, chat, compatibility, predict, varshaphal, report


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the Supabase client singleton on startup
    from app.core.supabase import get_supabase
    get_supabase()
    yield


app = FastAPI(
    title="Cosmos — Vedic Astrology Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(charts.router)
app.include_router(significators.router)
app.include_router(analyses.router)
app.include_router(timeline.router)
app.include_router(chat.router)
app.include_router(compatibility.router)
app.include_router(predict.router)
app.include_router(varshaphal.router)
app.include_router(report.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
