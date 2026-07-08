"""CAMP2.O — FastAPI application entry point.

The CO-PO mapping is computed by the in-house CSAS engine (app/engine), not an LLM.
See docs/SIGNATURE_ALGORITHM.md.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .db.database import init_db
from .db.seed import seed_if_empty

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_empty()
    yield

app = FastAPI(
    title="CAMP2.O — Course Alignment & Mapping Portal",
    description="Deterministic CO→PO mapping powered by the CSAS signature algorithm.",
    version="1.0.0",
    lifespan=lifespan,
)

# Frontend is served separately (static files / dev server); allow local origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")


# Serve the static frontend at /app (mounted last so it never shadows /api).
if _FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
