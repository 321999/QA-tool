"""
Pydantic models for CallIQ Analytics API.
All API responses and internal data structures are typed here.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class CallGrade(str, Enum):
    EXCELLENT = "excellent"   # >= 90
    GOOD      = "good"        # >= 75
    AVERAGE   = "average"     # >= 60
    POOR      = "poor"        # < 60


class JobStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class FatalFlag(str, Enum):
    F  = "F"   # Fatal — call disqualified
    NF = "NF"  # Not Fatal


# ─── Transcript ───────────────────────────────────────────────────────────────

class TranscriptEntry(BaseModel):
    speaker: str                      # e.g. "SPEAKER_00"
    speaker_label: str                # "Agent" | "Customer"
    start_time: float
    end_time: float
    text: str
    is_flagged: bool = False          # True if this segment has quality issues
    flag_reason: Optional[str] = None # e.g. "Missed greeting", "Rude tone"


# ─── QA Scoring ───────────────────────────────────────────────────────────────

class ScoreParameter(BaseModel):
    parameter: str
    score: int
    max_score: int
    percentage: float
    reason: str
    is_critical_miss: bool = False   # True if score == 0 on a high-weight param


class QASection(BaseModel):
    section_name: str                 # OPENING | SALES | SOFT_SKILLS | CLOSING
    parameters: List[ScoreParameter]
    section_score: int
    section_max: int
    section_percentage: float


class FatalFlags(BaseModel):
    right_party_confirmation: FatalFlag = FatalFlag.NF
    rude_behaviour: FatalFlag = FatalFlag.NF
    miss_sell: FatalFlag = FatalFlag.NF
    disposition: FatalFlag = FatalFlag.NF

    def has_fatal(self) -> bool:
        return any(v == FatalFlag.F for v in self.model_dump().values())

    def fatal_list(self) -> List[str]:
        return [k for k, v in self.model_dump().items() if v == FatalFlag.F]


class QAScorecard(BaseModel):
    total_score: int
    total_max: int = 100
    percentage: float
    grade: CallGrade
    letter_grade: str                 # A / B / C / D
    sections: List[QASection]
    fatal_flags: FatalFlags
    improvement_areas: List[str]     # Top 3 areas needing improvement
    strengths: List[str]             # Top 3 things done well
    summary_note: str                # One-line LLM-generated feedback


# ─── Call Record ──────────────────────────────────────────────────────────────

class SpeakerStats(BaseModel):
    speaker_id: str
    label: str                        # Agent | Customer
    total_talk_time: float            # seconds
    talk_time_formatted: str          # "3m42s"
    word_count: int
    interruptions: int = 0


class CallRecord(BaseModel):
    call_id: str                      # e.g. "4174_09890382855_07-Mar-26"
    file_name: str
    audio_url: str                    # served via /audio/{call_id}
    job_id: str
    status: JobStatus
    created_at: str
    duration_seconds: float
    duration_formatted: str
    agent_id: str                     # dominant speaker ID
    phone_number: Optional[str] = None
    transcript: List[TranscriptEntry]
    speaker_stats: List[SpeakerStats]
    scorecard: Optional[QAScorecard] = None
    grade: Optional[CallGrade] = None
    total_score: Optional[int] = None
    flagged_segments: List[int] = []  # indices of flagged transcript entries


# ─── Dashboard Summary ────────────────────────────────────────────────────────

class DashboardMetrics(BaseModel):
    total_calls: int
    attended_calls: int
    not_attended: int
    excellent: int                    # score >= 90
    good: int                         # score 75-89
    average: int                      # score 60-74
    poor: int                         # score < 60
    avg_score: float
    avg_duration: float
    fatal_calls: int                  # calls with any fatal flag


class CallListItem(BaseModel):
    """Lightweight call summary for the sidebar list."""
    call_id: str
    file_name: str
    phone_number: Optional[str]
    agent_id: str
    duration_formatted: str
    created_at: str
    status: JobStatus
    total_score: Optional[int]
    grade: Optional[CallGrade]
    letter_grade: Optional[str]
    has_fatal: bool
    audio_url: str


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    calls: List[CallListItem]


# ─── Upload Response ──────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    job_id: str
    files_queued: int
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_message: str
    call_id: Optional[str] = None

# """
# Pydantic models for CallIQ Analytics API.
# All API responses and internal data structures are typed here.
# """

# from pydantic import BaseModel, Field
# from typing import List, Dict, Optional, Literal
# from enum import Enum


# # ─── Enums ────────────────────────────────────────────────────────────────────

# class CallGrade(str, Enum):
#     EXCELLENT = "excellent"   # >= 90
#     GOOD      = "good"        # >= 75
#     AVERAGE   = "average"     # >= 60
#     POOR      = "poor"        # < 60


# class JobStatus(str, Enum):
#     PENDING    = "pending"
#     PROCESSING = "processing"
#     COMPLETED  = "completed"
#     FAILED     = "failed"


# class FatalFlag(str, Enum):
#     F  = "F"   # Fatal — call disqualified
#     NF = "NF"  # Not Fatal


# # ─── Transcript ───────────────────────────────────────────────────────────────

# class TranscriptEntry(BaseModel):
#     speaker: str                      # e.g. "SPEAKER_00"
#     speaker_label: str                # "Agent" | "Customer"
#     start_time: float
#     end_time: float
#     text: str
#     is_flagged: bool = False          # True if this segment has quality issues
#     flag_reason: Optional[str] = None # e.g. "Missed greeting", "Rude tone"


# # ─── QA Scoring ───────────────────────────────────────────────────────────────

# class ScoreParameter(BaseModel):
#     parameter: str
#     score: int
#     max_score: int
#     percentage: float
#     reason: str
#     is_critical_miss: bool = False   # True if score == 0 on a high-weight param


# class QASection(BaseModel):
#     section_name: str                 # OPENING | SALES | SOFT_SKILLS | CLOSING
#     parameters: List[ScoreParameter]
#     section_score: int
#     section_max: int
#     section_percentage: float


# class FatalFlags(BaseModel):
#     right_party_confirmation: FatalFlag = FatalFlag.NF
#     rude_behaviour: FatalFlag = FatalFlag.NF
#     miss_sell: FatalFlag = FatalFlag.NF
#     disposition: FatalFlag = FatalFlag.NF

#     def has_fatal(self) -> bool:
#         return any(v == FatalFlag.F for v in self.dict().values())

#     def fatal_list(self) -> List[str]:
#         return [k for k, v in self.dict().items() if v == FatalFlag.F]


# class QAScorecard(BaseModel):
#     total_score: int
#     total_max: int = 100
#     percentage: float
#     grade: CallGrade
#     letter_grade: str                 # A / B / C / D
#     sections: List[QASection]
#     fatal_flags: FatalFlags
#     improvement_areas: List[str]     # Top 3 areas needing improvement
#     strengths: List[str]             # Top 3 things done well
#     summary_note: str                # One-line LLM-generated feedback


# # ─── Call Record ──────────────────────────────────────────────────────────────

# class SpeakerStats(BaseModel):
#     speaker_id: str
#     label: str                        # Agent | Customer
#     total_talk_time: float            # seconds
#     talk_time_formatted: str          # "3m42s"
#     word_count: int
#     interruptions: int = 0


# class CallRecord(BaseModel):
#     call_id: str                      # e.g. "4174_09890382855_07-Mar-26"
#     file_name: str
#     audio_url: str                    # served via /audio/{call_id}
#     job_id: str
#     status: JobStatus
#     created_at: str
#     duration_seconds: float
#     duration_formatted: str
#     agent_id: str                     # dominant speaker ID
#     phone_number: Optional[str] = None
#     transcript: List[TranscriptEntry]
#     speaker_stats: List[SpeakerStats]
#     scorecard: Optional[QAScorecard] = None
#     grade: Optional[CallGrade] = None
#     total_score: Optional[int] = None
#     flagged_segments: List[int] = []  # indices of flagged transcript entries


# # ─── Dashboard Summary ────────────────────────────────────────────────────────

# class DashboardMetrics(BaseModel):
#     total_calls: int
#     attended_calls: int
#     not_attended: int
#     excellent: int                    # score >= 90
#     good: int                         # score 75-89
#     average: int                      # score 60-74
#     poor: int                         # score < 60
#     avg_score: float
#     avg_duration: float
#     fatal_calls: int                  # calls with any fatal flag


# class CallListItem(BaseModel):
#     """Lightweight call summary for the sidebar list."""
#     call_id: str
#     file_name: str
#     phone_number: Optional[str]
#     agent_id: str
#     duration_formatted: str
#     created_at: str
#     status: JobStatus
#     total_score: Optional[int]
#     grade: Optional[CallGrade]
#     letter_grade: Optional[str]
#     has_fatal: bool
#     audio_url: str


# class DashboardResponse(BaseModel):
#     metrics: DashboardMetrics
#     calls: List[CallListItem]


# # ─── Upload Response ──────────────────────────────────────────────────────────

# class UploadResponse(BaseModel):
#     job_id: str
#     files_queued: int
#     status: JobStatus
#     message: str


# class JobStatusResponse(BaseModel):
#     job_id: str
#     status: JobStatus
#     progress_message: str
#     call_id: Optional[str] = None
