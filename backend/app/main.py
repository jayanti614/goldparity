"""
GoldParity API — Phase 6.

Run locally with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs.

For deployment (Phase 9), set the ALLOWED_ORIGINS environment variable to
a comma-separated list of the frontend's real domain(s), e.g.:
    ALLOWED_ORIGINS=https://goldparity.vercel.app
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import init_db

app = FastAPI(
    title="GoldParity API",
    description="Cross-contract mispricing intelligence for MCX gold futures.",
    version="0.1.0",
)

# Local dev origins (Vite's default ports) are always allowed. Anything in
# the ALLOWED_ORIGINS env var (comma-separated) is added on top of that --
# this is how the deployed frontend's real domain gets permission to call
# this API without needing a code change per deployment.
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"name": "GoldParity API", "docs": "/docs"}


app.include_router(router)
