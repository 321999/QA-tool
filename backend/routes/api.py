"""
routes/api.py — PRODUCTION VERSION with full console logging
Every step prints to console so you can see EXACTLY what is happening.
"""

import os
import shutil
import traceback
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

from services.call_store import get_store
from models.schemas import (
    UploadResponse, JobStatusResponse, JobStatus, CallRecord,
)

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

_analytics = None

def get_analytics():
    global _analytics
    if _analytics is None:
        use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
        print("\n" + "="*60)
        print(f"[ANALYTICS INIT] USE_MOCK env = {os.getenv('USE_MOCK', 'not set (defaulting true)')}")
        print(f"[ANALYTICS INIT] Mode: {'MOCK' if use_mock else 'LIVE'}")
        if use_mock:
            from services.analytics import CallAnalytics
            _analytics = CallAnalytics(use_mock=True)
            print("[ANALYTICS INIT] ⚠️  MOCK MODE — uploaded audio will NOT be transcribed")
            print("[ANALYTICS INIT]    Fix: set USE_MOCK=false and sarvam_api_key in .env")
        else:
            from sarvamai import SarvamAI
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("sarvam_api_key")
            if not api_key:
                raise RuntimeError("sarvam_api_key not found in .env — add it or set USE_MOCK=true")
            print(f"[ANALYTICS INIT] ✓ Sarvam key loaded (...{api_key[-4:]})")
            client = SarvamAI(api_subscription_key=api_key)
            from services.analytics import CallAnalytics
            _analytics = CallAnalytics(client=client, use_mock=False)
            print("[ANALYTICS INIT] ✓ LIVE — Sarvam AI will transcribe your audio")
        print("="*60 + "\n")
    return _analytics


def _process_sync(audio_paths: List[str], call_ids: List[str], job_id: str):
    store    = get_store()
    use_mock = os.getenv("USE_MOCK", "true").lower() == "true"

    print("\n" + "█"*60)
    print(f"[BG] Job {job_id} started")
    print(f"[BG] Mode: {'MOCK (fake transcript)' if use_mock else 'LIVE (Sarvam AI)'}")
    for p in audio_paths:
        path = Path(p)
        size = path.stat().st_size if path.exists() else -1
        print(f"[BG] File: {path.name}  size={size} bytes  exists={path.exists()}")

    for cid in call_ids:
        store.update_status(cid, JobStatus.PROCESSING)
    print(f"[BG] All {len(call_ids)} call(s) marked PROCESSING")

    try:
        analytics = get_analytics()
        print(f"[BG] Calling analytics.process_audio_files({audio_paths})")
        records = analytics.process_audio_files(audio_paths)
        print(f"[BG] ✓ Done — {len(records)} record(s):")
        for r in records:
            print(f"  call_id={r.call_id}  score={r.total_score}  grade={r.grade}  transcript={len(r.transcript)} lines")
    except Exception as e:
        print(f"[BG] ✗ FAILED: {e}")
        traceback.print_exc()
        for cid in call_ids:
            store.update_status(cid, JobStatus.FAILED)
    print("█"*60 + "\n")


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    import uuid
    from services.transcription import _extract_call_id_from_filename, _extract_phone_from_filename

    job_id     = f"job-{uuid.uuid4().hex[:8]}"
    saved_paths = []
    call_ids   = []
    store      = get_store()
    use_mock   = os.getenv("USE_MOCK", "true").lower() == "true"

    print("\n" + "="*60)
    print(f"[UPLOAD] {len(files)} file(s) received  mode={'MOCK' if use_mock else 'LIVE'}")

    for file in files:
        dest = UPLOAD_DIR / file.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        size    = dest.stat().st_size
        call_id = _extract_call_id_from_filename(file.filename)
        phone   = _extract_phone_from_filename(file.filename)

        print(f"[UPLOAD] Saved {file.filename}  size={size} bytes  call_id={call_id}  phone={phone}")
        if size < 1000:
            print(f"[UPLOAD] ⚠️  File looks too small ({size} bytes) — may be corrupt")

        saved_paths.append(str(dest))
        call_ids.append(call_id)

        pending = CallRecord(
            call_id=call_id, file_name=file.filename,
            audio_url=f"/api/audio/{call_id}", job_id=job_id,
            status=JobStatus.PENDING, created_at=datetime.now().isoformat(),
            duration_seconds=0.0, duration_formatted="—",
            agent_id="UNKNOWN", phone_number=phone,
            transcript=[], speaker_stats=[],
        )
        store.upsert(pending)

    if use_mock:
        print(f"[UPLOAD] ⚠️  MOCK MODE: Your audio will NOT be transcribed. Fake transcript will be used.")
        print(f"[UPLOAD]    To use real Sarvam AI: set USE_MOCK=false + sarvam_api_key in backend/.env")

    background_tasks.add_task(_process_sync, saved_paths, call_ids, job_id)
    print(f"[UPLOAD] Job {job_id} queued")
    print("="*60 + "\n")

    return UploadResponse(
        job_id=job_id, files_queued=len(files), status=JobStatus.PENDING,
        message=f"{len(files)} file(s) queued ({'MOCK mode — fake transcript' if use_mock else 'LIVE mode — Sarvam AI'}).",
    )


@router.get("/dashboard")
async def get_dashboard(grade: Optional[str] = Query(default=None)):
    store  = get_store()
    result = store.build_dashboard(grade_filter=grade).model_dump()
    print(f"[DASHBOARD] {len(result['calls'])} calls  grade={grade}  metrics={result['metrics']}")
    return result


@router.get("/call/{call_id}")
async def get_call(call_id: str):
    store  = get_store()
    record = store.get_by_id(call_id)
    if not record:
        print(f"[CALL] 404: {call_id}")
        raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")
    print(f"[CALL] {call_id}  status={record.get('status')}  score={record.get('total_score')}  transcript={len(record.get('transcript',[]))} lines")
    return record


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    store  = get_store()
    record = store.get_by_job_id(job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    status = record.get("status", "pending")
    msgs   = {"pending":"Queued...","processing":"Transcribing...","completed":"Done.","failed":"Failed — check logs."}
    return JobStatusResponse(job_id=job_id, status=status, progress_message=msgs.get(status,"?"), call_id=record.get("call_id"))


@router.get("/jobs")
async def list_jobs():
    store = get_store()
    return {"jobs": store.all_records()}


@router.get("/leaderboard")
async def get_leaderboard():
    return {"leaderboard": get_analytics().get_leaderboard()}


@router.get("/audio/{call_id}")
async def serve_audio(call_id: str):
    print(f"[AUDIO DEBUG] call_id={call_id}")
    print(f"[AUDIO DEBUG] file_name={record.get('file_name')}") 
    print(f"[AUDIO DEBUG] path={audio_path}")
    print(f"[AUDIO DEBUG] exists={audio_path.exists()}")
    store  = get_store()
    record = store.get_by_id(call_id)
    if not record:
        raise HTTPException(status_code=404, detail="Call not found.")

    file_name  = record.get("file_name", "")
    audio_path = UPLOAD_DIR / file_name

    print(f"[AUDIO] {call_id} → {audio_path}  exists={audio_path.exists()}", end="")
    if audio_path.exists():
        sz = audio_path.stat().st_size
        print(f"  size={sz} bytes")
    else:
        print()

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio not on disk: {audio_path.absolute()}")

    sz = audio_path.stat().st_size
    if sz < 100:
        raise HTTPException(
            status_code=422,
            detail="Demo/seed call — no real audio. Upload your own WAV file to hear playback."
        )

    ext  = audio_path.suffix.lower()
    mime = {".wav":"audio/wav",".mp3":"audio/mpeg",".m4a":"audio/mp4",".ogg":"audio/ogg",".webm":"audio/webm"}.get(ext,"audio/wav")
    return FileResponse(path=str(audio_path), media_type=mime, filename=file_name,
                        headers={"Accept-Ranges":"bytes","Cache-Control":"no-cache"})


@router.post("/seed")
async def seed_mock_data():
    if os.getenv("USE_MOCK", "true").lower() != "true":
        raise HTTPException(status_code=403, detail="Seed only available when USE_MOCK=true")
    print("\n[SEED] Creating 3 demo records with fake transcripts...")
    fake_paths = [
        "uploads/4174_09890382855_07-Mar-26-14-28-19.WAV",
        "uploads/4175_09123456789_07-Mar-26-15-10-44.WAV",
        "uploads/4176_09765432100_07-Mar-26-15-45-30.WAV",
    ]
    for p in fake_paths:
        Path(p).parent.mkdir(exist_ok=True)
        if not Path(p).exists():
            Path(p).write_bytes(b"MOCK_SEED_PLACEHOLDER")
    records = get_analytics().process_audio_files(fake_paths)
    print(f"[SEED] ✓ {len(records)} demo records. These use FAKE transcripts.\n")
    return {"seeded": len(records), "call_ids": [r.call_id for r in records],
            "warning": "DEMO DATA — fake transcripts. Upload your real WAV for actual analysis."}


@router.get("/debug/store")
async def debug_store():
    store   = get_store()
    records = store.all_records()
    summary = [{"call_id":r.get("call_id"), "status":r.get("status"), "score":r.get("total_score"),
                "grade":r.get("grade"), "transcript_lines":len(r.get("transcript",[])),
                "has_scorecard":r.get("scorecard") is not None, "file":r.get("file_name")} for r in records]
    for s in summary:
        print(f"[DEBUG STORE] {s}")
    return {"total": len(records), "records": summary}


@router.get("/debug/env")
async def debug_env():
    """See exactly which mode is active and what files are uploaded."""
    use_mock  = os.getenv("USE_MOCK", "true").lower() == "true"
    has_key   = bool(os.getenv("sarvam_api_key"))
    uploads   = list(Path("uploads").glob("*")) if Path("uploads").exists() else []
    info = {
        "USE_MOCK":        os.getenv("USE_MOCK", "not set (defaults to true)"),
        "mode":            "MOCK — real audio NOT transcribed" if use_mock else "LIVE — Sarvam AI",
        "sarvam_key_set":  has_key,
        "uploads_dir":     str(Path("uploads").absolute()),
        "uploaded_files":  [{"name":f.name, "size_bytes":f.stat().st_size} for f in uploads],
        "store_file":      str(Path("outputs/call_store.json").absolute()),
        "store_exists":    Path("outputs/call_store.json").exists(),
    }
    print(f"\n[DEBUG ENV] {info}")
    return info


@router.delete("/debug/reset")
async def reset_store():
    import json
    import services.call_store as cs
    Path("outputs/call_store.json").write_text(json.dumps({"records": {}, "job_index": {}}))
    cs._store_instance = None
    print("[DEBUG RESET] Store cleared.")
    return {"message": "Store wiped. All records cleared."}

# ////////////////////////////////////////////////////////////////////////////////////////////

"""
routes/api.py — PRODUCTION VERSION with full console logging
Every step prints to console so you can see EXACTLY what is happening.
"""

# import os
# import shutil
# import traceback
# from pathlib import Path
# from typing import Optional, List
# from datetime import datetime

# from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
# from fastapi.responses import FileResponse

# from services.call_store import get_store
# from models.schemas import (
#     UploadResponse, JobStatusResponse, JobStatus, CallRecord,
# )

# router = APIRouter()

# UPLOAD_DIR = Path("uploads")
# UPLOAD_DIR.mkdir(exist_ok=True)

# _analytics = None

# def get_analytics():
#     global _analytics
#     if _analytics is None:
#         use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
#         print("\n" + "="*60)
#         print(f"[ANALYTICS INIT] USE_MOCK env = {os.getenv('USE_MOCK', 'not set (defaulting true)')}")
#         print(f"[ANALYTICS INIT] Mode: {'MOCK' if use_mock else 'LIVE'}")
#         if use_mock:
#             from services.analytics import CallAnalytics
#             _analytics = CallAnalytics(use_mock=True)
#             print("[ANALYTICS INIT] ⚠️  MOCK MODE — uploaded audio will NOT be transcribed")
#             print("[ANALYTICS INIT]    Fix: set USE_MOCK=false and sarvam_api_key in .env")
#         else:
#             from sarvamai import SarvamAI
#             from dotenv import load_dotenv
#             load_dotenv()
#             api_key = os.getenv("sarvam_api_key")
#             if not api_key:
#                 raise RuntimeError("sarvam_api_key not found in .env — add it or set USE_MOCK=true")
#             print(f"[ANALYTICS INIT] ✓ Sarvam key loaded (...{api_key[-4:]})")
#             client = SarvamAI(api_subscription_key=api_key)
#             from services.analytics import CallAnalytics
#             _analytics = CallAnalytics(client=client, use_mock=False)
#             print("[ANALYTICS INIT] ✓ LIVE — Sarvam AI will transcribe your audio")
#         print("="*60 + "\n")
#     return _analytics


# def _process_sync(audio_paths: List[str], call_ids: List[str], job_id: str):
#     store    = get_store()
#     use_mock = os.getenv("USE_MOCK", "true").lower() == "true"

#     print("\n" + "█"*60)
#     print(f"[BG] Job {job_id} started")
#     print(f"[BG] Mode: {'MOCK (fake transcript)' if use_mock else 'LIVE (Sarvam AI)'}")
#     for p in audio_paths:
#         path = Path(p)
#         size = path.stat().st_size if path.exists() else -1
#         print(f"[BG] File: {path.name}  size={size} bytes  exists={path.exists()}")

#     for cid in call_ids:
#         store.update_status(cid, JobStatus.PROCESSING)
#     print(f"[BG] All {len(call_ids)} call(s) marked PROCESSING")

#     try:
#         analytics = get_analytics()
#         print(f"[BG] Calling analytics.process_audio_files({audio_paths})")
#         records = analytics.process_audio_files(audio_paths)
#         print(f"[BG] ✓ Done — {len(records)} record(s):")
#         for r in records:
#             print(f"  call_id={r.call_id}  score={r.total_score}  grade={r.grade}  transcript={len(r.transcript)} lines")
#     except Exception as e:
#         print(f"[BG] ✗ FAILED: {e}")
#         traceback.print_exc()
#         for cid in call_ids:
#             store.update_status(cid, JobStatus.FAILED)
#     print("█"*60 + "\n")


# @router.post("/upload", response_model=UploadResponse)
# async def upload_audio(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
#     import uuid
#     from services.transcription import _extract_call_id_from_filename, _extract_phone_from_filename

#     job_id     = f"job-{uuid.uuid4().hex[:8]}"
#     saved_paths = []
#     call_ids   = []
#     store      = get_store()
#     use_mock   = os.getenv("USE_MOCK", "true").lower() == "true"

#     print("\n" + "="*60)
#     print(f"[UPLOAD] {len(files)} file(s) received  mode={'MOCK' if use_mock else 'LIVE'}")

#     for file in files:
#         dest = UPLOAD_DIR / file.filename
#         with dest.open("wb") as f:
#             shutil.copyfileobj(file.file, f)
#         size    = dest.stat().st_size
#         call_id = _extract_call_id_from_filename(file.filename)
#         phone   = _extract_phone_from_filename(file.filename)

#         print(f"[UPLOAD] Saved {file.filename}  size={size} bytes  call_id={call_id}  phone={phone}")
#         if size < 1000:
#             print(f"[UPLOAD] ⚠️  File looks too small ({size} bytes) — may be corrupt")

#         saved_paths.append(str(dest))
#         call_ids.append(call_id)

#         pending = CallRecord(
#             call_id=call_id, file_name=file.filename,
#             audio_url=f"/api/audio/{call_id}", job_id=job_id,
#             status=JobStatus.PENDING, created_at=datetime.now().isoformat(),
#             duration_seconds=0.0, duration_formatted="—",
#             agent_id="UNKNOWN", phone_number=phone,
#             transcript=[], speaker_stats=[],
#         )
#         store.upsert(pending)

#     if use_mock:
#         print(f"[UPLOAD] ⚠️  MOCK MODE: Your audio will NOT be transcribed. Fake transcript will be used.")
#         print(f"[UPLOAD]    To use real Sarvam AI: set USE_MOCK=false + sarvam_api_key in backend/.env")

#     background_tasks.add_task(_process_sync, saved_paths, call_ids, job_id)
#     print(f"[UPLOAD] Job {job_id} queued")
#     print("="*60 + "\n")

#     return UploadResponse(
#         job_id=job_id, files_queued=len(files), status=JobStatus.PENDING,
#         message=f"{len(files)} file(s) queued ({'MOCK mode — fake transcript' if use_mock else 'LIVE mode — Sarvam AI'}).",
#     )


# @router.get("/dashboard")
# async def get_dashboard(grade: Optional[str] = Query(default=None)):
#     store  = get_store()
#     result = store.build_dashboard(grade_filter=grade).model_dump()
#     print(f"[DASHBOARD] {len(result['calls'])} calls  grade={grade}  metrics={result['metrics']}")
#     return result


# @router.get("/call/{call_id}")
# async def get_call(call_id: str):
#     store  = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         print(f"[CALL] 404: {call_id}")
#         raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")
#     print(f"[CALL] {call_id}  status={record.get('status')}  score={record.get('total_score')}  transcript={len(record.get('transcript',[]))} lines")
#     return record


# @router.get("/jobs/{job_id}", response_model=JobStatusResponse)
# async def get_job_status(job_id: str):
#     store  = get_store()
#     record = store.get_by_job_id(job_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
#     status = record.get("status", "pending")
#     msgs   = {"pending":"Queued...","processing":"Transcribing...","completed":"Done.","failed":"Failed — check logs."}
#     return JobStatusResponse(job_id=job_id, status=status, progress_message=msgs.get(status,"?"), call_id=record.get("call_id"))


# @router.get("/jobs")
# async def list_jobs():
#     store = get_store()
#     return {"jobs": store.all_records()}


# @router.get("/leaderboard")
# async def get_leaderboard():
#     return {"leaderboard": get_analytics().get_leaderboard()}


# @router.get("/audio/{call_id}")
# async def serve_audio(call_id: str):
#     store  = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail="Call not found.")

#     file_name  = record.get("file_name", "")
#     audio_path = UPLOAD_DIR / file_name

#     print(f"[AUDIO] {call_id} → {audio_path}  exists={audio_path.exists()}", end="")
#     if audio_path.exists():
#         sz = audio_path.stat().st_size
#         print(f"  size={sz} bytes")
#     else:
#         print()

#     if not audio_path.exists():
#         raise HTTPException(status_code=404, detail=f"Audio not on disk: {audio_path.absolute()}")

#     sz = audio_path.stat().st_size
#     if sz < 100:
#         raise HTTPException(
#             status_code=422,
#             detail="Demo/seed call — no real audio. Upload your own WAV file to hear playback."
#         )

#     ext  = audio_path.suffix.lower()
#     mime = {".wav":"audio/wav",".mp3":"audio/mpeg",".m4a":"audio/mp4",".ogg":"audio/ogg",".webm":"audio/webm"}.get(ext,"audio/wav")
#     return FileResponse(path=str(audio_path), media_type=mime, filename=file_name,
#                         headers={"Accept-Ranges":"bytes","Cache-Control":"no-cache"})


# @router.post("/seed")
# async def seed_mock_data():
#     if os.getenv("USE_MOCK", "true").lower() != "true":
#         raise HTTPException(status_code=403, detail="Seed only available when USE_MOCK=true")
#     print("\n[SEED] Creating 3 demo records with fake transcripts...")
#     fake_paths = [
#         "uploads/4174_09890382855_07-Mar-26-14-28-19.WAV",
#         "uploads/4175_09123456789_07-Mar-26-15-10-44.WAV",
#         "uploads/4176_09765432100_07-Mar-26-15-45-30.WAV",
#     ]
#     for p in fake_paths:
#         Path(p).parent.mkdir(exist_ok=True)
#         if not Path(p).exists():
#             Path(p).write_bytes(b"MOCK_SEED_PLACEHOLDER")
#     records = get_analytics().process_audio_files(fake_paths)
#     print(f"[SEED] ✓ {len(records)} demo records. These use FAKE transcripts.\n")
#     return {"seeded": len(records), "call_ids": [r.call_id for r in records],
#             "warning": "DEMO DATA — fake transcripts. Upload your real WAV for actual analysis."}


# @router.get("/debug/store")
# async def debug_store():
#     store   = get_store()
#     records = store.all_records()
#     summary = [{"call_id":r.get("call_id"), "status":r.get("status"), "score":r.get("total_score"),
#                 "grade":r.get("grade"), "transcript_lines":len(r.get("transcript",[])),
#                 "has_scorecard":r.get("scorecard") is not None, "file":r.get("file_name")} for r in records]
#     for s in summary:
#         print(f"[DEBUG STORE] {s}")
#     return {"total": len(records), "records": summary}


# @router.get("/debug/env")
# async def debug_env():
#     """See exactly which mode is active and what files are uploaded."""
#     use_mock  = os.getenv("USE_MOCK", "true").lower() == "true"
#     has_key   = bool(os.getenv("sarvam_api_key"))
#     uploads   = list(Path("uploads").glob("*")) if Path("uploads").exists() else []
#     info = {
#         "USE_MOCK":        os.getenv("USE_MOCK", "not set (defaults to true)"),
#         "mode":            "MOCK — real audio NOT transcribed" if use_mock else "LIVE — Sarvam AI",
#         "sarvam_key_set":  has_key,
#         "uploads_dir":     str(Path("uploads").absolute()),
#         "uploaded_files":  [{"name":f.name, "size_bytes":f.stat().st_size} for f in uploads],
#         "store_file":      str(Path("outputs/call_store.json").absolute()),
#         "store_exists":    Path("outputs/call_store.json").exists(),
#     }
#     print(f"\n[DEBUG ENV] {info}")
#     return info


# @router.delete("/debug/reset")
# async def reset_store():
#     import json
#     import services.call_store as cs
#     Path("outputs/call_store.json").write_text(json.dumps({"records": {}, "job_index": {}}))
#     cs._store_instance = None
#     print("[DEBUG RESET] Store cleared.")
#     return {"message": "Store wiped. All records cleared."}


# # /////////////////////////////////////////////////////////////
# """
# routes/api.py  —  FIXED VERSION
# Key fixes:
# 1. Background task is now a plain sync function (not async) — fixes silent failure
# 2. Errors are printed to console with full traceback
# 3. /debug endpoint added to see exactly what's in the store
# 4. /debug/reset endpoint to wipe stale pending records
# """

# """
# routes/api.py  —  FIXED VERSION
# Key fixes:
# 1. Background task is now a plain sync function (not async) — fixes silent failure
# 2. Errors are printed to console with full traceback
# 3. /debug endpoint added to see exactly what's in the store
# 4. /debug/reset endpoint to wipe stale pending records
# """




# import os
# import shutil
# import traceback
# from pathlib import Path
# from typing import Optional, List
# from concurrent.futures import ThreadPoolExecutor

# from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
# from fastapi.responses import FileResponse

# from services.call_store import get_store
# from models.schemas import (
#     UploadResponse, JobStatusResponse, JobStatus,
#     DashboardResponse, CallRecord,
# )

# router = APIRouter()

# UPLOAD_DIR = Path("uploads")
# UPLOAD_DIR.mkdir(exist_ok=True)

# _analytics = None

# def get_analytics():
#     global _analytics
#     if _analytics is None:
#         from services.analytics import CallAnalytics
#         use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
#         if use_mock:
#             _analytics = CallAnalytics(use_mock=True)
#             print("[API] Analytics ready in MOCK mode.")
#         else:
#             from sarvamai import SarvamAI
#             from dotenv import load_dotenv
#             load_dotenv()
#             api_key = os.getenv("sarvam_api_key")
#             if not api_key:
#                 raise RuntimeError("sarvam_api_key not set in .env and USE_MOCK is false")
#             client = SarvamAI(api_subscription_key=api_key)
#             _analytics = CallAnalytics(client=client, use_mock=False)
#             print("[API] Analytics ready in LIVE mode.")
#     return _analytics


# # ─── BUG FIX: Background task must be a plain SYNC function ──────────────────
# # FastAPI's BackgroundTasks runs sync functions in a thread automatically.
# # The original async + run_in_executor caused SILENT FAILURES — nothing ran.

# def _process_sync(audio_paths: List[str], call_ids: List[str], job_id: str):
#     """
#     SYNC background worker. FastAPI runs this in a thread automatically.
#     DO NOT make this async — that was the original bug causing "pending" forever.
#     """
#     store = get_store()
#     print(f"[BG] Starting job {job_id} for: {audio_paths}")

#     for cid in call_ids:
#         store.update_status(cid, JobStatus.PROCESSING)

#     try:
#         analytics = get_analytics()
#         records = analytics.process_audio_files(audio_paths)
#         print(f"[BG] ✓ Job {job_id} done — {len(records)} record(s) stored.")
#     except Exception as e:
#         print(f"[BG] ✗ Job {job_id} FAILED:")
#         traceback.print_exc()
#         for cid in call_ids:
#             store.update_status(cid, JobStatus.FAILED)


# # ─── Upload ───────────────────────────────────────────────────────────────────

# @router.post("/upload", response_model=UploadResponse)
# async def upload_audio(
#     background_tasks: BackgroundTasks,
#     files: List[UploadFile] = File(...),
# ):
#     import uuid
#     from datetime import datetime
#     from services.transcription import _extract_call_id_from_filename, _extract_phone_from_filename

#     job_id = f"job-{uuid.uuid4().hex[:8]}"
#     saved_paths = []
#     call_ids = []
#     store = get_store()

#     for file in files:
#         dest = UPLOAD_DIR / file.filename
#         with dest.open("wb") as f:
#             shutil.copyfileobj(file.file, f)
#         saved_paths.append(str(dest))

#         call_id = _extract_call_id_from_filename(file.filename)
#         call_ids.append(call_id)

#         pending = CallRecord(
#             call_id=call_id,
#             file_name=file.filename,
#             audio_url=f"/api/audio/{call_id}",
#             job_id=job_id,
#             status=JobStatus.PENDING,
#             created_at=datetime.now().isoformat(),
#             duration_seconds=0.0,
#             duration_formatted="—",
#             agent_id="UNKNOWN",
#             phone_number=_extract_phone_from_filename(file.filename),
#             transcript=[],
#             speaker_stats=[],
#         )
#         store.upsert(pending)
#         print(f"[Upload] Pending record created: call_id={call_id}")

#     # KEY FIX: pass _process_sync (sync function), not an async coroutine
#     background_tasks.add_task(_process_sync, saved_paths, call_ids, job_id)

#     return UploadResponse(
#         job_id=job_id,
#         files_queued=len(files),
#         status=JobStatus.PENDING,
#         message=f"{len(files)} file(s) queued. Poll /api/call/CALL_ID for updates.",
#     )


# # ─── Dashboard ────────────────────────────────────────────────────────────────

# @router.get("/dashboard")
# async def get_dashboard(
#     grade: Optional[str] = Query(default=None, description="Filter: excellent | good | average | poor")
# ):
#     store = get_store()
#     return store.build_dashboard(grade_filter=grade).model_dump()


# # ─── Single Call Detail ───────────────────────────────────────────────────────

# @router.get("/call/{call_id}")
# async def get_call(call_id: str):
#     store = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")
#     return record


# # ─── Job Status ───────────────────────────────────────────────────────────────

# @router.get("/jobs/{job_id}", response_model=JobStatusResponse)
# async def get_job_status(job_id: str):
#     store = get_store()
#     record = store.get_by_job_id(job_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

#     status = record.get("status", JobStatus.PENDING.value)
#     messages = {
#         "pending":    "Queued for processing...",
#         "processing": "Transcribing and analysing...",
#         "completed":  "Analysis complete.",
#         "failed":     "Processing failed. Check server logs for full traceback.",
#     }
#     return JobStatusResponse(
#         job_id=job_id,
#         status=status,
#         progress_message=messages.get(status, "Unknown"),
#         call_id=record.get("call_id"),
#     )


# @router.get("/jobs")
# async def list_jobs():
#     store = get_store()
#     return {"jobs": store.all_records()}


# # ─── Leaderboard ──────────────────────────────────────────────────────────────

# @router.get("/leaderboard")
# async def get_leaderboard():
#     analytics = get_analytics()
#     return {"leaderboard": analytics.get_leaderboard()}


# # ─── Audio Serving ────────────────────────────────────────────────────────────

# @router.get("/audio/{call_id}")
# async def serve_audio(call_id: str):
#     store = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail="Call not found.")

#     file_name = record.get("file_name", "")
#     audio_path = UPLOAD_DIR / file_name

#     if not audio_path.exists():
#         raise HTTPException(
#             status_code=404,
#             detail=f"Audio file not found on disk: {audio_path.absolute()}"
#         )

#     ext = audio_path.suffix.lower()
#     media_types = {
#         ".wav": "audio/wav", ".mp3": "audio/mpeg",
#         ".m4a": "audio/mp4", ".ogg": "audio/ogg",
#     }
#     return FileResponse(
#         path=str(audio_path),
#         media_type=media_types.get(ext, "audio/wav"),
#         filename=file_name,
#         headers={"Accept-Ranges": "bytes"},
#     )


# # ─── Seed ─────────────────────────────────────────────────────────────────────

# @router.post("/seed")
# async def seed_mock_data():
#     """Load 3 mock completed calls instantly. Requires USE_MOCK=true."""
#     if os.getenv("USE_MOCK", "true").lower() != "true":
#         raise HTTPException(status_code=403, detail="Seed only available when USE_MOCK=true")

#     fake_paths = [
#         "uploads/4174_09890382855_07-Mar-26-14-28-19.WAV",
#         "uploads/4175_09123456789_07-Mar-26-15-10-44.WAV",
#         "uploads/4176_09765432100_07-Mar-26-15-45-30.WAV",
#     ]
#     for p in fake_paths:
#         Path(p).parent.mkdir(exist_ok=True)
#         if not Path(p).exists():
#             Path(p).write_bytes(b"MOCK")

#     # Runs synchronously — fast in mock mode
#     analytics = get_analytics()
#     records = analytics.process_audio_files(fake_paths)

#     return {
#         "seeded": len(records),
#         "call_ids": [r.call_id for r in records],
#         "message": "Done! Refresh /api/dashboard to see data.",
#     }


# # ─── Debug endpoints ──────────────────────────────────────────────────────────

# @router.get("/debug/store")
# async def debug_store():
#     """Shows exactly what is in the call store — use to diagnose 'pending' issues."""
#     store = get_store()
#     all_records = store.all_records()
#     return {
#         "total_records": len(all_records),
#         "records": [
#             {
#                 "call_id": r.get("call_id"),
#                 "status": r.get("status"),
#                 "grade": r.get("grade"),
#                 "total_score": r.get("total_score"),
#                 "transcript_lines": len(r.get("transcript", [])),
#                 "has_scorecard": r.get("scorecard") is not None,
#                 "file_name": r.get("file_name"),
#                 "created_at": r.get("created_at"),
#             }
#             for r in all_records
#         ]
#     }


# @router.delete("/debug/reset")
# async def reset_store():
#     """Wipe ALL records. Use when stuck calls won't clear."""
#     import json
#     import services.call_store as cs

#     store_file = Path("outputs/call_store.json")
#     store_file.write_text(json.dumps({"records": {}, "job_index": {}}))

#     # Force the singleton to reload from the now-empty file
#     cs._store_instance = None

#     return {"message": "Store wiped. All records cleared."}

# -----------------------------------------------------------------------------------------------------

# import os
# import shutil
# import traceback
# from pathlib import Path
# from typing import Optional, List
# from concurrent.futures import ThreadPoolExecutor

# from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
# from fastapi.responses import FileResponse

# from services.call_store import get_store
# from models.schemas import (
#     UploadResponse, JobStatusResponse, JobStatus,
#     DashboardResponse, CallRecord,
# )

# router = APIRouter()

# UPLOAD_DIR = Path("uploads")
# UPLOAD_DIR.mkdir(exist_ok=True)

# _analytics = None

# def get_analytics():
#     global _analytics
#     if _analytics is None:
#         from services.analytics import CallAnalytics
#         use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
#         if use_mock:
#             _analytics = CallAnalytics(use_mock=True)
#             print("[API] Analytics ready in MOCK mode.")
#         else:
#             from sarvamai import SarvamAI
#             from dotenv import load_dotenv
#             load_dotenv()
#             api_key = os.getenv("sarvam_api_key")
#             if not api_key:
#                 raise RuntimeError("sarvam_api_key not set in .env and USE_MOCK is false")
#             client = SarvamAI(api_subscription_key=api_key)
#             _analytics = CallAnalytics(client=client, use_mock=False)
#             print("[API] Analytics ready in LIVE mode.")
#     return _analytics


# # ─── BUG FIX: Background task must be a plain SYNC function ──────────────────
# # FastAPI's BackgroundTasks runs sync functions in a thread automatically.
# # The original async + run_in_executor caused SILENT FAILURES — nothing ran.

# def _process_sync(audio_paths: List[str], call_ids: List[str], job_id: str):
#     """
#     SYNC background worker. FastAPI runs this in a thread automatically.
#     DO NOT make this async — that was the original bug causing "pending" forever.
#     """
#     store = get_store()
#     print(f"[BG] Starting job {job_id} for: {audio_paths}")

#     for cid in call_ids:
#         store.update_status(cid, JobStatus.PROCESSING)

#     try:
#         analytics = get_analytics()
#         records = analytics.process_audio_files(audio_paths)
#         print(f"[BG] ✓ Job {job_id} done — {len(records)} record(s) stored.")
#     except Exception as e:
#         print(f"[BG] ✗ Job {job_id} FAILED:")
#         traceback.print_exc()
#         for cid in call_ids:
#             store.update_status(cid, JobStatus.FAILED)


# # ─── Upload ───────────────────────────────────────────────────────────────────

# @router.post("/upload", response_model=UploadResponse)
# async def upload_audio(
#     background_tasks: BackgroundTasks,
#     files: List[UploadFile] = File(...),
# ):
#     import uuid
#     from datetime import datetime
#     from services.transcription import _extract_call_id_from_filename, _extract_phone_from_filename

#     job_id = f"job-{uuid.uuid4().hex[:8]}"
#     saved_paths = []
#     call_ids = []
#     store = get_store()

#     for file in files:
#         dest = UPLOAD_DIR / file.filename
#         with dest.open("wb") as f:
#             shutil.copyfileobj(file.file, f)
#         saved_paths.append(str(dest))

#         call_id = _extract_call_id_from_filename(file.filename)
#         call_ids.append(call_id)

#         pending = CallRecord(
#             call_id=call_id,
#             file_name=file.filename,
#             audio_url=f"/api/audio/{call_id}",
#             job_id=job_id,
#             status=JobStatus.PENDING,
#             created_at=datetime.now().isoformat(),
#             duration_seconds=0.0,
#             duration_formatted="—",
#             agent_id="UNKNOWN",
#             phone_number=_extract_phone_from_filename(file.filename),
#             transcript=[],
#             speaker_stats=[],
#         )
#         store.upsert(pending)
#         print(f"[Upload] Pending record created: call_id={call_id}")

#     # KEY FIX: pass _process_sync (sync function), not an async coroutine
#     background_tasks.add_task(_process_sync, saved_paths, call_ids, job_id)

#     return UploadResponse(
#         job_id=job_id,
#         files_queued=len(files),
#         status=JobStatus.PENDING,
#         message=f"{len(files)} file(s) queued. Poll /api/call/CALL_ID for updates.",
#     )


# # ─── Dashboard ────────────────────────────────────────────────────────────────

# @router.get("/dashboard")
# async def get_dashboard(
#     grade: Optional[str] = Query(default=None, description="Filter: excellent | good | average | poor")
# ):
#     store = get_store()
#     return store.build_dashboard(grade_filter=grade).dict()


# # ─── Single Call Detail ───────────────────────────────────────────────────────

# @router.get("/call/{call_id}")
# async def get_call(call_id: str):
#     store = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")
#     return record


# # ─── Job Status ───────────────────────────────────────────────────────────────

# @router.get("/jobs/{job_id}", response_model=JobStatusResponse)
# async def get_job_status(job_id: str):
#     store = get_store()
#     record = store.get_by_job_id(job_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

#     status = record.get("status", JobStatus.PENDING.value)
#     messages = {
#         "pending":    "Queued for processing...",
#         "processing": "Transcribing and analysing...",
#         "completed":  "Analysis complete.",
#         "failed":     "Processing failed. Check server logs for full traceback.",
#     }
#     return JobStatusResponse(
#         job_id=job_id,
#         status=status,
#         progress_message=messages.get(status, "Unknown"),
#         call_id=record.get("call_id"),
#     )


# @router.get("/jobs")
# async def list_jobs():
#     store = get_store()
#     return {"jobs": store.all_records()}


# # ─── Leaderboard ──────────────────────────────────────────────────────────────

# @router.get("/leaderboard")
# async def get_leaderboard():
#     analytics = get_analytics()
#     return {"leaderboard": analytics.get_leaderboard()}


# # ─── Audio Serving ────────────────────────────────────────────────────────────

# @router.get("/audio/{call_id}")
# async def serve_audio(call_id: str):
#     store = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail="Call not found.")

#     file_name = record.get("file_name", "")
#     audio_path = UPLOAD_DIR / file_name

#     if not audio_path.exists():
#         raise HTTPException(
#             status_code=404,
#             detail=f"Audio file not found on disk: {audio_path.absolute()}"
#         )

#     ext = audio_path.suffix.lower()
#     media_types = {
#         ".wav": "audio/wav", ".mp3": "audio/mpeg",
#         ".m4a": "audio/mp4", ".ogg": "audio/ogg",
#     }
#     return FileResponse(
#         path=str(audio_path),
#         media_type=media_types.get(ext, "audio/wav"),
#         filename=file_name,
#         headers={"Accept-Ranges": "bytes"},
#     )


# # ─── Seed ─────────────────────────────────────────────────────────────────────

# @router.post("/seed")
# async def seed_mock_data():
#     """Load 3 mock completed calls instantly. Requires USE_MOCK=true."""
#     if os.getenv("USE_MOCK", "true").lower() != "true":
#         raise HTTPException(status_code=403, detail="Seed only available when USE_MOCK=true")

#     fake_paths = [
#         "uploads/4174_09890382855_07-Mar-26-14-28-19.WAV",
#         "uploads/4175_09123456789_07-Mar-26-15-10-44.WAV",
#         "uploads/4176_09765432100_07-Mar-26-15-45-30.WAV",
#     ]
#     for p in fake_paths:
#         Path(p).parent.mkdir(exist_ok=True)
#         if not Path(p).exists():
#             Path(p).write_bytes(b"MOCK")

#     # Runs synchronously — fast in mock mode
#     analytics = get_analytics()
#     records = analytics.process_audio_files(fake_paths)

#     return {
#         "seeded": len(records),
#         "call_ids": [r.call_id for r in records],
#         "message": "Done! Refresh /api/dashboard to see data.",
#     }


# # ─── Debug endpoints ──────────────────────────────────────────────────────────

# @router.get("/debug/store")
# async def debug_store():
#     """Shows exactly what is in the call store — use to diagnose 'pending' issues."""
#     store = get_store()
#     all_records = store.all_records()
#     return {
#         "total_records": len(all_records),
#         "records": [
#             {
#                 "call_id": r.get("call_id"),
#                 "status": r.get("status"),
#                 "grade": r.get("grade"),
#                 "total_score": r.get("total_score"),
#                 "transcript_lines": len(r.get("transcript", [])),
#                 "has_scorecard": r.get("scorecard") is not None,
#                 "file_name": r.get("file_name"),
#                 "created_at": r.get("created_at"),
#             }
#             for r in all_records
#         ]
#     }


# @router.delete("/debug/reset")
# async def reset_store():
#     """Wipe ALL records. Use when stuck calls won't clear."""
#     import json
#     import services.call_store as cs

#     store_file = Path("outputs/call_store.json")
#     store_file.write_text(json.dumps({"records": {}, "job_index": {}}))

#     # Force the singleton to reload from the now-empty file
#     cs._store_instance = None

#     return {"message": "Store wiped. All records cleared."}



# """
# routes/api.py
# All FastAPI route handlers for the CallIQ dashboard.
# """

# import os
# import shutil
# import asyncio
# from pathlib import Path
# from typing import Optional, List
# from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
# from fastapi.responses import FileResponse

# from services.call_store import get_store
# from models.schemas import (
#     UploadResponse, JobStatusResponse, JobStatus,
#     DashboardResponse, CallRecord,
# )

# router = APIRouter()

# UPLOAD_DIR = Path("uploads")
# UPLOAD_DIR.mkdir(exist_ok=True)

# # Lazy import analytics to avoid circular imports
# _analytics = None

# def get_analytics():
#     global _analytics
#     if _analytics is None:
#         from services.analytics import CallAnalytics
#         use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
#         if use_mock:
#             _analytics = CallAnalytics(use_mock=True)
#         else:
#             from sarvamai import SarvamAI
#             from dotenv import load_dotenv
#             load_dotenv()
#             api_key = os.getenv("sarvam_api_key")
#             client = SarvamAI(api_subscription_key=api_key)
#             _analytics = CallAnalytics(client=client, use_mock=False)
#     return _analytics


# # ─── Background processing ────────────────────────────────────────────────────

# async def _process_in_background(audio_paths: List[str], call_ids: List[str]):
#     """Run analytics pipeline in background thread."""
#     store = get_store()
#     analytics = get_analytics()

#     # Mark all as processing
#     for cid in call_ids:
#         store.update_status(cid, JobStatus.PROCESSING)

#     try:
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(None, analytics.process_audio_files, audio_paths)
#     except Exception as e:
#         print(f"[API] Background processing failed: {e}")
#         for cid in call_ids:
#             store.update_status(cid, JobStatus.FAILED)


# # ─── Upload ───────────────────────────────────────────────────────────────────

# @router.post("/upload", response_model=UploadResponse)
# async def upload_audio(
#     background_tasks: BackgroundTasks,
#     files: List[UploadFile] = File(...),
# ):
#     """
#     Upload one or more audio files for transcription + QA analysis.
#     Processing happens in the background; poll /jobs/{job_id} for status.
#     """
#     import uuid
#     job_id = f"job-{uuid.uuid4().hex[:8]}"
#     saved_paths = []
#     call_ids = []

#     store = get_store()

#     for file in files:
#         dest = UPLOAD_DIR / file.filename
#         with dest.open("wb") as f:
#             shutil.copyfileobj(file.file, f)
#         saved_paths.append(str(dest))

#         # Create a pending record immediately so the UI shows it
#         from models.schemas import CallRecord, TranscriptEntry, SpeakerStats
#         from services.transcription import _extract_call_id_from_filename, _extract_phone_from_filename
#         from datetime import datetime

#         call_id = _extract_call_id_from_filename(file.filename)
#         call_ids.append(call_id)

#         pending = CallRecord(
#             call_id=call_id,
#             file_name=file.filename,
#             audio_url=f"/audio/{call_id}",
#             job_id=job_id,
#             status=JobStatus.PENDING,
#             created_at=datetime.now().isoformat(),
#             duration_seconds=0.0,
#             duration_formatted="—",
#             agent_id="UNKNOWN",
#             phone_number=_extract_phone_from_filename(file.filename),
#             transcript=[],
#             speaker_stats=[],
#         )
#         store.upsert(pending)

#     background_tasks.add_task(_process_in_background, saved_paths, call_ids)

#     return UploadResponse(
#         job_id=job_id,
#         files_queued=len(files),
#         status=JobStatus.PENDING,
#         message=f"{len(files)} file(s) queued for processing.",
#     )


# # ─── Dashboard ────────────────────────────────────────────────────────────────

# @router.get("/dashboard")
# async def get_dashboard(
#     grade: Optional[str] = Query(
#         default=None,
#         description="Filter call list by grade: excellent | good | average | poor"
#     )
# ):
#     """
#     Returns full dashboard data:
#     - metrics: total_calls, attended, not_attended, excellent, good, average, poor
#     - calls: filtered list of calls for the sidebar

#     Usage:
#       GET /dashboard              → all calls
#       GET /dashboard?grade=excellent → only excellent calls
#       GET /dashboard?grade=poor   → only poor calls
#     """
#     store = get_store()
#     return store.build_dashboard(grade_filter=grade).dict()


# # ─── Single Call Detail ───────────────────────────────────────────────────────

# @router.get("/call/{call_id}")
# async def get_call(call_id: str):
#     """
#     Returns full call detail:
#     - transcript (with is_flagged markers for red-line view)
#     - scorecard (all sections, parameters, scores, reasons)
#     - fatal flags
#     - speaker stats
#     - audio_url
#     """
#     store = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found.")
#     return record


# # ─── Job Status ───────────────────────────────────────────────────────────────

# @router.get("/jobs/{job_id}", response_model=JobStatusResponse)
# async def get_job_status(job_id: str):
#     """Poll this endpoint after upload to check processing status."""
#     store = get_store()
#     record = store.get_by_job_id(job_id)
#     if not record:
#         raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

#     status = record.get("status", JobStatus.PENDING.value)
#     messages = {
#         "pending":    "Queued for processing...",
#         "processing": "Transcribing and analysing...",
#         "completed":  "Analysis complete.",
#         "failed":     "Processing failed. Please retry.",
#     }

#     return JobStatusResponse(
#         job_id=job_id,
#         status=status,
#         progress_message=messages.get(status, "Unknown status."),
#         call_id=record.get("call_id"),
#     )


# @router.get("/jobs")
# async def list_jobs():
#     """List all jobs (for the sidebar)."""
#     store = get_store()
#     return {"jobs": store.all_records()}


# # ─── Leaderboard ──────────────────────────────────────────────────────────────

# @router.get("/leaderboard")
# async def get_leaderboard():
#     """Agent performance leaderboard — mirrors get_summary() output as JSON."""
#     analytics = get_analytics()
#     return {"leaderboard": analytics.get_leaderboard()}


# # ─── Audio File Serving ───────────────────────────────────────────────────────

# @router.get("/audio/{call_id}")
# async def serve_audio(call_id: str):
#     """
#     Serve the original audio file for the in-browser player.
#     Looks in uploads/ directory for matching filename.
#     """
#     store = get_store()
#     record = store.get_by_id(call_id)
#     if not record:
#         raise HTTPException(status_code=404, detail="Call not found.")

#     file_name = record.get("file_name", "")
#     audio_path = UPLOAD_DIR / file_name

#     if not audio_path.exists():
#         raise HTTPException(status_code=404, detail=f"Audio file not found: {file_name}")

#     # Determine media type from extension
#     ext = audio_path.suffix.lower()
#     media_types = {
#         ".wav": "audio/wav",
#         ".mp3": "audio/mpeg",
#         ".m4a": "audio/mp4",
#         ".ogg": "audio/ogg",
#     }
#     media_type = media_types.get(ext, "audio/wav")

#     return FileResponse(
#         path=str(audio_path),
#         media_type=media_type,
#         filename=file_name,
#     )


# # ─── Seed Endpoint (for testing without real audio) ──────────────────────────

# @router.post("/seed")
# async def seed_mock_data():
#     """
#     Loads mock data into the store so you can test the UI immediately.
#     Only available when USE_MOCK=true.
#     """
#     if os.getenv("USE_MOCK", "true").lower() != "true":
#         raise HTTPException(status_code=403, detail="Seed only available in mock mode.")

#     analytics = get_analytics()

#     # Process a fake audio path — mock service doesn't actually read the file
#     fake_paths = [
#         "uploads/4174_09890382855_07-Mar-26-14-28-19.WAV",
#         "uploads/4175_09123456789_07-Mar-26-15-10-44.WAV",
#         "uploads/4176_09765432100_07-Mar-26-15-45-30.WAV",
#     ]

#     # Create dummy files so the store records them
#     for p in fake_paths:
#         Path(p).parent.mkdir(exist_ok=True)
#         if not Path(p).exists():
#             Path(p).write_bytes(b"")  # empty file — mock doesn't read it

#     records = analytics.process_audio_files(fake_paths)

#     return {
#         "seeded": len(records),
#         "call_ids": [r.call_id for r in records],
#     }
