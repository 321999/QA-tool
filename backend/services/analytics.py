"""
services/analytics.py
UPGRADED CallAnalytics class.

This is a refactored, production-ready version of your original code.
All original logic is preserved; new structured JSON layer is added on top.
"""

"""
services/analytics.py
UPGRADED CallAnalytics class.

This is a refactored, production-ready version of your original code.
All original logic is preserved; new structured JSON layer is added on top.
"""

import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from models.schemas import (
    CallRecord, TranscriptEntry, SpeakerStats,
    JobStatus, CallGrade,
)
from services.transcription import (
    SarvamTranscriptionService,
    MockTranscriptionService,
    seconds_to_mmss,
    _extract_phone_from_filename,
    _extract_call_id_from_filename,
)
from services.llm_analysis import LLMAnalysisService, MockLLMAnalysisService
from services.parser import flag_transcript_segments
from services.call_store import get_store


OUTPUT_DIR = "outputs"


def _duration_from_entries(entries: list) -> float:
    if not entries:
        return 0.0
    return max(e.get("end_time", 0) for e in entries)


def _word_count(entries: list, speaker: str) -> int:
    total = 0
    for e in entries:
        if e.get("speaker") == speaker:
            total += len(e.get("text", "").split())
    return total


class CallAnalytics:
    """
    Upgraded version of your original CallAnalytics.

    Changes:
    - process_audio_files() now returns structured CallRecord objects
    - analyze_transcription() now returns QAScorecard JSON
    - All results stored in CallStore (memory + disk)
    - get_summary() still prints the leaderboard (backwards compat)
    - New: build_dashboard_data() for frontend
    """

    def __init__(self, client=None, use_mock: bool = False):
        self.use_mock = use_mock or client is None
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)

        if self.use_mock:
            self.transcription_svc = MockTranscriptionService(OUTPUT_DIR)
            self.llm_svc = MockLLMAnalysisService(OUTPUT_DIR)
            print("[CallAnalytics] Running in MOCK mode (no API keys required).")
        else:
            self.transcription_svc = SarvamTranscriptionService(client, OUTPUT_DIR)
            self.llm_svc = LLMAnalysisService(client, OUTPUT_DIR)

        self.store = get_store()

    # ─── Main Entry Point ──────────────────────────────────────────────────────

    def process_audio_files(self, audio_paths: List[str]) -> List[CallRecord]:
        """
        Full pipeline: audio → transcript → QA scorecard → stored CallRecord.
        Logs every step to console.
        """
        print(f"\n[Analytics] === PIPELINE START === {len(audio_paths)} file(s)")
        print(f"[Analytics] Mode: {'MOCK' if self.use_mock else 'LIVE (Sarvam AI)'}")

        # ── Step 1: Transcribe ────────────────────────────────────────────────
        print(f"[Analytics] Step 1/5: Transcribing audio...")
        transcription_results, job_id = self.transcription_svc.transcribe_files(audio_paths)
        print(f"[Analytics] Step 1/5: ✓ Got {len(transcription_results)} transcription(s) — job_id={job_id}")

        records: List[CallRecord] = []

        for file_path_str in audio_paths:
            file_path = Path(file_path_str)
            stem = file_path.stem

            trans_data = transcription_results.get(stem)
            if not trans_data:
                print(f"[Analytics] No transcription found for {stem}, skipping.")
                continue

            entries_raw = trans_data["entries"]
            speaker_times = trans_data["speaker_times"]
            speaker_labels = trans_data["speaker_labels"]
            total_duration = trans_data["total_duration"]

            # ── Step 2: Build conversation text ────────────────────────────
            print(f"[Analytics] Step 2/5: Building conversation text for {stem}...")
            conversation_text = "\n".join(
                f"{e['speaker']}: {e['text']}" for e in entries_raw
            )
            print(f"[Analytics]           {len(entries_raw)} entries, {len(conversation_text)} chars")

            job_dir = self.output_dir / f"transcriptions_{job_id}"
            job_dir.mkdir(parents=True, exist_ok=True)
            txt_path = job_dir / f"{stem}_conversation.txt"
            txt_path.write_text(conversation_text)
            analysis_path = job_dir / f"{stem}_analysis.txt"

            # ── Step 3: LLM QA Analysis ───────────────────────────────────────
            print(f"[Analytics] Step 3/5: Running LLM QA analysis...")
            raw_text, scorecard = self.llm_svc.analyze_transcription(
                conversation_text,
                save_path=analysis_path,
            )

            # ── Step 4: Flag transcript segments based on QA failures ─────────
            print(f"[Analytics] Step 3/5: ✓ Score={scorecard.total_score} Grade={scorecard.grade}")
            print(f"[Analytics] Step 4/5: Flagging transcript segments...")
            flagged_entries = flag_transcript_segments(entries_raw, scorecard)

            # ── Step 5: Build TranscriptEntry objects ─────────────────────────
            transcript_objs = [
                TranscriptEntry(**e) for e in flagged_entries
            ]

            # ── Step 6: Build SpeakerStats ─────────────────────────────────
            agent_id = max(speaker_times, key=speaker_times.get) if speaker_times else "UNKNOWN"

            speaker_stats_list = []
            for spk_id, talk_time in speaker_times.items():
                speaker_stats_list.append(SpeakerStats(
                    speaker_id=spk_id,
                    label=speaker_labels.get(spk_id, "Unknown"),
                    total_talk_time=round(talk_time, 2),
                    talk_time_formatted=seconds_to_mmss(talk_time),
                    word_count=_word_count(entries_raw, spk_id),
                ))

            # ── Step 7: Build CallRecord ───────────────────────────────────────
            call_id = _extract_call_id_from_filename(file_path.name)
            print("///////////////////////////calll id///////////////////////////////")
            print(call_id)
            phone = _extract_phone_from_filename(file_path.name)
            flagged_indices = [i for i, e in enumerate(flagged_entries) if e.get("is_flagged")]

            record = CallRecord(
                call_id=call_id,
                file_name=file_path.name,
                audio_url=f"/api/audio/{call_id}",
                job_id=job_id,
                status=JobStatus.COMPLETED,
                created_at=datetime.now().isoformat(),
                duration_seconds=round(total_duration, 2),
                duration_formatted=seconds_to_mmss(total_duration),
                agent_id=agent_id,
                phone_number=phone,
                transcript=transcript_objs,
                speaker_stats=speaker_stats_list,
                scorecard=scorecard,
                grade=scorecard.grade,
                total_score=scorecard.total_score,
                flagged_segments=flagged_indices,
            )

            # ── Step 8: Persist ────────────────────────────────────────────────
            print(f"[Analytics] Step 5/5: Saving record to store...")
            self.store.upsert(record)
            records.append(record)
            print(f"[Analytics] ✓ COMPLETE: {call_id}")
            print(f"[Analytics]   Score={scorecard.total_score}/100  Grade={scorecard.grade.value}")
            print(f"[Analytics]   Transcript={len(transcript_objs)} lines  Duration={record.duration_formatted}")

        print(f"[Analytics] === PIPELINE COMPLETE === {len(records)}/{len(audio_paths)} files processed")
        return records

    def build_dashboard_data(self, grade_filter: Optional[str] = None) -> dict:
        """
        Returns full dashboard JSON for the frontend.
        Optional grade_filter: "excellent" | "good" | "average" | "poor"
        """
        return self.store.build_dashboard(grade_filter).model_dump()

    def get_call(self, call_id: str) -> Optional[dict]:
        """Returns full call detail dict for the frontend."""
        return self.store.get_by_id(call_id)

    def get_leaderboard(self) -> List[dict]:
        return self.store.build_leaderboard()

    def get_summary(self):
        """
        Preserved from your original code.
        Prints the agent leaderboard to stdout.
        """
        print("\nAGENT LEADERBOARD")
        print("-" * 40)
        for row in self.get_leaderboard():
            print(
                row["agent_id"],
                "| Calls:", row["total_calls"],
                "| Avg Score:", row["avg_score"],
                "| Grade:", row["letter_grade"]
            )


# import re
# import uuid
# from pathlib import Path
# from datetime import datetime
# from typing import List, Optional, Dict

# from models.schemas import (
#     CallRecord, TranscriptEntry, SpeakerStats,
#     JobStatus, CallGrade,
# )
# from services.transcription import (
#     SarvamTranscriptionService,
#     MockTranscriptionService,
#     seconds_to_mmss,
#     _extract_phone_from_filename,
#     _extract_call_id_from_filename,
# )
# from services.llm_analysis import LLMAnalysisService, MockLLMAnalysisService
# from services.parser import flag_transcript_segments
# from services.call_store import get_store


# OUTPUT_DIR = "outputs"


# def _duration_from_entries(entries: list) -> float:
#     if not entries:
#         return 0.0
#     return max(e.get("end_time", 0) for e in entries)


# def _word_count(entries: list, speaker: str) -> int:
#     total = 0
#     for e in entries:
#         if e.get("speaker") == speaker:
#             total += len(e.get("text", "").split())
#     return total


# class CallAnalytics:
#     """
#     Upgraded version of your original CallAnalytics.

#     Changes:
#     - process_audio_files() now returns structured CallRecord objects
#     - analyze_transcription() now returns QAScorecard JSON
#     - All results stored in CallStore (memory + disk)
#     - get_summary() still prints the leaderboard (backwards compat)
#     - New: build_dashboard_data() for frontend
#     """

#     def __init__(self, client=None, use_mock: bool = False):
#         self.use_mock = use_mock or client is None
#         self.output_dir = Path(OUTPUT_DIR)
#         self.output_dir.mkdir(exist_ok=True)

#         if self.use_mock:
#             self.transcription_svc = MockTranscriptionService(OUTPUT_DIR)
#             self.llm_svc = MockLLMAnalysisService(OUTPUT_DIR)
#             print("[CallAnalytics] Running in MOCK mode (no API keys required).")
#         else:
#             self.transcription_svc = SarvamTranscriptionService(client, OUTPUT_DIR)
#             self.llm_svc = LLMAnalysisService(client, OUTPUT_DIR)

#         self.store = get_store()

#     # ─── Main Entry Point ──────────────────────────────────────────────────────

#     def process_audio_files(self, audio_paths: List[str]) -> List[CallRecord]:
#         """
#         Full pipeline: audio → transcript → QA scorecard → stored CallRecord.
#         Returns list of CallRecord objects (one per audio file).
#         """
#         print(f"[Analytics] Processing {len(audio_paths)} file(s)...")

#         # ── Step 1: Transcribe ────────────────────────────────────────────────
#         transcription_results, job_id = self.transcription_svc.transcribe_files(audio_paths)

#         records: List[CallRecord] = []

#         for file_path_str in audio_paths:
#             file_path = Path(file_path_str)
#             stem = file_path.stem

#             trans_data = transcription_results.get(stem)
#             if not trans_data:
#                 print(f"[Analytics] No transcription found for {stem}, skipping.")
#                 continue

#             entries_raw = trans_data["entries"]
#             speaker_times = trans_data["speaker_times"]
#             speaker_labels = trans_data["speaker_labels"]
#             total_duration = trans_data["total_duration"]

#             # ── Step 2: Build conversation text (same as original) ───────────
#             conversation_text = "\n".join(
#                 f"{e['speaker']}: {e['text']}" for e in entries_raw
#             )

#             job_dir = self.output_dir / f"transcriptions_{job_id}"
#             job_dir.mkdir(parents=True, exist_ok=True)
#             txt_path = job_dir / f"{stem}_conversation.txt"
#             txt_path.write_text(conversation_text)
#             analysis_path = job_dir / f"{stem}_analysis.txt"

#             # ── Step 3: LLM QA Analysis ───────────────────────────────────────
#             raw_text, scorecard = self.llm_svc.analyze_transcription(
#                 conversation_text,
#                 save_path=analysis_path,
#             )

#             # ── Step 4: Flag transcript segments based on QA failures ─────────
#             flagged_entries = flag_transcript_segments(entries_raw, scorecard)

#             # ── Step 5: Build TranscriptEntry objects ─────────────────────────
#             transcript_objs = [
#                 TranscriptEntry(**e) for e in flagged_entries
#             ]

#             # ── Step 6: Build SpeakerStats ─────────────────────────────────
#             agent_id = max(speaker_times, key=speaker_times.get) if speaker_times else "UNKNOWN"

#             speaker_stats_list = []
#             for spk_id, talk_time in speaker_times.items():
#                 speaker_stats_list.append(SpeakerStats(
#                     speaker_id=spk_id,
#                     label=speaker_labels.get(spk_id, "Unknown"),
#                     total_talk_time=round(talk_time, 2),
#                     talk_time_formatted=seconds_to_mmss(talk_time),
#                     word_count=_word_count(entries_raw, spk_id),
#                 ))

#             # ── Step 7: Build CallRecord ───────────────────────────────────────
#             call_id = _extract_call_id_from_filename(file_path.name)
#             phone = _extract_phone_from_filename(file_path.name)
#             flagged_indices = [i for i, e in enumerate(flagged_entries) if e.get("is_flagged")]

#             record = CallRecord(
#                 call_id=call_id,
#                 file_name=file_path.name,
#                 audio_url=f"/audio/{call_id}",
#                 job_id=job_id,
#                 status=JobStatus.COMPLETED,
#                 created_at=datetime.now().isoformat(),
#                 duration_seconds=round(total_duration, 2),
#                 duration_formatted=seconds_to_mmss(total_duration),
#                 agent_id=agent_id,
#                 phone_number=phone,
#                 transcript=transcript_objs,
#                 speaker_stats=speaker_stats_list,
#                 scorecard=scorecard,
#                 grade=scorecard.grade,
#                 total_score=scorecard.total_score,
#                 flagged_segments=flagged_indices,
#             )

#             # ── Step 8: Persist ────────────────────────────────────────────────
#             self.store.upsert(record)
#             records.append(record)
#             print(f"[Analytics] ✓ {call_id} — Score: {scorecard.total_score}/100 ({scorecard.grade.value})")

#         return records

#     def build_dashboard_data(self, grade_filter: Optional[str] = None) -> dict:
#         """
#         Returns full dashboard JSON for the frontend.
#         Optional grade_filter: "excellent" | "good" | "average" | "poor"
#         """
#         return self.store.build_dashboard(grade_filter).model_dump()

#     def get_call(self, call_id: str) -> Optional[dict]:
#         """Returns full call detail dict for the frontend."""
#         return self.store.get_by_id(call_id)

#     def get_leaderboard(self) -> List[dict]:
#         return self.store.build_leaderboard()

#     def get_summary(self):
#         """
#         Preserved from your original code.
#         Prints the agent leaderboard to stdout.
#         """
#         print("\nAGENT LEADERBOARD")
#         print("-" * 40)
#         for row in self.get_leaderboard():
#             print(
#                 row["agent_id"],
#                 "| Calls:", row["total_calls"],
#                 "| Avg Score:", row["avg_score"],
#                 "| Grade:", row["letter_grade"]
#             )
            

# *******************************************************************************************
# """
# services/analytics.py
# UPGRADED CallAnalytics class.

# This is a refactored, production-ready version of your original code.
# All original logic is preserved; new structured JSON layer is added on top.
# """

# import re
# import uuid
# from pathlib import Path
# from datetime import datetime
# from typing import List, Optional, Dict

# from models.schemas import (
#     CallRecord, TranscriptEntry, SpeakerStats,
#     JobStatus, CallGrade,
# )
# from services.transcription import (
#     SarvamTranscriptionService,
#     MockTranscriptionService,
#     seconds_to_mmss,
#     _extract_phone_from_filename,
#     _extract_call_id_from_filename,
# )
# from services.llm_analysis import LLMAnalysisService, MockLLMAnalysisService
# from services.parser import flag_transcript_segments
# from services.call_store import get_store


# OUTPUT_DIR = "outputs"


# def _duration_from_entries(entries: list) -> float:
#     if not entries:
#         return 0.0
#     return max(e.get("end_time", 0) for e in entries)


# def _word_count(entries: list, speaker: str) -> int:
#     total = 0
#     for e in entries:
#         if e.get("speaker") == speaker:
#             total += len(e.get("text", "").split())
#     return total


# class CallAnalytics:
#     """
#     Upgraded version of your original CallAnalytics.

#     Changes:
#     - process_audio_files() now returns structured CallRecord objects
#     - analyze_transcription() now returns QAScorecard JSON
#     - All results stored in CallStore (memory + disk)
#     - get_summary() still prints the leaderboard (backwards compat)
#     - New: build_dashboard_data() for frontend
#     """

#     def __init__(self, client=None, use_mock: bool = False):
#         self.use_mock = use_mock or client is None
#         self.output_dir = Path(OUTPUT_DIR)
#         self.output_dir.mkdir(exist_ok=True)

#         if self.use_mock:
#             self.transcription_svc = MockTranscriptionService(OUTPUT_DIR)
#             self.llm_svc = MockLLMAnalysisService(OUTPUT_DIR)
#             print("[CallAnalytics] Running in MOCK mode (no API keys required).")
#         else:
#             self.transcription_svc = SarvamTranscriptionService(client, OUTPUT_DIR)
#             self.llm_svc = LLMAnalysisService(client, OUTPUT_DIR)

#         self.store = get_store()

#     # ─── Main Entry Point ──────────────────────────────────────────────────────

#     def process_audio_files(self, audio_paths: List[str]) -> List[CallRecord]:
#         """
#         Full pipeline: audio → transcript → QA scorecard → stored CallRecord.
#         Returns list of CallRecord objects (one per audio file).
#         """
#         print(f"[Analytics] Processing {len(audio_paths)} file(s)...")

#         # ── Step 1: Transcribe ────────────────────────────────────────────────
#         transcription_results, job_id = self.transcription_svc.transcribe_files(audio_paths)

#         records: List[CallRecord] = []

#         for file_path_str in audio_paths:
#             file_path = Path(file_path_str)
#             stem = file_path.stem

#             trans_data = transcription_results.get(stem)
#             if not trans_data:
#                 print(f"[Analytics] No transcription found for {stem}, skipping.")
#                 continue

#             entries_raw = trans_data["entries"]
#             speaker_times = trans_data["speaker_times"]
#             speaker_labels = trans_data["speaker_labels"]
#             total_duration = trans_data["total_duration"]

#             # ── Step 2: Build conversation text (same as original) ───────────
#             conversation_text = "\n".join(
#                 f"{e['speaker']}: {e['text']}" for e in entries_raw
#             )

#             job_dir = self.output_dir / f"transcriptions_{job_id}"
#             job_dir.mkdir(parents=True, exist_ok=True)
#             txt_path = job_dir / f"{stem}_conversation.txt"
#             txt_path.write_text(conversation_text)
#             analysis_path = job_dir / f"{stem}_analysis.txt"

#             # ── Step 3: LLM QA Analysis ───────────────────────────────────────
#             raw_text, scorecard = self.llm_svc.analyze_transcription(
#                 conversation_text,
#                 save_path=analysis_path,
#             )

#             # ── Step 4: Flag transcript segments based on QA failures ─────────
#             flagged_entries = flag_transcript_segments(entries_raw, scorecard)

#             # ── Step 5: Build TranscriptEntry objects ─────────────────────────
#             transcript_objs = [
#                 TranscriptEntry(**e) for e in flagged_entries
#             ]

#             # ── Step 6: Build SpeakerStats ─────────────────────────────────
#             agent_id = max(speaker_times, key=speaker_times.get) if speaker_times else "UNKNOWN"

#             speaker_stats_list = []
#             for spk_id, talk_time in speaker_times.items():
#                 speaker_stats_list.append(SpeakerStats(
#                     speaker_id=spk_id,
#                     label=speaker_labels.get(spk_id, "Unknown"),
#                     total_talk_time=round(talk_time, 2),
#                     talk_time_formatted=seconds_to_mmss(talk_time),
#                     word_count=_word_count(entries_raw, spk_id),
#                 ))

#             # ── Step 7: Build CallRecord ───────────────────────────────────────
#             call_id = _extract_call_id_from_filename(file_path.name)
#             phone = _extract_phone_from_filename(file_path.name)
#             flagged_indices = [i for i, e in enumerate(flagged_entries) if e.get("is_flagged")]

#             record = CallRecord(
#                 call_id=call_id,
#                 file_name=file_path.name,
#                 audio_url=f"/audio/{call_id}",
#                 job_id=job_id,
#                 status=JobStatus.COMPLETED,
#                 created_at=datetime.now().isoformat(),
#                 duration_seconds=round(total_duration, 2),
#                 duration_formatted=seconds_to_mmss(total_duration),
#                 agent_id=agent_id,
#                 phone_number=phone,
#                 transcript=transcript_objs,
#                 speaker_stats=speaker_stats_list,
#                 scorecard=scorecard,
#                 grade=scorecard.grade,
#                 total_score=scorecard.total_score,
#                 flagged_segments=flagged_indices,
#             )

#             # ── Step 8: Persist ────────────────────────────────────────────────
#             self.store.upsert(record)
#             records.append(record)
#             print(f"[Analytics] ✓ {call_id} — Score: {scorecard.total_score}/100 ({scorecard.grade.value})")

#         return records

#     def build_dashboard_data(self, grade_filter: Optional[str] = None) -> dict:
#         """
#         Returns full dashboard JSON for the frontend.
#         Optional grade_filter: "excellent" | "good" | "average" | "poor"
#         """
#         return self.store.build_dashboard(grade_filter).dict()

#     def get_call(self, call_id: str) -> Optional[dict]:
#         """Returns full call detail dict for the frontend."""
#         return self.store.get_by_id(call_id)

#     def get_leaderboard(self) -> List[dict]:
#         return self.store.build_leaderboard()

#     def get_summary(self):
#         """
#         Preserved from your original code.
#         Prints the agent leaderboard to stdout.
#         """
#         print("\nAGENT LEADERBOARD")
#         print("-" * 40)
#         for row in self.get_leaderboard():
#             print(
#                 row["agent_id"],
#                 "| Calls:", row["total_calls"],
#                 "| Avg Score:", row["avg_score"],
#                 "| Grade:", row["letter_grade"]
#             )
