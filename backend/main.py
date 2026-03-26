"""
main.py
FastAPI application entry point for CallIQ Analytics API.

Run:
  uvicorn main:app --reload --port 8000

Environment variables (.env):
  sarvam_api_key=your_key_here
  USE_MOCK=true          # set false when using real Sarvam AI
"""
"""
main.py — CallIQ Analytics API

HOW TO RUN (IMPORTANT — read this):
=====================================

✅ CORRECT way (no auto-restart killing background tasks):
   uvicorn main:app --reload --reload-dir . --port 8000

   The --reload-dir . tells uvicorn to only watch Python source files,
   NOT the uploads/ folder. Without this, uploading a WAV file triggers
   a server restart which kills the background transcription task.

❌ WRONG way (causes "processing forever" bug):
   uvicorn main:app --reload --port 8000
   (watches ALL directories including uploads/ — restarts on every upload)

OR run without reload (best for stable usage):
   uvicorn main:app --port 8000

Environment (.env):
   USE_MOCK=true            → fake transcripts (for testing UI)
   USE_MOCK=false           → real Sarvam AI transcription
   sarvam_api_key=YOUR_KEY  → required when USE_MOCK=false
"""

import os
import json
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""

    use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
    has_key  = bool(os.getenv("sarvam_api_key"))

    print("\n" + "="*60)
    print("[CallIQ] Server started")
    print(f"[CallIQ] USE_MOCK    = {os.getenv('USE_MOCK', 'not set (defaulting to true)')}")
    print(f"[CallIQ] Mode        = {'⚠️  MOCK — real audio NOT transcribed' if use_mock else '✅ LIVE — Sarvam AI active'}")
    print(f"[CallIQ] Sarvam key  = {'✓ SET' if has_key else '✗ NOT SET (required for LIVE mode)'}")
    print(f"[CallIQ] Docs        = http://localhost:8000/docs")
    print(f"[CallIQ] Env check   = http://localhost:8000/api/debug/env")
    print()
    print("[CallIQ] ⚠️  IMPORTANT: Run with --reload-dir to prevent upload restarts:")
    print("[CallIQ]    uvicorn main:app --reload --reload-dir . --port 8000")
    print("="*60 + "\n")

    # ── On startup: reset any orphaned 'processing' records ──────────────────
    # If the server was killed/restarted mid-processing, records stay 'processing'
    # forever. Reset them to 'failed' so user knows to re-upload.
    from services.call_store import get_store
    from models.schemas import JobStatus

    store = get_store()
    orphaned = 0
    for call_id, record in list(store._records.items()):
        if record.get("status") in ("processing", "pending"):
            store._records[call_id]["status"] = JobStatus.FAILED.value
            store._records[call_id]["_failure_reason"] = "Server restarted during processing — please re-upload"
            orphaned += 1

    if orphaned:
        store._save_to_disk()
        print(f"[CallIQ] ⚠️  Reset {orphaned} orphaned 'processing' record(s) to 'failed'")
        print(f"[CallIQ]    These were stuck because the server restarted during processing.")
        print(f"[CallIQ]    Re-upload those files to process them.\n")

    yield

    print("[CallIQ] Server shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CallIQ Analytics API",
    description="AI-powered call quality analytics. Set USE_MOCK=false for real transcription.",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

from routes.api import router
app.include_router(router, prefix="/api")

# ─── Ensure dirs exist ────────────────────────────────────────────────────────

Path("uploads").mkdir(exist_ok=True)
Path("outputs").mkdir(exist_ok=True)

# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
    return {
        "status": "ok",
        "version": "2.1.0",
        "mode": "mock" if use_mock else "live",
        "run_command": "uvicorn main:app --reload --reload-dir . --port 8000",
    }

# *******************************************************************************************
# """
# main.py
# FastAPI application entry point for CallIQ Analytics API.

# Run:
#   uvicorn main:app --reload --port 8000

# Environment variables (.env):
#   sarvam_api_key=your_key_here
#   USE_MOCK=true          # set false when using real Sarvam AI
# """

# import os
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from pathlib import Path
# from dotenv import load_dotenv

# load_dotenv()

# # ── App ───────────────────────────────────────────────────────────────────────

# app = FastAPI(
#     title="CallIQ Analytics API",
#     description="AI-powered call quality analytics backend for tele-sales QA.",
#     version="2.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# # ── CORS (allow React dev server) ─────────────────────────────────────────────

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",   # React dev server (Vite)
#         "http://localhost:5173",   # Vite default port
#         "http://127.0.0.1:3000",
#         "http://127.0.0.1:5173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ── Routes ────────────────────────────────────────────────────────────────────

# from routes.api import router
# app.include_router(router, prefix="/api")

# # ── Static file serving for uploads ───────────────────────────────────────────

# Path("uploads").mkdir(exist_ok=True)
# Path("outputs").mkdir(exist_ok=True)

# # ── Health check ──────────────────────────────────────────────────────────────

# @app.get("/health")
# async def health():
#     return {
#         "status": "ok",
#         "mode": "mock" if os.getenv("USE_MOCK", "true").lower() == "true" else "live",
#         "version": "2.0.0",
#     }


# # ── Startup ───────────────────────────────────────────────────────────────────

# @app.on_event("startup")
# async def startup():
#     mode = os.getenv("USE_MOCK", "true")
#     print(f"[Athena] Server started. USE_MOCK={mode}")
#     print(f"[Athena] API docs: http://localhost:8000/docs")
#     print(f"[Athena] POST /api/seed to load demo data")