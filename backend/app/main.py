"""
GoldParity API — Phase 6.

Run with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import init_db

app = FastAPI(
    title="GoldParity API",
    description="Cross-contract mispricing intelligence for MCX gold futures.",
    version="0.1.0",
)

# Vite's default dev server ports. The frontend also proxies /api through
# its own dev server (see frontend/vite.config.js), so CORS is a fallback
# safety net rather than the primary mechanism.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
