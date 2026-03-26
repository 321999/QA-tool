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

# """
# services/parser.py
# Converts raw LLM analysis text → structured QAScorecard JSON.
# This is the critical bridge between your existing LLM output and the frontend.
# """

# import re
# from typing import List, Tuple, Optional
# from models.schemas import (
#     QAScorecard, QASection, ScoreParameter,
#     FatalFlags, FatalFlag, CallGrade
# )


# # ─── Section Definitions (matches your ANALYSIS_PROMPT_TEMPLATE exactly) ──────

# SECTION_PARAMS = {
#     "OPENING": [
#         ("Greeting", 5),
#         ("Self Introduction", 5),
#         ("Company Introduction", 3),
#         ("Quality Disclaimer", 3),
#         ("Purpose of Call", 3),
#     ],
#     "SALES": [
#         ("Product Explanation", 10),
#         ("Customer Need Probing", 5),
#         ("Insurance Benefits Explained", 5),
#         ("Address Verification", 10),
#         ("Urgency Creation", 3),
#         ("Bank Details Confirmation", 10),
#         ("Objection Handling", 5),
#     ],
#     "SOFT_SKILLS": [
#         ("Active Listening", 5),
#         ("Hold / Dead Air", 3),
#         ("Voice Tone", 3),
#         ("Confidence", 3),
#         ("Telephone Etiquette", 3),
#         ("Speech Clarity", 3),
#         ("Rapport Building", 5),
#     ],
#     "CLOSING": [
#         ("Call Summary", 5),
#         ("Closing Thanks", 3),
#     ],
# }

# FATAL_PARAM_KEYS = {
#     "Right Party Confirmation": "right_party_confirmation",
#     "Rude Behaviour": "rude_behaviour",
#     "Miss Sell": "miss_sell",
#     "Disposition": "disposition",
# }


# def _grade_from_score(score: int) -> Tuple[CallGrade, str]:
#     """Return (CallGrade enum, letter string) from numeric score."""
#     if score >= 90:
#         return CallGrade.EXCELLENT, "A"
#     elif score >= 75:
#         return CallGrade.GOOD, "B"
#     elif score >= 60:
#         return CallGrade.AVERAGE, "C"
#     return CallGrade.POOR, "D"


# def _extract_total_score(text: str) -> int:
#     match = re.search(r"TOTAL SCORE:\s*(\d+)\s*/\s*100", text, re.IGNORECASE)
#     return int(match.group(1)) if match else 0


# def _parse_parameter_line(line: str) -> Optional[Tuple[str, int, int, str]]:
#     """
#     Parse a line like: "Greeting: 5/5 - Warm opener used correctly."
#     Returns (param_name, score, max_score, reason) or None.
#     """
#     # Match "Parameter Name: score/max - reason text"
#     pattern = r"^(.+?):\s*(\d+)\s*/\s*(\d+)\s*[-–]\s*(.+)$"
#     match = re.match(pattern, line.strip())
#     if match:
#         name = match.group(1).strip()
#         score = int(match.group(2))
#         max_s = int(match.group(3))
#         reason = match.group(4).strip()
#         return name, score, max_s, reason
#     return None


# def _parse_fatal_line(line: str) -> Optional[Tuple[str, FatalFlag]]:
#     """
#     Parse a line like: "Right Party Confirmation: F" or "Rude Behaviour: NF"
#     """
#     pattern = r"^(.+?):\s*(F|NF)\s*$"
#     match = re.match(pattern, line.strip(), re.IGNORECASE)
#     if match:
#         name = match.group(1).strip()
#         flag = FatalFlag.F if match.group(2).upper() == "F" else FatalFlag.NF
#         return name, flag
#     return None


# def _find_improvement_areas(sections: List[QASection]) -> List[str]:
#     """Extract top 3 worst-performing parameters for coaching."""
#     all_params = []
#     for sec in sections:
#         for p in sec.parameters:
#             if p.max_score > 0:
#                 all_params.append((p.parameter, p.percentage, p.reason))
#     # Sort by percentage ascending (worst first)
#     all_params.sort(key=lambda x: x[1])
#     return [f"{p[0]} ({p[1]:.0f}%): {p[2]}" for p in all_params[:3]]


# def _find_strengths(sections: List[QASection]) -> List[str]:
#     """Extract top 3 best-performing parameters."""
#     all_params = []
#     for sec in sections:
#         for p in sec.parameters:
#             if p.max_score > 0 and p.score > 0:
#                 all_params.append((p.parameter, p.percentage, p.reason))
#     all_params.sort(key=lambda x: x[1], reverse=True)
#     return [f"{p[0]} ({p[1]:.0f}%)" for p in all_params[:3]]


# def parse_analysis_text(raw_text: str) -> QAScorecard:
#     """
#     Main parser: converts raw LLM output string → structured QAScorecard.

#     Handles the exact format produced by ANALYSIS_PROMPT_TEMPLATE:
#       TOTAL SCORE: 83/100
#       OPENING
#       Greeting: 5/5 - reason
#       ...
#       FATAL
#       Right Party Confirmation: F/NF
#       ...
#     """
#     lines = raw_text.strip().splitlines()

#     total_score = _extract_total_score(raw_text)

#     # Build lookup: param_name (lowercase) → max_score from schema
#     param_max_lookup = {}
#     for sec_params in SECTION_PARAMS.values():
#         for name, max_s in sec_params:
#             param_max_lookup[name.lower()] = max_s

#     # ── Walk lines and bucket into sections ──────────────────────────────────
#     current_section = None
#     section_lines: dict[str, List[str]] = {k: [] for k in SECTION_PARAMS}
#     fatal_lines: List[str] = []

#     section_keywords = set(SECTION_PARAMS.keys()) | {"SOFT SKILLS"}
#     section_aliases = {"SOFT SKILLS": "SOFT_SKILLS", "SOFT_SKILLS": "SOFT_SKILLS"}

#     for line in lines:
#         stripped = line.strip()
#         if not stripped:
#             continue

#         upper = stripped.upper()

#         # Detect section header
#         found_section = None
#         for kw in section_keywords:
#             if upper == kw or upper.startswith(kw + ":"):
#                 found_section = section_aliases.get(kw, kw)
#                 break

#         if found_section:
#             current_section = found_section
#             continue

#         if upper == "FATAL" or upper.startswith("FATAL:"):
#             current_section = "FATAL"
#             continue

#         if current_section == "FATAL":
#             fatal_lines.append(stripped)
#         elif current_section in section_lines:
#             section_lines[current_section].append(stripped)

#     # ── Parse each section ────────────────────────────────────────────────────
#     parsed_sections: List[QASection] = []

#     for sec_name, expected_params in SECTION_PARAMS.items():
#         section_score = 0
#         section_max = sum(m for _, m in expected_params)
#         parsed_params: List[ScoreParameter] = []

#         # Build a map of parsed lines by param name
#         parsed_map = {}
#         for line in section_lines.get(sec_name, []):
#             result = _parse_parameter_line(line)
#             if result:
#                 name, score, max_s, reason = result
#                 parsed_map[name.lower()] = (name, score, max_s, reason)

#         for param_name, expected_max in expected_params:
#             key = param_name.lower()

#             if key in parsed_map:
#                 _, score, parsed_max, reason = parsed_map[key]
#                 # Trust parsed max; fallback to expected if parse gives wrong value
#                 actual_max = expected_max
#                 actual_score = min(score, actual_max)
#             else:
#                 # Param not found in LLM output — default to 0
#                 actual_score = 0
#                 actual_max = expected_max
#                 reason = "Not evaluated in this call."

#             pct = round((actual_score / actual_max) * 100, 1) if actual_max > 0 else 0
#             is_critical = actual_score == 0 and actual_max >= 5

#             parsed_params.append(ScoreParameter(
#                 parameter=param_name,
#                 score=actual_score,
#                 max_score=actual_max,
#                 percentage=pct,
#                 reason=reason,
#                 is_critical_miss=is_critical,
#             ))
#             section_score += actual_score

#         sec_pct = round((section_score / section_max) * 100, 1) if section_max > 0 else 0
#         parsed_sections.append(QASection(
#             section_name=sec_name,
#             parameters=parsed_params,
#             section_score=section_score,
#             section_max=section_max,
#             section_percentage=sec_pct,
#         ))

#     # ── Parse fatal flags ─────────────────────────────────────────────────────
#     fatal_data = {v: FatalFlag.NF for v in FATAL_PARAM_KEYS.values()}

#     for line in fatal_lines:
#         result = _parse_fatal_line(line)
#         if result:
#             name, flag = result
#             # match against known keys (case-insensitive)
#             for known_name, field_key in FATAL_PARAM_KEYS.items():
#                 if known_name.lower() in name.lower():
#                     fatal_data[field_key] = flag
#                     break

#     fatal_flags = FatalFlags(**fatal_data)

#     # ── Compute final grade ───────────────────────────────────────────────────
#     computed_total = sum(s.section_score for s in parsed_sections)
#     # Prefer LLM-reported score if close to computed (within 5 pts)
#     if abs(computed_total - total_score) > 10:
#         total_score = computed_total  # LLM made arithmetic error — use recomputed

#     pct = round((total_score / 100) * 100, 1)
#     grade, letter = _grade_from_score(total_score)

#     improvements = _find_improvement_areas(parsed_sections)
#     strengths = _find_strengths(parsed_sections)

#     # Simple summary note based on grade
#     summary_note_map = {
#         CallGrade.EXCELLENT: "Outstanding performance — agent demonstrated excellent process adherence.",
#         CallGrade.GOOD: "Good call — minor gaps in sales process but overall solid handling.",
#         CallGrade.AVERAGE: "Average performance — key areas like sales pitch and closings need work.",
#         CallGrade.POOR: "Poor performance — significant process violations detected. Coaching required.",
#     }

#     return QAScorecard(
#         total_score=total_score,
#         total_max=100,
#         percentage=pct,
#         grade=grade,
#         letter_grade=letter,
#         sections=parsed_sections,
#         fatal_flags=fatal_flags,
#         improvement_areas=improvements,
#         strengths=strengths,
#         summary_note=summary_note_map[grade],
#     )


# def flag_transcript_segments(
#     transcript_entries: list,
#     scorecard: QAScorecard,
# ) -> list:
#     """
#     Cross-references QA failures with transcript segments.
#     Marks transcript lines that likely correspond to quality failures.
#     Returns updated entries with is_flagged=True and flag_reason set.
#     """
#     flag_keywords = {
#         "Greeting": ["hello", "good morning", "good afternoon", "hi", "thank you for calling"],
#         "Quality Disclaimer": ["recorded", "quality", "monitoring", "training"],
#         "Bank Details Confirmation": ["account", "bank", "debit", "payment", "account number"],
#         "Right Party Confirmation": ["speaking", "am i speaking", "is this"],
#         "Call Summary": ["so to summarize", "to recap", "in summary", "to confirm"],
#         "Closing Thanks": ["thank you", "have a great", "goodbye", "thank you for your time"],
#     }

#     # Collect all critical miss parameters
#     critical_params = []
#     for section in scorecard.sections:
#         for p in section.parameters:
#             if p.is_critical_miss or p.percentage < 50:
#                 critical_params.append(p.parameter)

#     updated = []
#     for i, entry in enumerate(transcript_entries):
#         entry_dict = entry if isinstance(entry, dict) else entry.dict()
#         text_lower = entry_dict["text"].lower()
#         is_agent = entry_dict.get("speaker_label", "").lower() == "agent"

#         flagged = False
#         flag_reason = None

#         if is_agent:
#             for param in critical_params:
#                 keywords = flag_keywords.get(param, [])
#                 # If this param had keywords that SHOULD appear but tone/content was wrong
#                 for kw in keywords:
#                     if kw in text_lower:
#                         # Agent said the keywords but scored poorly — flag as improvement area
#                         flagged = True
#                         flag_reason = f"Quality issue: {param} — review delivery"
#                         break
#                 if flagged:
#                     break

#         entry_dict["is_flagged"] = flagged
#         entry_dict["flag_reason"] = flag_reason
#         updated.append(entry_dict)

#     return updated
