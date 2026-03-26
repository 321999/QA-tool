# """
# services/transcription.py
# Handles audio → diarized transcript.
# Wraps SarvamAI STT with a local mock fallback for testing without API keys.
# """

# import json
# import re
# import os
# import time
# from pathlib import Path
# from typing import List, Dict, Optional, Tuple
# from models.schemas import TranscriptEntry


# # ─── Speaker Label Detection ──────────────────────────────────────────────────

# def resolve_speaker_labels(
#     speaker_times: Dict[str, float]
# ) -> Dict[str, str]:
#     """
#     Identifies which speaker is the Agent vs Customer.
#     Agent = the speaker with the most talk time (typically the agent drives the call).
#     Returns {speaker_id: "Agent"|"Customer"}
#     """
#     if not speaker_times:
#         return {}

#     sorted_speakers = sorted(speaker_times.items(), key=lambda x: x[1], reverse=True)
#     labels = {}
#     for i, (spk, _) in enumerate(sorted_speakers):
#         labels[spk] = "Agent" if i == 0 else "Customer"
#     return labels


# def seconds_to_mmss(seconds: float) -> str:
#     minutes = int(seconds // 60)
#     sec = int(seconds % 60)
#     return f"{minutes}m{sec:02d}s"


# def _extract_phone_from_filename(filename: str) -> Optional[str]:
#     """Extract phone number from filename like 4174_09890382855_07-Mar-26.WAV"""
#     match = re.search(r"_(\d{10,11})_", filename)
#     return match.group(1) if match else None


# def _extract_call_id_from_filename(filename: str) -> str:
#     """Stable call ID from filename without extension."""
#     stem = Path(filename).stem
#     return stem


# # ─── SarvamAI Transcription ───────────────────────────────────────────────────

# class SarvamTranscriptionService:
#     """Wraps SarvamAI speech-to-text jobs with diarization."""

#     def __init__(self, client, output_dir: str = "outputs"):
#         self.client = client
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(exist_ok=True)

#     def transcribe_files(
#         self, audio_paths: List[str]
#     ) -> Dict[str, dict]:
#         """
#         Submit audio files to Sarvam STT with diarization.
#         Returns dict keyed by file stem → transcription data.
#         """
#         import time

#         print(f"[Sarvam] Submitting {len(audio_paths)} file(s)...")
#         for p in audio_paths:
#             sz = Path(p).stat().st_size if Path(p).exists() else -1
#             print(f"[Sarvam]   {Path(p).name}  {sz:,} bytes")

#         print("[Sarvam] Creating job (model=saaras:v3, diarization=True)...")
#         job = self.client.speech_to_text_job.create_job(
#             model="saaras:v3",
#             with_diarization=True,
#         )
#         print(f"[Sarvam] Job created: {job.job_id}")

#         print("[Sarvam] Uploading files to Sarvam...")
#         job.upload_files(file_paths=audio_paths)
#         print("[Sarvam] Files uploaded. Starting job...")

#         job.start()
#         print("[Sarvam] Job started. Polling for completion (timeout=10min)...")

#         # Poll manually with timeout instead of blocking wait_until_complete
#         MAX_WAIT_SECONDS = 600  # 10 minutes
#         POLL_INTERVAL    = 10   # check every 10 seconds
#         waited = 0

#         while waited < MAX_WAIT_SECONDS:
#             time.sleep(POLL_INTERVAL)
#             waited += POLL_INTERVAL

#             try:
#                 status = job.get_status() if hasattr(job, "get_status") else None
#                 # Fall back to is_failed / is_complete checks
#                 if hasattr(job, "is_complete") and job.is_complete():
#                     print(f"[Sarvam] ✓ Job complete after {waited}s")
#                     break
#                 if hasattr(job, "is_failed") and job.is_failed():
#                     raise RuntimeError(f"Sarvam job failed after {waited}s: {job.job_id}")
#                 print(f"[Sarvam] Still processing... ({waited}s elapsed)")
#             except RuntimeError:
#                 raise
#             except Exception as poll_err:
#                 print(f"[Sarvam] Poll error (will retry): {poll_err}")
#         else:
#             # Timed out
#             raise RuntimeError(
#                 f"Sarvam transcription timed out after {MAX_WAIT_SECONDS}s "
#                 f"for job {job.job_id}. Check your Sarvam dashboard."
#             )

#         # Check final status
#         if hasattr(job, "is_failed") and job.is_failed():
#             raise RuntimeError(f"Sarvam transcription job failed: {job.job_id}")

#         print("[Sarvam] Downloading outputs...")
#         job_output_dir = self.output_dir / f"transcriptions_{job.job_id}"
#         job_output_dir.mkdir(parents=True, exist_ok=True)
#         job.download_outputs(str(job_output_dir))
#         print(f"[Sarvam] Outputs saved to {job_output_dir}")

#         result = self._parse_output_dir(job_output_dir)
#         print(f"[Sarvam] Parsed {len(result)} transcription(s)")
#         return result, str(job.job_id)

#     def _parse_output_dir(self, output_dir: Path) -> Dict[str, dict]:
#         """Parse all .json outputs from a Sarvam job directory."""
#         results = {}
#         for json_file in output_dir.glob("*.json"):
#             data = json.loads(json_file.read_text())
#             parsed = self._parse_diarized_json(data)
#             parsed["source_json"] = str(json_file)
#             results[json_file.stem] = parsed
#         return results

#     def _parse_diarized_json(self, data: dict) -> dict:
#         """Convert Sarvam diarized JSON → our internal transcript format."""
#         entries_raw = data.get("diarized_transcript", {}).get("entries", [])

#         entries = []
#         speaker_times: Dict[str, float] = {}
#         total_duration = 0.0

#         for entry in entries_raw:
#             speaker = entry["speaker_id"]
#             text = entry["transcript"]
#             start = float(entry.get("start_time_seconds", 0))
#             end = float(entry.get("end_time_seconds", 0))
#             duration = end - start

#             entries.append({
#                 "speaker": speaker,
#                 "speaker_label": "",          # resolved later
#                 "start_time": start,
#                 "end_time": end,
#                 "text": text.strip(),
#                 "is_flagged": False,
#                 "flag_reason": None,
#             })

#             speaker_times[speaker] = speaker_times.get(speaker, 0.0) + duration
#             total_duration = max(total_duration, end)

#         # Resolve agent vs customer labels
#         labels = resolve_speaker_labels(speaker_times)
#         for e in entries:
#             e["speaker_label"] = labels.get(e["speaker"], "Unknown")

#         return {
#             "entries": entries,
#             "speaker_times": speaker_times,
#             "speaker_labels": labels,
#             "total_duration": total_duration,
#         }


# # ─── Mock Transcription Service (for testing without API keys) ────────────────

# MOCK_TRANSCRIPT_ENTRIES = [
#     {"speaker": "SPEAKER_00", "start_time": 0.0,  "end_time": 8.5,  "text": "Good afternoon, this is Arjun calling from SecureLife Insurance. Am I speaking with Mr. Kapoor?"},
#     {"speaker": "SPEAKER_01", "start_time": 9.0,  "end_time": 12.5, "text": "Yes, speaking. What is this regarding?"},
#     {"speaker": "SPEAKER_00", "start_time": 13.0, "end_time": 28.0, "text": "Sir, I'm calling regarding your existing policy renewal and to share details about our new comprehensive health cover that premium customers are opting for this quarter."},
#     {"speaker": "SPEAKER_01", "start_time": 29.0, "end_time": 35.0, "text": "I already have insurance. I'm not really interested in buying something new right now."},
#     {"speaker": "SPEAKER_00", "start_time": 36.0, "end_time": 58.0, "text": "I completely understand, sir. Many customers felt the same way before they saw the gap in their current coverage. Can I take just two minutes to show you how this plan actually complements what you already have?"},
#     {"speaker": "SPEAKER_01", "start_time": 59.0, "end_time": 62.0, "text": "Fine, be quick."},
#     {"speaker": "SPEAKER_00", "start_time": 63.0, "end_time": 95.0, "text": "Absolutely. This plan covers hospitalisation, critical illness, and outpatient expenses up to ten lakh per year. You're eligible for our loyalty pricing at eight hundred rupees per month. Your current address is still fourteen B Linking Road, Bandra West, correct?"},
#     {"speaker": "SPEAKER_01", "start_time": 96.0, "end_time": 102.0, "text": "Yes, that's correct. The benefits do sound quite useful."},
#     {"speaker": "SPEAKER_00", "start_time": 103.0, "end_time": 145.0, "text": "Excellent sir. I'm glad it resonates. Shall I go ahead and initiate the documentation? Our representative can visit at a time of your convenience. This offer is valid only through the end of this month."},
#     {"speaker": "SPEAKER_01", "start_time": 146.0, "end_time": 155.0, "text": "Okay, let's go ahead. What do you need from my side?"},
#     {"speaker": "SPEAKER_00", "start_time": 156.0, "end_time": 180.0, "text": "I'll need your address confirmation and preferred visit time. I'll send an SMS with the details. Is there anything else I can help you with today?"},
#     {"speaker": "SPEAKER_01", "start_time": 181.0, "end_time": 185.0, "text": "No that's all, thank you."},
#     {"speaker": "SPEAKER_00", "start_time": 186.0, "end_time": 192.0, "text": "Thank you for your time, Mr. Kapoor. Have a wonderful afternoon. Goodbye!"},
# ]

# MOCK_ANALYSIS_TEXT = """TOTAL SCORE: 77/100

# OPENING
# Greeting: 5/5 - Warm, professional greeting with name and company mentioned immediately.
# Self Introduction: 4/5 - Name given clearly; could have been more detailed about role.
# Company Introduction: 3/3 - SecureLife Insurance clearly stated at the start.
# Quality Disclaimer: 0/3 - Quality disclaimer was completely skipped — critical miss.
# Purpose of Call: 3/3 - Call purpose stated within the first 30 seconds clearly.

# SALES
# Product Explanation: 8/10 - Features well covered; pricing mentioned but not detailed enough.
# Customer Need Probing: 4/5 - Good probing of customer's existing coverage; one missed follow-up.
# Insurance Benefits Explained: 5/5 - All key benefits clearly and accurately articulated.
# Address Verification: 10/10 - Address confirmed with the customer mid-call — excellent.
# Urgency Creation: 2/3 - Month-end deadline mentioned but not emphasised strongly enough.
# Bank Details Confirmation: 0/10 - Bank details were never confirmed — critical process failure.
# Objection Handling: 4/5 - Handled the initial resistance very well with empathy.

# SOFT SKILLS
# Active Listening: 4/5 - Good listening overall; agent reflected back customer concerns.
# Hold / Dead Air: 3/3 - No unnecessary hold time observed throughout the call.
# Voice Tone: 3/3 - Consistent, professional, and warm tone maintained.
# Confidence: 3/3 - Spoke confidently on product details throughout.
# Telephone Etiquette: 3/3 - Standard telephone etiquette maintained throughout.
# Speech Clarity: 3/3 - Clear diction with no mumbling or unclear segments.
# Rapport Building: 4/5 - Good rapport built; could have personalised conversation more.

# CLOSING
# Call Summary: 3/5 - Summary given but key next steps were only partially covered.
# Closing Thanks: 3/3 - Polite and warm sign-off with customer name.

# FATAL
# Right Party Confirmation: NF
# Rude Behaviour: NF
# Miss Sell: NF
# Disposition: F"""


# class MockTranscriptionService:
#     """
#     Drop-in replacement for SarvamTranscriptionService.
#     Returns realistic mock data without making any API calls.
#     Used for local development and testing.
#     """

#     def __init__(self, output_dir: str = "outputs"):
#         self.output_dir = Path(output_dir)
#         self.output_dir.mkdir(exist_ok=True)

#     def transcribe_files(self, audio_paths: List[str]) -> Tuple[Dict[str, dict], str]:
#         """
#         Returns mock transcription + fake job ID.
#         BUG FIX: Each file gets its own stem key so multiple uploads all get records.
#         """
#         import uuid
#         job_id = f"mock-{uuid.uuid4().hex[:8]}"
#         job_dir = self.output_dir / f"transcriptions_{job_id}"
#         job_dir.mkdir(parents=True, exist_ok=True)

#         results = {}
#         for path in audio_paths:
#             stem = Path(path).stem
#             speaker_times = {"SPEAKER_00": 187.0, "SPEAKER_01": 95.0}
#             labels = resolve_speaker_labels(speaker_times)

#             entries = []
#             for e in MOCK_TRANSCRIPT_ENTRIES:
#                 entry = dict(e)
#                 entry["speaker_label"] = labels.get(e["speaker"], "Unknown")
#                 entry["is_flagged"] = False
#                 entry["flag_reason"] = None
#                 entries.append(entry)

#             results[stem] = {
#                 "entries": entries,
#                 "speaker_times": speaker_times,
#                 "speaker_labels": labels,
#                 "total_duration": 192.0,
#             }

#             # Save conversation txt (preserves original behaviour)
#             txt_path = job_dir / f"{stem}_conversation.txt"
#             lines = [f"{e['speaker']}: {e['text']}" for e in MOCK_TRANSCRIPT_ENTRIES]
#             txt_path.write_text("\n".join(lines))
#             print(f"[MockTranscription] Processed stem: {stem}")

#         return results, job_id

#     def get_mock_analysis_text(self) -> str:
#         return MOCK_ANALYSIS_TEXT


# **********************************************************************************
# """
# services/llm_analysis.py
# Handles transcript summarization and LLM-based QA scorecard generation.
# Preserves your original logic; adds structured output on top.
# """

# import re
# from pathlib import Path
# from typing import List, Optional
# from services.parser import parse_analysis_text
# from models.schemas import QAScorecard


# # ─── Prompt Template (preserved from your original exactly) ──────────────────

# ANALYSIS_PROMPT_TEMPLATE = """
# You are a Call Quality Analyst evaluating a tele-sales call.

# TRANSCRIPTION:
# {transcription}

# Evaluate agent performance and generate the QA scorecard.

# TOTAL SCORE = 100

# OUTPUT FORMAT STRICTLY:

# TOTAL SCORE: 77/100

# OPENING
# Greeting: 5/5 - reason
# Self Introduction: 4/5 - reason
# Company Introduction: 3/3 - reason
# Quality Disclaimer: 0/3 - reason
# Purpose of Call: 3/3 - reason

# SALES
# Product Explanation: 8/10 - reason
# Customer Need Probing: 4/5 - reason
# Insurance Benefits Explained: 5/5 - reason
# Address Verification: 10/10 - reason
# Urgency Creation: 2/3 - reason
# Bank Details Confirmation: 0/10 - reason
# Objection Handling: 4/5 - reason

# SOFT SKILLS
# Active Listening: 4/5 - reason
# Hold / Dead Air: 3/3 - reason
# Voice Tone: 3/3 - reason
# Confidence: 3/3 - reason
# Telephone Etiquette: 3/3 - reason
# Speech Clarity: 3/3 - reason
# Rapport Building: 4/5 - reason

# CLOSING
# Call Summary: 3/5 - reason
# Closing Thanks: 3/3 - reason

# FATAL
# Right Party Confirmation: F/NF
# Rude Behaviour: F/NF
# Miss Sell: F/NF
# Disposition: F/NF
# """

# CHUNK_MAX_CHARS = 4000


# def split_transcript(transcription: str, max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
#     """Preserved from your original code."""
#     chunks = []
#     start = 0
#     while start < len(transcription):
#         chunks.append(transcription[start:start + max_chars])
#         start += max_chars
#     return chunks


# class LLMAnalysisService:
#     """
#     Handles:
#     1. Transcript chunking + summarization  (your original logic)
#     2. QA scorecard generation via LLM      (your original logic)
#     3. Parsing raw text → QAScorecard JSON  (NEW structured layer)
#     """

#     def __init__(self, client, output_dir: str = "outputs"):
#         self.client = client
#         self.output_dir = Path(output_dir)

#     def summarize_chunk(self, chunk: str) -> str:
#         """
#         Preserved from your original code.
#         Summarizes a single transcript chunk.
#         """
#         prompt = f"""
# Summarize this call transcript part.
# Focus on key conversation points.

# {chunk}
# """
#         messages = [
#             {"role": "system", "content": "You summarize call transcripts."},
#             {"role": "user",   "content": prompt},
#         ]
#         response = self.client.chat.completions(messages=messages)
#         return response.choices[0].message.content

#     def build_combined_summary(self, transcription: str) -> str:
#         """
#         Chunk → summarize each → join.
#         Preserved from your original analyze_transcription() logic.
#         """
#         chunks = split_transcript(transcription)
#         summaries = [self.summarize_chunk(chunk) for chunk in chunks]
#         return "\n".join(summaries)

#     def analyze_transcription(
#         self,
#         conversation_text: str,
#         save_path: Optional[Path] = None,
#     ) -> tuple[str, QAScorecard]:
#         """
#         UPGRADED from your original analyze_transcription().
#         - Still summarizes and calls LLM (same logic)
#         - Now ALSO returns a structured QAScorecard alongside the raw text
#         Returns: (raw_analysis_text, QAScorecard)
#         """
#         summary = self.build_combined_summary(conversation_text)

#         prompt = ANALYSIS_PROMPT_TEMPLATE.format(transcription=summary)
#         messages = [
#             {"role": "system", "content": "You are a call QA expert."},
#             {"role": "user",   "content": prompt},
#         ]

#         response = self.client.chat.completions(messages=messages)
#         raw_text = response.choices[0].message.content

#         # Save raw text (preserves your original file-writing)
#         if save_path:
#             save_path.write_text(raw_text)
#             print(f"[LLM] Saved analysis: {save_path}")

#         # NEW: parse into structured QAScorecard
#         scorecard = parse_analysis_text(raw_text)

#         return raw_text, scorecard


# class MockLLMAnalysisService:
#     """
#     Drop-in for LLMAnalysisService when no API key is available.
#     Returns the same mock analysis text used in transcription mock.
#     """

#     def __init__(self, output_dir: str = "outputs"):
#         self.output_dir = Path(output_dir)
#         from services.transcription import MOCK_ANALYSIS_TEXT
#         self._mock_text = MOCK_ANALYSIS_TEXT

#     def summarize_chunk(self, chunk: str) -> str:
#         return f"[Mock summary of {len(chunk)} chars]"

#     def build_combined_summary(self, transcription: str) -> str:
#         return "[Mock combined summary]"

#     def analyze_transcription(
#         self,
#         conversation_text: str,
#         save_path: Optional[Path] = None,
#     ) -> tuple[str, QAScorecard]:
#         if save_path:
#             save_path.write_text(self._mock_text)
#         scorecard = parse_analysis_text(self._mock_text)
#         return self._mock_text, scorecard

# *************************************************************************************************
"""
services/llm_analysis.py
Handles transcript summarization and LLM-based QA scorecard generation.
Preserves your original logic; adds structured output on top.
"""

import re
from pathlib import Path
from typing import List, Optional
from services.parser import parse_analysis_text
from models.schemas import QAScorecard


# ─── Prompt Template (preserved from your original exactly) ──────────────────

# # ANALYSIS_PROMPT_TEMPLATE = """
# You are a Call Quality Analyst evaluating a tele-sales call.

# TRANSCRIPTION:
# {transcription}

# Evaluate agent performance and generate the QA scorecard.

# TOTAL SCORE = 100

# OUTPUT FORMAT STRICTLY:

# TOTAL SCORE: 83/100

# OPENING
# Greeting: 5/5 - reason
# Self Introduction: 4/5 - reason
# Company Introduction: 3/3 - reason
# Quality Disclaimer: 0/3 - reason
# Purpose of Call: 3/3 - reason

# SALES
# Product Explanation: 8/10 - reason
# Customer Need Probing: 4/5 - reason
# Insurance Benefits Explained: 5/5 - reason
# Address Verification: 10/10 - reason
# Urgency Creation: 2/3 - reason
# Bank Details Confirmation: 0/10 - reason
# Objection Handling: 4/5 - reason

# SOFT SKILLS
# Active Listening: 4/5 - reason
# Hold / Dead Air: 3/3 - reason
# Voice Tone: 3/3 - reason
# Confidence: 3/3 - reason
# Telephone Etiquette: 3/3 - reason
# Speech Clarity: 3/3 - reason
# Rapport Building: 4/5 - reason

# CLOSING
# Call Summary: 3/5 - reason
# Closing Thanks: 3/3 - reason

# FATAL
# Right Party Confirmation: F/NF
# Rude Behaviour: F/NF
# Miss Sell: F/NF
# Disposition: F/NF
# """


ANALYSIS_PROMPT_TEMPLATE = """
You are a Call Quality Analyst evaluating a tele-sales call.

You MUST follow the format EXACTLY.
DO NOT skip any field.
DO NOT rename anything.
DO NOT change order.

If data is missing, still assign a score and write reason.

TRANSCRIPTION:
{transcription}

TOTAL SCORE = 100

OUTPUT FORMAT STRICTLY:

TOTAL SCORE: <number>/100

OPENING
Greeting: <x>/5 - <reason>
Self Introduction: <x>/5 - <reason>
Company Introduction: <x>/3 - <reason>
Quality Disclaimer: <x>/3 - <reason>
Purpose of Call: <x>/3 - <reason>

SALES
Product Explanation: <x>/10 - <reason>
Customer Need Probing: <x>/5 - <reason>
Insurance Benefits Explained: <x>/5 - <reason>
Address Verification: <x>/10 - <reason>
Urgency Creation: <x>/3 - <reason>
Bank Details Confirmation: <x>/10 - <reason>
Objection Handling: <x>/5 - <reason>

SOFT SKILLS
Active Listening: <x>/5 - <reason>
Hold / Dead Air: <x>/3 - <reason>
Voice Tone: <x>/3 - <reason>
Confidence: <x>/3 - <reason>
Telephone Etiquette: <x>/3 - <reason>
Speech Clarity: <x>/3 - <reason>
Rapport Building: <x>/5 - <reason>

CLOSING
Call Summary: <x>/5 - <reason>
Closing Thanks: <x>/3 - <reason>

FATAL
Right Party Confirmation: F/NF
Rude Behaviour: F/NF
Miss Sell: F/NF
Disposition: F/NF

IMPORTANT:
- Replace <x> with actual numbers
- ALWAYS include ALL fields
- DO NOT add extra text
"""
CHUNK_MAX_CHARS = 4000


def split_transcript(transcription: str, max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
    """Preserved from your original code."""
    chunks = []
    start = 0
    while start < len(transcription):
        chunks.append(transcription[start:start + max_chars])
        start += max_chars
    return chunks


class LLMAnalysisService:
    """
    Handles:
    1. Transcript chunking + summarization  (your original logic)
    2. QA scorecard generation via LLM      (your original logic)
    3. Parsing raw text → QAScorecard JSON  (NEW structured layer)
    """

    def __init__(self, client, output_dir: str = "outputs"):
        self.client = client
        self.output_dir = Path(output_dir)

    def summarize_chunk(self, chunk: str) -> str:
        """
        Preserved from your original code.
        Summarizes a single transcript chunk.
        """
        prompt = f"""
Summarize this call transcript part.
Focus on key conversation points.

{chunk}
"""
        messages = [
            {"role": "system", "content": "You summarize call transcripts."},
            {"role": "user",   "content": prompt},
        ]
        response = self.client.chat.completions(messages=messages,temperature=0)
        return response.choices[0].message.content

    def build_combined_summary(self, transcription: str) -> str:
        """
        Chunk → summarize each → join.
        Preserved from your original analyze_transcription() logic.
        """
        chunks = split_transcript(transcription)
        summaries = [self.summarize_chunk(chunk) for chunk in chunks]
        return "\n".join(summaries)

    def analyze_transcription(
        self,
        conversation_text: str,
        save_path: Optional[Path] = None,
    ) -> tuple[str, QAScorecard]:
        """
        UPGRADED from your original analyze_transcription().
        - Still summarizes and calls LLM (same logic)
        - Now ALSO returns a structured QAScorecard alongside the raw text
        Returns: (raw_analysis_text, QAScorecard)
        """
        summary = self.build_combined_summary(conversation_text)

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(transcription=summary)
        messages = [
            {"role": "system", "content": "You are a call QA expert."},
            {"role": "user",   "content": prompt},
        ]

        response = self.client.chat.completions(messages=messages)
        raw_text = response.choices[0].message.content
        print(response)

        # Save raw text (preserves your original file-writing)
        if save_path:
            save_path.write_text(raw_text)
            print(f"[LLM] Saved analysis: {save_path}")

        # NEW: parse into structured QAScorecard
        scorecard = parse_analysis_text(raw_text)

        return raw_text, scorecard  


class MockLLMAnalysisService:
    """
    Drop-in for LLMAnalysisService when no API key is available.
    Returns the same mock analysis text used in transcription mock.
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        from services.transcription import MOCK_ANALYSIS_TEXT
        self._mock_text = MOCK_ANALYSIS_TEXT

    def summarize_chunk(self, chunk: str) -> str:
        return f"[Mock summary of {len(chunk)} chars]"

    def build_combined_summary(self, transcription: str) -> str:
        return "[Mock combined summary]"

    def analyze_transcription(
        self,
        conversation_text: str,
        save_path: Optional[Path] = None,
    ) -> tuple[str, QAScorecard]:
        if save_path:
            save_path.write_text(self._mock_text)
        scorecard = parse_analysis_text(self._mock_text)
        return self._mock_text, scorecard
