# CallIQ Backend — Setup & API Reference

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env
echo "sarvam_api_key=YOUR_KEY_HERE" > .env

# 3. Run
uvicorn main:app --reload --port 8000

# 4. Open API docs
open http://localhost:8000/docs
```

---

## Project Structure

```
calliq/
├── main.py                      ← FastAPI app entry point
├── requirements.txt
├── .env                         ← sarvam_api_key=...
├── outputs/                     ← transcriptions + analysis text files
├── recordings/                  ← uploaded audio files
└── app/
    ├── models/
    │   └── schemas.py           ← ALL Pydantic models (single source of truth)
    ├── services/
    │   ├── analytics.py         ← Core logic (refactored from your original)
    │   ├── parser.py            ← LLM text → structured JSON parser
    │   └── prompt.py            ← QA analysis prompt template
    └── routes/
        └── api.py               ← All FastAPI route handlers
```

---

## API Endpoints

### `GET /api/dashboard`
Full dashboard payload. Feed directly to React.

**Response:**
```json
{
  "summary": {
    "total_calls": 10,
    "attended_calls": 8,
    "not_attended": 2,
    "excellent": 3,
    "good": 2,
    "average": 2,
    "poor": 1,
    "unscored": 2,
    "avg_score": 78.5
  },
  "calls": [
    {
      "call_id": "4174AB",
      "file_name": "4174_09890382855_07-Mar-26-14-28-19.WAV",
      "audio_url": "/api/audio/4174AB",
      "status": "completed",
      "grade": "good",
      "total_score": 83,
      "recorded_at": "2026-03-07T14:28:19",
      "agent_id": "SPEAKER_00",
      "duration_secs": 282.0,
      "transcript": null,
      "scorecard": null
    }
  ]
}
```

---

### `GET /api/dashboard/filter?grade=excellent`
Filter call list by grade tab click.

**Query param:** `grade` = `excellent` | `good` | `average` | `poor` | `unscored`

**Response:** Array of light `CallRecord` objects (same as `calls[]` above).

---

### `GET /api/call/{call_id}`
Full call detail — loads when user clicks a call in the list.

**Response:**
```json
{
  "call_id": "4174AB",
  "file_name": "4174_09890382855_07-Mar-26-14-28-19.WAV",
  "audio_url": "/api/audio/4174AB",
  "status": "completed",
  "grade": "good",
  "total_score": 83,
  "recorded_at": "2026-03-07T14:28:19",
  "agent_id": "SPEAKER_00",
  "duration_secs": 282.0,

  "transcript": {
    "agent_id": "SPEAKER_00",
    "customer_id": "SPEAKER_01",
    "total_duration": 282.0,
    "speaker_times": { "SPEAKER_00": 187.0, "SPEAKER_01": 95.0 },
    "entries": [
      {
        "speaker_id": "SPEAKER_00",
        "is_agent": true,
        "text": "Good afternoon, this is Arjun calling from SecureLife...",
        "start_time": 0.0,
        "end_time": 8.0,
        "duration": 8.0,
        "issue_flag": false,        ← RED LINE = true means agent failed here
        "issue_reason": null
      },
      {
        "speaker_id": "SPEAKER_00",
        "is_agent": true,
        "text": "Let me confirm your bank details...",
        "start_time": 120.0,
        "end_time": 127.0,
        "duration": 7.0,
        "issue_flag": true,         ← ← ← RENDER RED LINE ON THIS
        "issue_reason": "Bank Details Confirmation (Bank details were never confirmed)"
      }
    ]
  },

  "scorecard": {
    "total_score": 83,
    "total_max": 100,
    "grade": "good",
    "fatal_flags": {
      "right_party_confirmation": "NF",
      "rude_behaviour": "NF",
      "miss_sell": "NF",
      "disposition": "F"
    },
    "sections": [
      {
        "section_name": "OPENING",
        "section_score": 15,
        "section_max": 19,
        "section_pct": 78.9,
        "parameters": [
          {
            "parameter": "Greeting",
            "score": 5,
            "max_score": 5,
            "pct": 100.0,
            "reason": "Warm, confident opener used correctly."
          },
          {
            "parameter": "Quality Disclaimer",
            "score": 0,
            "max_score": 3,
            "pct": 0.0,
            "reason": "Disclaimer was completely skipped."
          }
        ]
      },
      {
        "section_name": "SALES",
        "section_score": 33,
        "section_max": 48,
        "section_pct": 68.75,
        "parameters": [...]
      },
      {
        "section_name": "SOFT SKILLS",
        "section_score": 24,
        "section_max": 26,
        "section_pct": 92.3,
        "parameters": [...]
      },
      {
        "section_name": "CLOSING",
        "section_score": 6,
        "section_max": 8,
        "section_pct": 75.0,
        "parameters": [...]
      }
    ]
  }
}
```

---

### `POST /api/upload`
Upload audio files. Processing happens in background.

**Request:** `multipart/form-data` with `files[]` field.

**Response:**
```json
{
  "call_ids": ["PENDING_4174AB"],
  "message": "Processing 1 file(s). Poll /call/{id} for status."
}
```

---

### `GET /api/audio/{call_id}`
Streams the original audio file. Feed directly to `<audio src="...">`.

---

### `GET /api/leaderboard`
Agent performance ranking (your original `get_summary()`).

**Response:**
```json
[
  {
    "agent_id": "SPEAKER_00",
    "total_calls": 5,
    "avg_score": 84.4,
    "grade": "good",
    "scores": [83, 91, 78, 85, 85]
  }
]
```

---

## Frontend Integration Guide

### Top Metrics Tabs
```js
const res = await fetch('/api/dashboard');
const { summary, calls } = await res.json();
// summary.excellent, summary.good, summary.average, summary.poor
```

### Click Grade Tab → Filter List
```js
const calls = await fetch('/api/dashboard/filter?grade=excellent').then(r => r.json());
```

### Click Call → Load Detail
```js
const call = await fetch(`/api/call/${callId}`).then(r => r.json());
// call.transcript.entries  → render bubbles, red lines on issue_flag=true
// call.scorecard.sections  → render parameter bars
// call.scorecard.fatal_flags → render fatal badges
// call.audio_url            → <audio src={call.audio_url} controls />
```

### Red Line Logic (React)
```jsx
{entry.issue_flag && (
  <div className="border-l-2 border-red-500 pl-2">
    <span className="text-red-400 text-xs">{entry.issue_reason}</span>
  </div>
)}
```

---

## Running Without Sarvam Key (Mock Mode)
If `sarvam_api_key` is not set, the server starts in **mock mode**:
- Transcription returns the raw text unchanged
- QA analysis returns a hardcoded realistic scorecard
- All parsing, JSON structuring, and API routes work identically
- Perfect for frontend development

```bash
# Start mock mode (no API key needed)
uvicorn main:app --reload
```


### working 
##### parser.py
```
"""
services/parser.py
Converts raw LLM analysis text → structured QAScorecard JSON.
This is the critical bridge between your existing LLM output and the frontend.
"""

import re
from typing import List, Tuple, Optional
from models.schemas import (
    QAScorecard, QASection, ScoreParameter,
    FatalFlags, FatalFlag, CallGrade
)


# ─── Section Definitions (matches your ANALYSIS_PROMPT_TEMPLATE exactly) ──────

SECTION_PARAMS = {
    "OPENING": [
        ("Greeting", 5),
        ("Self Introduction", 5),
        ("Company Introduction", 3),
        ("Quality Disclaimer", 3),
        ("Purpose of Call", 3),
    ],
    "SALES": [
        ("Product Explanation", 10),
        ("Customer Need Probing", 5),
        ("Insurance Benefits Explained", 5),
        ("Address Verification", 10),
        ("Urgency Creation", 3),
        ("Bank Details Confirmation", 10),
        ("Objection Handling", 5),
    ],
    "SOFT_SKILLS": [
        ("Active Listening", 5),
        ("Hold / Dead Air", 3),
        ("Voice Tone", 3),
        ("Confidence", 3),
        ("Telephone Etiquette", 3),
        ("Speech Clarity", 3),
        ("Rapport Building", 5),
    ],
    "CLOSING": [
        ("Call Summary", 5),
        ("Closing Thanks", 3),
    ],
}

FATAL_PARAM_KEYS = {
    "Right Party Confirmation": "right_party_confirmation",
    "Rude Behaviour": "rude_behaviour",
    "Miss Sell": "miss_sell",
    "Disposition": "disposition",
}


def _grade_from_score(score: int) -> Tuple[CallGrade, str]:
    """Return (CallGrade enum, letter string) from numeric score."""
    if score >= 90:
        return CallGrade.EXCELLENT, "A"
    elif score >= 75:
        return CallGrade.GOOD, "B"
    elif score >= 60:
        return CallGrade.AVERAGE, "C"
    return CallGrade.POOR, "D"


def _extract_total_score(text: str) -> int:
    match = re.search(r"TOTAL SCORE:\s*(\d+)\s*/\s*100", text, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _parse_parameter_line(line: str) -> Optional[Tuple[str, int, int, str]]:
    """
    Parse a line like: "Greeting: 5/5 - Warm opener used correctly."
    Returns (param_name, score, max_score, reason) or None.
    """
    # Match "Parameter Name: score/max - reason text"
    pattern = r"^(.+?):\s*(\d+)\s*/\s*(\d+)\s*[-–]\s*(.+)$"
    match = re.match(pattern, line.strip())
    if match:
        name = match.group(1).strip()
        score = int(match.group(2))
        max_s = int(match.group(3))
        reason = match.group(4).strip()
        return name, score, max_s, reason
    return None


def _parse_fatal_line(line: str) -> Optional[Tuple[str, FatalFlag]]:
    """
    Parse a line like: "Right Party Confirmation: F" or "Rude Behaviour: NF"
    """
    pattern = r"^(.+?):\s*(F|NF)\s*$"
    match = re.match(pattern, line.strip(), re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        flag = FatalFlag.F if match.group(2).upper() == "F" else FatalFlag.NF
        return name, flag
    return None


def _find_improvement_areas(sections: List[QASection]) -> List[str]:
    """Extract top 3 worst-performing parameters for coaching."""
    all_params = []
    for sec in sections:
        for p in sec.parameters:
            if p.max_score > 0:
                all_params.append((p.parameter, p.percentage, p.reason))
    # Sort by percentage ascending (worst first)
    all_params.sort(key=lambda x: x[1])
    return [f"{p[0]} ({p[1]:.0f}%): {p[2]}" for p in all_params[:3]]


def _find_strengths(sections: List[QASection]) -> List[str]:
    """Extract top 3 best-performing parameters."""
    all_params = []
    for sec in sections:
        for p in sec.parameters:
            if p.max_score > 0 and p.score > 0:
                all_params.append((p.parameter, p.percentage, p.reason))
    all_params.sort(key=lambda x: x[1], reverse=True)
    return [f"{p[0]} ({p[1]:.0f}%)" for p in all_params[:3]]


def parse_analysis_text(raw_text: str) -> QAScorecard:
    """
    Main parser: converts raw LLM output string → structured QAScorecard.

    Handles the exact format produced by ANALYSIS_PROMPT_TEMPLATE:
      TOTAL SCORE: 83/100
      OPENING
      Greeting: 5/5 - reason
      ...
      FATAL
      Right Party Confirmation: F/NF
      ...
    """
    lines = raw_text.strip().splitlines()

    total_score = _extract_total_score(raw_text)

    # Build lookup: param_name (lowercase) → max_score from schema
    param_max_lookup = {}
    for sec_params in SECTION_PARAMS.values():
        for name, max_s in sec_params:
            param_max_lookup[name.lower()] = max_s

    # ── Walk lines and bucket into sections ──────────────────────────────────
    current_section = None
    section_lines: dict[str, List[str]] = {k: [] for k in SECTION_PARAMS}
    fatal_lines: List[str] = []

    section_keywords = set(SECTION_PARAMS.keys()) | {"SOFT SKILLS"}
    section_aliases = {"SOFT SKILLS": "SOFT_SKILLS", "SOFT_SKILLS": "SOFT_SKILLS"}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        upper = stripped.upper()

        # Detect section header
        found_section = None
        for kw in section_keywords:
            if upper == kw or upper.startswith(kw + ":"):
                found_section = section_aliases.get(kw, kw)
                break

        if found_section:
            current_section = found_section
            continue

        if upper == "FATAL" or upper.startswith("FATAL:"):
            current_section = "FATAL"
            continue

        if current_section == "FATAL":
            fatal_lines.append(stripped)
        elif current_section in section_lines:
            section_lines[current_section].append(stripped)

    # ── Parse each section ────────────────────────────────────────────────────
    parsed_sections: List[QASection] = []

    for sec_name, expected_params in SECTION_PARAMS.items():
        section_score = 0
        section_max = sum(m for _, m in expected_params)
        parsed_params: List[ScoreParameter] = []

        # Build a map of parsed lines by param name
        parsed_map = {}
        for line in section_lines.get(sec_name, []):
            result = _parse_parameter_line(line)
            if result:
                name, score, max_s, reason = result
                parsed_map[name.lower()] = (name, score, max_s, reason)

        for param_name, expected_max in expected_params:
            key = param_name.lower()

            if key in parsed_map:
                _, score, parsed_max, reason = parsed_map[key]
                # Trust parsed max; fallback to expected if parse gives wrong value
                actual_max = expected_max
                actual_score = min(score, actual_max)
            else:
                # Param not found in LLM output — default to 0
                actual_score = 0
                actual_max = expected_max
                reason = "Not evaluated in this call."

            pct = round((actual_score / actual_max) * 100, 1) if actual_max > 0 else 0
            is_critical = actual_score == 0 and actual_max >= 5

            parsed_params.append(ScoreParameter(
                parameter=param_name,
                score=actual_score,
                max_score=actual_max,
                percentage=pct,
                reason=reason,
                is_critical_miss=is_critical,
            ))
            section_score += actual_score

        sec_pct = round((section_score / section_max) * 100, 1) if section_max > 0 else 0
        parsed_sections.append(QASection(
            section_name=sec_name,
            parameters=parsed_params,
            section_score=section_score,
            section_max=section_max,
            section_percentage=sec_pct,
        ))

    # ── Parse fatal flags ─────────────────────────────────────────────────────
    fatal_data = {v: FatalFlag.NF for v in FATAL_PARAM_KEYS.values()}

    for line in fatal_lines:
        result = _parse_fatal_line(line)
        if result:
            name, flag = result
            # match against known keys (case-insensitive)
            for known_name, field_key in FATAL_PARAM_KEYS.items():
                if known_name.lower() in name.lower():
                    fatal_data[field_key] = flag
                    break

    fatal_flags = FatalFlags(**fatal_data)

    # ── Compute final grade ───────────────────────────────────────────────────
    computed_total = sum(s.section_score for s in parsed_sections)
    # Prefer LLM-reported score if close to computed (within 5 pts)
    if abs(computed_total - total_score) > 10:
        total_score = computed_total  # LLM made arithmetic error — use recomputed

    pct = round((total_score / 100) * 100, 1)
    grade, letter = _grade_from_score(total_score)

    improvements = _find_improvement_areas(parsed_sections)
    strengths = _find_strengths(parsed_sections)

    # Simple summary note based on grade
    summary_note_map = {
        CallGrade.EXCELLENT: "Outstanding performance — agent demonstrated excellent process adherence.",
        CallGrade.GOOD: "Good call — minor gaps in sales process but overall solid handling.",
        CallGrade.AVERAGE: "Average performance — key areas like sales pitch and closings need work.",
        CallGrade.POOR: "Poor performance — significant process violations detected. Coaching required.",
    }

    return QAScorecard(
        total_score=total_score,
        total_max=100,
        percentage=pct,
        grade=grade,
        letter_grade=letter,
        sections=parsed_sections,
        fatal_flags=fatal_flags,
        improvement_areas=improvements,
        strengths=strengths,
        summary_note=summary_note_map[grade],
    )


def flag_transcript_segments(
    transcript_entries: list,
    scorecard: QAScorecard,
) -> list:
    """
    Cross-references QA failures with transcript segments.
    Marks transcript lines that likely correspond to quality failures.
    Returns updated entries with is_flagged=True and flag_reason set.
    """
    flag_keywords = {
        "Greeting": ["hello", "good morning", "good afternoon", "hi", "thank you for calling"],
        "Quality Disclaimer": ["recorded", "quality", "monitoring", "training"],
        "Bank Details Confirmation": ["account", "bank", "debit", "payment", "account number"],
        "Right Party Confirmation": ["speaking", "am i speaking", "is this"],
        "Call Summary": ["so to summarize", "to recap", "in summary", "to confirm"],
        "Closing Thanks": ["thank you", "have a great", "goodbye", "thank you for your time"],
    }

    # Collect all critical miss parameters
    critical_params = []
    for section in scorecard.sections:
        for p in section.parameters:
            if p.is_critical_miss or p.percentage < 50:
                critical_params.append(p.parameter)

    updated = []
    for i, entry in enumerate(transcript_entries):
        entry_dict = entry if isinstance(entry, dict) else entry.model_dump()
        text_lower = entry_dict["text"].lower()
        is_agent = entry_dict.get("speaker_label", "").lower() == "agent"

        flagged = False
        flag_reason = None

        if is_agent:
            for param in critical_params:
                keywords = flag_keywords.get(param, [])
                # If this param had keywords that SHOULD appear but tone/content was wrong
                for kw in keywords:
                    if kw in text_lower:
                        # Agent said the keywords but scored poorly — flag as improvement area
                        flagged = True
                        flag_reason = f"Quality issue: {param} — review delivery"
                        break
                if flagged:
                    break

        entry_dict["is_flagged"] = flagged
        entry_dict["flag_reason"] = flag_reason
        updated.append(entry_dict)

    return updated
```