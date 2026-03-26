"""
services/call_store.py
In-memory + JSON-file persistence for all processed CallRecords.
Thread-safe with a simple RLock for concurrent FastAPI requests.
"""
"""
services/call_store.py
In-memory + JSON-file persistence for all processed CallRecords.
Thread-safe with a simple RLock for concurrent FastAPI requests.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from models.schemas import (
    CallRecord, CallListItem, DashboardMetrics,
    DashboardResponse, JobStatus, CallGrade,
)


STORE_FILE = Path("outputs/call_store.json")


def _ensure_store_dir():
    STORE_FILE.parent.mkdir(exist_ok=True)


class CallStore:
    """
    Central registry of all processed calls.
    Persists to outputs/call_store.json so data survives restarts.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._records: Dict[str, dict] = {}    # call_id → raw dict
        self._job_index: Dict[str, str] = {}   # job_id → call_id
        _ensure_store_dir()
        self._load_from_disk()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_from_disk(self):
        if STORE_FILE.exists():
            try:
                data = json.loads(STORE_FILE.read_text())
                self._records = data.get("records", {})
                self._job_index = data.get("job_index", {})
                print(f"[Store] Loaded {len(self._records)} call(s) from disk.")
            except Exception as e:
                print(f"[Store] Could not load from disk: {e}")

    def _save_to_disk(self):
        try:
            STORE_FILE.write_text(json.dumps({
                "records": self._records,
                "job_index": self._job_index,
            }, indent=2, default=str))
        except Exception as e:
            print(f"[Store] Could not save to disk: {e}")

    # ── Write ─────────────────────────────────────────────────────────────────

    def upsert(self, call: CallRecord):
        """Insert or update a call record."""
        with self._lock:
            self._records[call.call_id] = call.model_dump()
            self._job_index[call.job_id] = call.call_id
            self._save_to_disk()

    def update_status(self, call_id: str, status: JobStatus, **kwargs):
        """
        BUG FIX: Only update the status field + any explicit kwargs.
        Never wipes existing transcript/scorecard data already in the record.
        """
        with self._lock:
            if call_id in self._records:
                self._records[call_id]["status"] = status.value
                # Only merge kwargs that carry real values
                for k, v in kwargs.items():
                    if v is not None:
                        self._records[call_id][k] = v
                self._save_to_disk()
            else:
                print(f"[Store] update_status: call_id '{call_id}' not in store — skipping.")

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, call_id: str) -> Optional[dict]:
        with self._lock:
            return self._records.get(call_id)

    def get_by_job_id(self, job_id: str) -> Optional[dict]:
        with self._lock:
            call_id = self._job_index.get(job_id)
            return self._records.get(call_id) if call_id else None

    def all_records(self) -> List[dict]:
        with self._lock:
            return list(self._records.values())

    # ── Dashboard Builder ─────────────────────────────────────────────────────

    def build_dashboard(self, grade_filter: Optional[str] = None) -> DashboardResponse:
        """
        Returns metrics + call list.
        Optional grade_filter: "excellent" | "good" | "average" | "poor"
        """
        with self._lock:
            all_calls = list(self._records.values())

        completed = [c for c in all_calls if c.get("status") == JobStatus.COMPLETED.value]

        # ── Metrics (always over all completed calls) ──────────────────────────
        scores = [c["total_score"] for c in completed if c.get("total_score") is not None]
        durations = [c.get("duration_seconds", 0) for c in completed]

        def count_grade(g: str) -> int:
            return sum(1 for c in completed if c.get("grade") == g)

        metrics = DashboardMetrics(
            total_calls=len(all_calls),
            attended_calls=len(completed),
            not_attended=len(all_calls) - len(completed),
            excellent=count_grade(CallGrade.EXCELLENT.value),
            good=count_grade(CallGrade.GOOD.value),
            average=count_grade(CallGrade.AVERAGE.value),
            poor=count_grade(CallGrade.POOR.value),
            avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
            avg_duration=round(sum(durations) / len(durations), 1) if durations else 0.0,
            fatal_calls=sum(
                1 for c in completed
                if c.get("scorecard") and
                any(v == "F" for v in (c["scorecard"].get("fatal_flags") or {}).values())
            ),
        )

        # ── Call list (filtered if grade_filter given) ─────────────────────────
        filtered = completed if not grade_filter else [
            c for c in completed if c.get("grade") == grade_filter
        ]
        # Also include non-completed if no filter
        if not grade_filter:
            filtered = all_calls

        # Sort: newest first
        filtered.sort(key=lambda c: c.get("created_at", ""), reverse=True)

        call_items = [
            CallListItem(
                call_id=c["call_id"],
                file_name=c["file_name"],
                phone_number=c.get("phone_number"),
                agent_id=c.get("agent_id", "UNKNOWN"),
                duration_formatted=c.get("duration_formatted", "—"),
                created_at=c.get("created_at", ""),
                status=c.get("status", JobStatus.PENDING.value),
                total_score=c.get("total_score"),
                grade=c.get("grade"),
                letter_grade=_letter_from_grade(c.get("grade")),
                has_fatal=_has_fatal(c),
                audio_url=c.get("audio_url", ""),
            )
            for c in filtered
        ]

        return DashboardResponse(metrics=metrics, calls=call_items)

    def build_leaderboard(self) -> List[dict]:
        """Agent → avg score leaderboard (mirrors your original get_summary())."""
        with self._lock:
            all_calls = list(self._records.values())

        agent_data: Dict[str, dict] = {}
        for c in all_calls:
            if c.get("status") != JobStatus.COMPLETED.value:
                continue
            agent = c.get("agent_id", "UNKNOWN")
            score = c.get("total_score")
            if score is None:
                continue
            if agent not in agent_data:
                agent_data[agent] = {"scores": [], "calls": 0}
            agent_data[agent]["scores"].append(score)
            agent_data[agent]["calls"] += 1

        leaderboard = []
        for agent, data in agent_data.items():
            avg = round(sum(data["scores"]) / len(data["scores"]), 2)
            from services.parser import _grade_from_score
            grade, letter = _grade_from_score(int(avg))
            leaderboard.append({
                "agent_id": agent,
                "total_calls": data["calls"],
                "avg_score": avg,
                "grade": grade.value,
                "letter_grade": letter,
            })

        leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
        return leaderboard


# ── Helpers ────────────────────────────────────────────────────────────────────

def _letter_from_grade(grade: Optional[str]) -> Optional[str]:
    return {"excellent": "A", "good": "B", "average": "C", "poor": "D"}.get(grade or "")


def _has_fatal(call_dict: dict) -> bool:
    sc = call_dict.get("scorecard")
    if not sc:
        return False
    flags = sc.get("fatal_flags", {})
    return any(v == "F" for v in flags.values())


# ── Singleton ─────────────────────────────────────────────────────────────────
_store_instance: Optional[CallStore] = None

def get_store() -> CallStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = CallStore()
    return _store_instance

# ---------------------------------------------------------------------------------------------

# import json
# import threading
# from pathlib import Path
# from typing import Dict, List, Optional
# from datetime import datetime

# from models.schemas import (
#     CallRecord, CallListItem, DashboardMetrics,
#     DashboardResponse, JobStatus, CallGrade,
# )


# STORE_FILE = Path("outputs/call_store.json")


# def _ensure_store_dir():
#     STORE_FILE.parent.mkdir(exist_ok=True)


# class CallStore:
#     """
#     Central registry of all processed calls.
#     Persists to outputs/call_store.json so data survives restarts.
#     """

#     def __init__(self):
#         self._lock = threading.RLock()
#         self._records: Dict[str, dict] = {}    # call_id → raw dict
#         self._job_index: Dict[str, str] = {}   # job_id → call_id
#         _ensure_store_dir()
#         self._load_from_disk()

#     # ── Persistence ───────────────────────────────────────────────────────────

#     def _load_from_disk(self):
#         if STORE_FILE.exists():
#             try:
#                 data = json.loads(STORE_FILE.read_text())
#                 self._records = data.get("records", {})
#                 self._job_index = data.get("job_index", {})
#                 print(f"[Store] Loaded {len(self._records)} call(s) from disk.")
#             except Exception as e:
#                 print(f"[Store] Could not load from disk: {e}")

#     def _save_to_disk(self):
#         try:
#             STORE_FILE.write_text(json.dumps({
#                 "records": self._records,
#                 "job_index": self._job_index,
#             }, indent=2, default=str))
#         except Exception as e:
#             print(f"[Store] Could not save to disk: {e}")

#     # ── Write ─────────────────────────────────────────────────────────────────

#     def upsert(self, call: CallRecord):
#         """Insert or update a call record."""
#         with self._lock:
#             self._records[call.call_id] = call.dict()
#             self._job_index[call.job_id] = call.call_id
#             self._save_to_disk()


#     def update_status(self, call_id: str, status: JobStatus, **kwargs):
#         """
#         BUG FIX: Only update the status field + any explicit kwargs.
#         Never wipes existing transcript/scorecard data already in the record.
#         """
#         with self._lock:
#             if call_id in self._records:
#                 self._records[call_id]["status"] = status.value
#                 # Only merge kwargs that carry real values
#                 for k, v in kwargs.items():
#                     if v is not None:
#                         self._records[call_id][k] = v
#                 self._save_to_disk()
#             else:
#                 print(f"[Store] update_status: call_id '{call_id}' not in store — skipping.")

#     # ── Read ──────────────────────────────────────────────────────────────────

#     def get_by_id(self, call_id: str) -> Optional[dict]:
#         with self._lock:
#             return self._records.get(call_id)

#     def get_by_job_id(self, job_id: str) -> Optional[dict]:
#         with self._lock:
#             call_id = self._job_index.get(job_id)
#             return self._records.get(call_id) if call_id else None

#     def all_records(self) -> List[dict]:
#         with self._lock:
#             return list(self._records.values())

#     # ── Dashboard Builder ─────────────────────────────────────────────────────

#     def build_dashboard(self, grade_filter: Optional[str] = None) -> DashboardResponse:
#         """
#         Returns metrics + call list.
#         Optional grade_filter: "excellent" | "good" | "average" | "poor"
#         """
#         with self._lock:
#             all_calls = list(self._records.values())

#         completed = [c for c in all_calls if c.get("status") == JobStatus.COMPLETED.value]

#         # ── Metrics (always over all completed calls) ──────────────────────────
#         scores = [c["total_score"] for c in completed if c.get("total_score") is not None]
#         durations = [c.get("duration_seconds", 0) for c in completed]

#         def count_grade(g: str) -> int:
#             return sum(1 for c in completed if c.get("grade") == g)

#         metrics = DashboardMetrics(
#             total_calls=len(all_calls),
#             attended_calls=len(completed),
#             not_attended=len(all_calls) - len(completed),
#             excellent=count_grade(CallGrade.EXCELLENT.value),
#             good=count_grade(CallGrade.GOOD.value),
#             average=count_grade(CallGrade.AVERAGE.value),
#             poor=count_grade(CallGrade.POOR.value),
#             avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
#             avg_duration=round(sum(durations) / len(durations), 1) if durations else 0.0,
#             fatal_calls=sum(
#                 1 for c in completed
#                 if c.get("scorecard") and
#                 any(v == "F" for v in (c["scorecard"].get("fatal_flags") or {}).values())
#             ),
#         )

#         # ── Call list (filtered if grade_filter given) ─────────────────────────
#         filtered = completed if not grade_filter else [
#             c for c in completed if c.get("grade") == grade_filter
#         ]
#         # Also include non-completed if no filter
#         if not grade_filter:
#             filtered = all_calls

#         # Sort: newest first
#         filtered.sort(key=lambda c: c.get("created_at", ""), reverse=True)

#         call_items = [
#             CallListItem(
#                 call_id=c["call_id"],
#                 file_name=c["file_name"],
#                 phone_number=c.get("phone_number"),
#                 agent_id=c.get("agent_id", "UNKNOWN"),
#                 duration_formatted=c.get("duration_formatted", "—"),
#                 created_at=c.get("created_at", ""),
#                 status=c.get("status", JobStatus.PENDING.value),
#                 total_score=c.get("total_score"),
#                 grade=c.get("grade"),
#                 letter_grade=_letter_from_grade(c.get("grade")),
#                 has_fatal=_has_fatal(c),
#                 audio_url=c.get("audio_url", ""),
#             )
#             for c in filtered
#         ]

#         return DashboardResponse(metrics=metrics, calls=call_items)

#     def build_leaderboard(self) -> List[dict]:
#         """Agent → avg score leaderboard (mirrors your original get_summary())."""
#         with self._lock:
#             all_calls = list(self._records.values())

#         agent_data: Dict[str, dict] = {}
#         for c in all_calls:
#             if c.get("status") != JobStatus.COMPLETED.value:
#                 continue
#             agent = c.get("agent_id", "UNKNOWN")
#             score = c.get("total_score")
#             if score is None:
#                 continue
#             if agent not in agent_data:
#                 agent_data[agent] = {"scores": [], "calls": 0}
#             agent_data[agent]["scores"].append(score)
#             agent_data[agent]["calls"] += 1

#         leaderboard = []
#         for agent, data in agent_data.items():
#             avg = round(sum(data["scores"]) / len(data["scores"]), 2)
#             from services.parser import _grade_from_score
#             grade, letter = _grade_from_score(int(avg))
#             leaderboard.append({
#                 "agent_id": agent,
#                 "total_calls": data["calls"],
#                 "avg_score": avg,
#                 "grade": grade.value,
#                 "letter_grade": letter,
#             })

#         leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
#         return leaderboard


# # ── Helpers ────────────────────────────────────────────────────────────────────

# def _letter_from_grade(grade: Optional[str]) -> Optional[str]:
#     return {"excellent": "A", "good": "B", "average": "C", "poor": "D"}.get(grade or "")


# def _has_fatal(call_dict: dict) -> bool:
#     sc = call_dict.get("scorecard")
#     if not sc:
#         return False
#     flags = sc.get("fatal_flags", {})
#     return any(v == "F" for v in flags.values())


# # ── Singleton ─────────────────────────────────────────────────────────────────
# _store_instance: Optional[CallStore] = None

# def get_store() -> CallStore:
#     global _store_instance
#     if _store_instance is None:
#         _store_instance = CallStore()
#     return _store_instance




# """
# services/call_store.py
# In-memory + JSON-file persistence for all processed CallRecords.
# Thread-safe with a simple RLock for concurrent FastAPI requests.
# """

# import json
# import threading
# from pathlib import Path
# from typing import Dict, List, Optional
# from datetime import datetime

# from models.schemas import (
#     CallRecord, CallListItem, DashboardMetrics,
#     DashboardResponse, JobStatus, CallGrade,
# )


# STORE_FILE = Path("outputs/call_store.json")


# def _ensure_store_dir():
#     STORE_FILE.parent.mkdir(exist_ok=True)


# class CallStore:
#     """
#     Central registry of all processed calls.
#     Persists to outputs/call_store.json so data survives restarts.
#     """

#     def __init__(self):
#         self._lock = threading.RLock()
#         self._records: Dict[str, dict] = {}    # call_id → raw dict
#         self._job_index: Dict[str, str] = {}   # job_id → call_id
#         _ensure_store_dir()
#         self._load_from_disk()

#     # ── Persistence ───────────────────────────────────────────────────────────

#     def _load_from_disk(self):
#         if STORE_FILE.exists():
#             try:
#                 data = json.loads(STORE_FILE.read_text())
#                 self._records = data.get("records", {})
#                 self._job_index = data.get("job_index", {})
#                 print(f"[Store] Loaded {len(self._records)} call(s) from disk.")
#             except Exception as e:
#                 print(f"[Store] Could not load from disk: {e}")

#     def _save_to_disk(self):
#         try:
#             STORE_FILE.write_text(json.dumps({
#                 "records": self._records,
#                 "job_index": self._job_index,
#             }, indent=2, default=str))
#         except Exception as e:
#             print(f"[Store] Could not save to disk: {e}")

#     # ── Write ─────────────────────────────────────────────────────────────────

#     def upsert(self, call: CallRecord):
#         """Insert or update a call record."""
#         with self._lock:
#             self._records[call.call_id] = call.dict()
#             self._job_index[call.job_id] = call.call_id
#             self._save_to_disk()

#     def update_status(self, call_id: str, status: JobStatus, **kwargs):
#         with self._lock:
#             if call_id in self._records:
#                 self._records[call_id]["status"] = status.value
#                 self._records[call_id].update(kwargs)
#                 self._save_to_disk()

#     # ── Read ──────────────────────────────────────────────────────────────────

#     def get_by_id(self, call_id: str) -> Optional[dict]:
#         with self._lock:
#             return self._records.get(call_id)

#     def get_by_job_id(self, job_id: str) -> Optional[dict]:
#         with self._lock:
#             call_id = self._job_index.get(job_id)
#             return self._records.get(call_id) if call_id else None

#     def all_records(self) -> List[dict]:
#         with self._lock:
#             return list(self._records.values())

#     # ── Dashboard Builder ─────────────────────────────────────────────────────

#     def build_dashboard(self, grade_filter: Optional[str] = None) -> DashboardResponse:
#         """
#         Returns metrics + call list.
#         Optional grade_filter: "excellent" | "good" | "average" | "poor"
#         """
#         with self._lock:
#             all_calls = list(self._records.values())

#         completed = [c for c in all_calls if c.get("status") == JobStatus.COMPLETED.value]

#         # ── Metrics (always over all completed calls) ──────────────────────────
#         scores = [c["total_score"] for c in completed if c.get("total_score") is not None]
#         durations = [c.get("duration_seconds", 0) for c in completed]

#         def count_grade(g: str) -> int:
#             return sum(1 for c in completed if c.get("grade") == g)

#         metrics = DashboardMetrics(
#             total_calls=len(all_calls),
#             attended_calls=len(completed),
#             not_attended=len(all_calls) - len(completed),
#             excellent=count_grade(CallGrade.EXCELLENT.value),
#             good=count_grade(CallGrade.GOOD.value),
#             average=count_grade(CallGrade.AVERAGE.value),
#             poor=count_grade(CallGrade.POOR.value),
#             avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
#             avg_duration=round(sum(durations) / len(durations), 1) if durations else 0.0,
#             fatal_calls=sum(
#                 1 for c in completed
#                 if c.get("scorecard") and
#                 any(v == "F" for v in (c["scorecard"].get("fatal_flags") or {}).values())
#             ),
#         )

#         # ── Call list (filtered if grade_filter given) ─────────────────────────
#         filtered = completed if not grade_filter else [
#             c for c in completed if c.get("grade") == grade_filter
#         ]
#         # Also include non-completed if no filter
#         if not grade_filter:
#             filtered = all_calls

#         # Sort: newest first
#         filtered.sort(key=lambda c: c.get("created_at", ""), reverse=True)

#         call_items = [
#             CallListItem(
#                 call_id=c["call_id"],
#                 file_name=c["file_name"],
#                 phone_number=c.get("phone_number"),
#                 agent_id=c.get("agent_id", "UNKNOWN"),
#                 duration_formatted=c.get("duration_formatted", "—"),
#                 created_at=c.get("created_at", ""),
#                 status=c.get("status", JobStatus.PENDING.value),
#                 total_score=c.get("total_score"),
#                 grade=c.get("grade"),
#                 letter_grade=_letter_from_grade(c.get("grade")),
#                 has_fatal=_has_fatal(c),
#                 audio_url=c.get("audio_url", ""),
#             )
#             for c in filtered
#         ]

#         return DashboardResponse(metrics=metrics, calls=call_items)

#     def build_leaderboard(self) -> List[dict]:
#         """Agent → avg score leaderboard (mirrors your original get_summary())."""
#         with self._lock:
#             all_calls = list(self._records.values())

#         agent_data: Dict[str, dict] = {}
#         for c in all_calls:
#             if c.get("status") != JobStatus.COMPLETED.value:
#                 continue
#             agent = c.get("agent_id", "UNKNOWN")
#             score = c.get("total_score")
#             if score is None:
#                 continue
#             if agent not in agent_data:
#                 agent_data[agent] = {"scores": [], "calls": 0}
#             agent_data[agent]["scores"].append(score)
#             agent_data[agent]["calls"] += 1

#         leaderboard = []
#         for agent, data in agent_data.items():
#             avg = round(sum(data["scores"]) / len(data["scores"]), 2)
#             from parser import _grade_from_score
#             grade, letter = _grade_from_score(int(avg))
#             leaderboard.append({
#                 "agent_id": agent,
#                 "total_calls": data["calls"],
#                 "avg_score": avg,
#                 "grade": grade.value,
#                 "letter_grade": letter,
#             })

#         leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
#         return leaderboard


# # ── Helpers ────────────────────────────────────────────────────────────────────

# def _letter_from_grade(grade: Optional[str]) -> Optional[str]:
#     return {"excellent": "A", "good": "B", "average": "C", "poor": "D"}.get(grade or "")


# def _has_fatal(call_dict: dict) -> bool:
#     sc = call_dict.get("scorecard")
#     if not sc:
#         return False
#     flags = sc.get("fatal_flags", {})
#     return any(v == "F" for v in flags.values())


# # ── Singleton ─────────────────────────────────────────────────────────────────
# _store_instance: Optional[CallStore] = None

# def get_store() -> CallStore:
#     global _store_instance
#     if _store_instance is None:
#         _store_instance = CallStore()
#     return _store_instance
