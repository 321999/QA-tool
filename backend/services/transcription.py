"""
services/transcription.py
Handles audio → diarized transcript.
Wraps SarvamAI STT with a local mock fallback for testing without API keys.
"""
"""
services/transcription.py
Handles audio → diarized transcript.
Wraps SarvamAI STT with a local mock fallback for testing without API keys.
"""

import json
import re
import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from models.schemas import TranscriptEntry


# ─── Speaker Label Detection ──────────────────────────────────────────────────

def resolve_speaker_labels(
    speaker_times: Dict[str, float]
) -> Dict[str, str]:
    """
    Identifies which speaker is the Agent vs Customer.
    Agent = the speaker with the most talk time (typically the agent drives the call).
    Returns {speaker_id: "Agent"|"Customer"}
    """
    if not speaker_times:
        return {}

    sorted_speakers = sorted(speaker_times.items(), key=lambda x: x[1], reverse=True)
    labels = {}
    for i, (spk, _) in enumerate(sorted_speakers):
        labels[spk] = "Agent" if i == 0 else "Customer"
    return labels


def seconds_to_mmss(seconds: float) -> str:
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    return f"{minutes}m{sec:02d}s"


def _extract_phone_from_filename(filename: str) -> Optional[str]:
    """Extract phone number from filename like 4174_09890382855_07-Mar-26.WAV"""
    match = re.search(r"_(\d{10,11})_", filename)
    return match.group(1) if match else None


def _extract_call_id_from_filename(filename: str) -> str:
    """Stable call ID from filename without extension."""
    stem = Path(filename).stem
    return stem


# ─── SarvamAI Transcription ───────────────────────────────────────────────────

class SarvamTranscriptionService:
    """Wraps SarvamAI speech-to-text jobs with diarization."""

    def __init__(self, client, output_dir: str = "outputs"):
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def transcribe_files(
        self, audio_paths: List[str]
    ) -> Dict[str, dict]:
        """
        Submit audio files to Sarvam STT with diarization.
        Returns dict keyed by file stem → transcription data.
        """
        print(f"[Sarvam] Submitting {len(audio_paths)} file(s)...")

        job = self.client.speech_to_text_job.create_job(
            model="saaras:v3",
            with_diarization=True,
        )
        job.upload_files(file_paths=audio_paths)
        job.start()
        job.wait_until_complete()

        if job.is_failed():
            raise RuntimeError(f"Sarvam transcription job failed: {job.job_id}")

        job_output_dir = self.output_dir / f"transcriptions_{job.job_id}"
        job_output_dir.mkdir(parents=True, exist_ok=True)
        job.download_outputs(str(job_output_dir))
        return self._parse_output_dir(job_output_dir, audio_paths), str(job.job_id)        # return self._parse_output_dir(job_output_dir), str(job.job_id)

    # def _parse_output_dir(self, output_dir: Path, audio_paths: List[str]) -> Dict[str, dict]:
    #     """Parse Sarvam outputs and map them back to original filenames."""
    #     results = {}

    #     json_files = list(output_dir.glob("*.json"))

    #     print("[DEBUG] INPUT FILES:", [Path(p).stem for p in audio_paths])
    #     print("[DEBUG] OUTPUT FILES:", [f.stem for f in json_files])

    #     for i, json_file in enumerate(json_files):
    #         data = json.loads(json_file.read_text())
    #         parsed = self._parse_diarized_json(data)
    #         parsed["source_json"] = str(json_file)

    #     # 🔥 KEY FIX: map using index
    #         if i < len(audio_paths):
    #             original_stem = Path(audio_paths[i]).stem
    #             results[original_stem] = parsed
    #         else:
    #             print(f"[WARNING] Extra output file with no matching input: {json_file}")

    #     return results

    # def _parse_output_dir(self, output_dir: Path, audio_paths: List[str]) -> Dict[str, dict]:
    #     """Parse Sarvam outputs and map correctly to original filenames."""
    #     results = {}

    #     json_files = list(output_dir.glob("*.json"))

    #     print("[DEBUG] INPUT FILES:", [Path(p).name for p in audio_paths])
    #     print("[DEBUG] OUTPUT FILES:", [f.name for f in json_files])

    #     for json_file in json_files:
    #         data = json.loads(json_file.read_text())
    #         parsed = self._parse_diarized_json(data)
    #         parsed["source_json"] = str(json_file)

    #     # 🔥 TRY to get original filename from Sarvam response
    #         original_name = None

    #     # Try multiple possible keys (Sarvam may vary)
    #         for key in ["input_file", "file_name", "source_file", "audio_file"]:
    #             if key in data:
    #                 original_name = data[key]
    #                 break

    #         if original_name:
    #             stem = Path(original_name).stem
    #             print(f"[MAP] {json_file.name} → {stem}")
    #             results[stem] = parsed
    #         else:
    #             print(f"[ERROR] Cannot map {json_file.name} to any input file — skipping")
    #         print("[FULL JSON KEYS]", data.keys())
    #     return results

    # def _parse_output_dir(self, output_dir: Path, audio_paths: List[str]) -> Dict[str, dict]:
        """Parse Sarvam outputs and map correctly to original filenames."""
        results = {}

        json_files = list(output_dir.glob("*.json"))

        print("[DEBUG] INPUT FILES:", [Path(p).name for p in audio_paths])
        print("[DEBUG] OUTPUT FILES:", [f.name for f in json_files])

        for json_file in json_files:
            data = json.loads(json_file.read_text())

        # 🔍 DEBUG: see what Sarvam actually returns
            print("[FULL JSON KEYS]", list(data.keys()))

            parsed = self._parse_diarized_json(data)
            parsed["source_json"] = str(json_file)

        # 🔥 Try to get original filename from Sarvam response
            original_name = None

            for key in ["input_file", "file_name", "source_file", "audio_file"]:
                if key in data:
                    original_name = data[key]
                    print(f"[FOUND KEY] {key} → {original_name}")
                    break

            if original_name:
                stem = Path(original_name).stem
                print(f"[MAP] {json_file.name} → {stem}")
                results[stem] = parsed
            else:
                print(f"[ERROR] Cannot map {json_file.name} to any input file — skipping")

        return results
    def _parse_output_dir(self, output_dir: Path, audio_paths: List[str]) -> Dict[str, dict]:
        results = {}

        json_files = list(output_dir.glob("*.json"))

        print("[DEBUG] INPUT FILES:", [Path(p).name for p in audio_paths])
        print("[DEBUG] OUTPUT FILES:", [f.name for f in json_files])

        for json_file in json_files:
            data = json.loads(json_file.read_text())
            parsed = self._parse_diarized_json(data)
            parsed["source_json"] = str(json_file)

        # ✅ FINAL FIX: use filename itself
            file_name = json_file.name.replace(".json", "")
            stem = Path(file_name).stem

            print(f"[MAP] {json_file.name} → {stem}")
            results[stem] = parsed

        return results
    # def _parse_output_dir(self, output_dir: Path) -> Dict[str, dict]:
    #     """Parse all .json outputs from a Sarvam job directory."""
    #     results = {}
        
    #     for json_file in output_dir.glob("*.json"):
    #         data = json.loads(json_file.read_text())
    #         parsed = self._parse_diarized_json(data)
    #         parsed["source_json"] = str(json_file)
    #         results[json_file.stem] = parsed
    #     return results

    def _parse_diarized_json(self, data: dict) -> dict:
        """Convert Sarvam diarized JSON → our internal transcript format."""
        entries_raw = data.get("diarized_transcript", {}).get("entries", [])

        entries = []
        speaker_times: Dict[str, float] = {}
        total_duration = 0.0

        for entry in entries_raw:
            speaker = entry["speaker_id"]
            text = entry["transcript"]
            start = float(entry.get("start_time_seconds", 0))
            end = float(entry.get("end_time_seconds", 0))
            duration = end - start

            entries.append({
                "speaker": speaker,
                "speaker_label": "",          # resolved later
                "start_time": start,
                "end_time": end,
                "text": text.strip(),
                "is_flagged": False,
                "flag_reason": None,
            })

            speaker_times[speaker] = speaker_times.get(speaker, 0.0) + duration
            total_duration = max(total_duration, end)

        # Resolve agent vs customer labels
        labels = resolve_speaker_labels(speaker_times)
        for e in entries:
            e["speaker_label"] = labels.get(e["speaker"], "Unknown")

        return {
            "entries": entries,
            "speaker_times": speaker_times,
            "speaker_labels": labels,
            "total_duration": total_duration,
        }


# ─── Mock Transcription Service (for testing without API keys) ────────────────

MOCK_TRANSCRIPT_ENTRIES = [
    {"speaker": "SPEAKER_00", "start_time": 0.0,  "end_time": 8.5,  "text": "Good afternoon, this is Arjun calling from SecureLife Insurance. Am I speaking with Mr. Kapoor?"},
    {"speaker": "SPEAKER_01", "start_time": 9.0,  "end_time": 12.5, "text": "Yes, speaking. What is this regarding?"},
    {"speaker": "SPEAKER_00", "start_time": 13.0, "end_time": 28.0, "text": "Sir, I'm calling regarding your existing policy renewal and to share details about our new comprehensive health cover that premium customers are opting for this quarter."},
    {"speaker": "SPEAKER_01", "start_time": 29.0, "end_time": 35.0, "text": "I already have insurance. I'm not really interested in buying something new right now."},
    {"speaker": "SPEAKER_00", "start_time": 36.0, "end_time": 58.0, "text": "I completely understand, sir. Many customers felt the same way before they saw the gap in their current coverage. Can I take just two minutes to show you how this plan actually complements what you already have?"},
    {"speaker": "SPEAKER_01", "start_time": 59.0, "end_time": 62.0, "text": "Fine, be quick."},
    {"speaker": "SPEAKER_00", "start_time": 63.0, "end_time": 95.0, "text": "Absolutely. This plan covers hospitalisation, critical illness, and outpatient expenses up to ten lakh per year. You're eligible for our loyalty pricing at eight hundred rupees per month. Your current address is still fourteen B Linking Road, Bandra West, correct?"},
    {"speaker": "SPEAKER_01", "start_time": 96.0, "end_time": 102.0, "text": "Yes, that's correct. The benefits do sound quite useful."},
    {"speaker": "SPEAKER_00", "start_time": 103.0, "end_time": 145.0, "text": "Excellent sir. I'm glad it resonates. Shall I go ahead and initiate the documentation? Our representative can visit at a time of your convenience. This offer is valid only through the end of this month."},
    {"speaker": "SPEAKER_01", "start_time": 146.0, "end_time": 155.0, "text": "Okay, let's go ahead. What do you need from my side?"},
    {"speaker": "SPEAKER_00", "start_time": 156.0, "end_time": 180.0, "text": "I'll need your address confirmation and preferred visit time. I'll send an SMS with the details. Is there anything else I can help you with today?"},
    {"speaker": "SPEAKER_01", "start_time": 181.0, "end_time": 185.0, "text": "No that's all, thank you."},
    {"speaker": "SPEAKER_00", "start_time": 186.0, "end_time": 192.0, "text": "Thank you for your time, Mr. Kapoor. Have a wonderful afternoon. Goodbye!"},
]



MOCK_ANALYSIS_TEXT = """TOTAL SCORE: 77/100

OPENING
Greeting: 5/5 - Warm, professional greeting with name and company mentioned immediately.
Self Introduction: 4/5 - Name given clearly; could have been more detailed about role.
Company Introduction: 3/3 - SecureLife Insurance clearly stated at the start.
Quality Disclaimer: 0/3 - Quality disclaimer was completely skipped — critical miss.
Purpose of Call: 3/3 - Call purpose stated within the first 30 seconds clearly.

SALES
Product Explanation: 8/10 - Features well covered; pricing mentioned but not detailed enough.
Customer Need Probing: 4/5 - Good probing of customer's existing coverage; one missed follow-up.
Insurance Benefits Explained: 5/5 - All key benefits clearly and accurately articulated.
Address Verification: 10/10 - Address confirmed with the customer mid-call — excellent.
Urgency Creation: 2/3 - Month-end deadline mentioned but not emphasised strongly enough.
Bank Details Confirmation: 0/10 - Bank details were never confirmed — critical process failure.
Objection Handling: 4/5 - Handled the initial resistance very well with empathy.

SOFT SKILLS
Active Listening: 4/5 - Good listening overall; agent reflected back customer concerns.
Hold / Dead Air: 3/3 - No unnecessary hold time observed throughout the call.
Voice Tone: 3/3 - Consistent, professional, and warm tone maintained.
Confidence: 3/3 - Spoke confidently on product details throughout.
Telephone Etiquette: 3/3 - Standard telephone etiquette maintained throughout.
Speech Clarity: 3/3 - Clear diction with no mumbling or unclear segments.
Rapport Building: 4/5 - Good rapport built; could have personalised conversation more.

CLOSING
Call Summary: 3/5 - Summary given but key next steps were only partially covered.
Closing Thanks: 3/3 - Polite and warm sign-off with customer name.

FATAL
Right Party Confirmation: NF
Rude Behaviour: NF
Miss Sell: NF
Disposition: F"""


class MockTranscriptionService:
    """
    Drop-in replacement for SarvamTranscriptionService.
    Returns realistic mock data without making any API calls.
    Used for local development and testing.
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def transcribe_files(self, audio_paths: List[str]) -> Tuple[Dict[str, dict], str]:
        """
        Returns mock transcription + fake job ID.
        BUG FIX: Each file gets its own stem key so multiple uploads all get records.
        """
        import uuid
        job_id = f"mock-{uuid.uuid4().hex[:8]}"
        job_dir = self.output_dir / f"transcriptions_{job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        for path in audio_paths:
            stem = Path(path).stem
            speaker_times = {"SPEAKER_00": 187.0, "SPEAKER_01": 95.0}
            labels = resolve_speaker_labels(speaker_times)

            entries = []
            for e in MOCK_TRANSCRIPT_ENTRIES:
                entry = dict(e)
                entry["speaker_label"] = labels.get(e["speaker"], "Unknown")
                entry["is_flagged"] = False
                entry["flag_reason"] = None
                entries.append(entry)

            results[stem] = {
                "entries": entries,
                "speaker_times": speaker_times,
                "speaker_labels": labels,
                "total_duration": 192.0,
            }

            # Save conversation txt (preserves original behaviour)
            txt_path = job_dir / f"{stem}_conversation.txt"
            lines = [f"{e['speaker']}: {e['text']}" for e in MOCK_TRANSCRIPT_ENTRIES]
            txt_path.write_text("\n".join(lines))
            print(f"[MockTranscription] Processed stem: {stem}")

        return results, job_id

    def get_mock_analysis_text(self) -> str:
        return MOCK_ANALYSIS_TEXT

# ***********************************************************************************************
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
#         print(f"[Sarvam] Submitting {len(audio_paths)} file(s)...")

#         job = self.client.speech_to_text_job.create_job(
#             model="saaras:v3",
#             with_diarization=True,
#         )
#         job.upload_files(file_paths=audio_paths)
#         job.start()
#         job.wait_until_complete()

#         if job.is_failed():
#             raise RuntimeError(f"Sarvam transcription job failed: {job.job_id}")

#         job_output_dir = self.output_dir / f"transcriptions_{job.job_id}"
#         job_output_dir.mkdir(parents=True, exist_ok=True)
#         job.download_outputs(str(job_output_dir))

#         return self._parse_output_dir(job_output_dir), str(job.job_id)

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

# MOCK_ANALYSIS_TEXT = """TOTAL SCORE: 83/100

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
#         print(f"[Sarvam] Submitting {len(audio_paths)} file(s)...")

#         job = self.client.speech_to_text_job.create_job(
#             model="saaras:v3",
#             with_diarization=True,
#         )
#         job.upload_files(file_paths=audio_paths)
#         job.start()
#         job.wait_until_complete()

#         if job.is_failed():
#             raise RuntimeError(f"Sarvam transcription job failed: {job.job_id}")

#         job_output_dir = self.output_dir / f"transcriptions_{job.job_id}"
#         job_output_dir.mkdir(parents=True, exist_ok=True)
#         job.download_outputs(str(job_output_dir))

#         return self._parse_output_dir(job_output_dir), str(job.job_id)

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

# MOCK_ANALYSIS_TEXT = """TOTAL SCORE: 83/100

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
#         """Returns mock transcription + fake job ID."""
#         import uuid
#         job_id = f"mock-{uuid.uuid4().hex[:8]}"

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

#             # Also save conversation txt (matches original behaviour)
#             job_dir = self.output_dir / f"transcriptions_{job_id}"
#             job_dir.mkdir(parents=True, exist_ok=True)
#             txt_path = job_dir / f"{stem}_conversation.txt"
#             lines = [f"{e['speaker']}: {e['text']}" for e in MOCK_TRANSCRIPT_ENTRIES]
#             txt_path.write_text("\n".join(lines))

#         return results, job_id

#     def get_mock_analysis_text(self) -> str:
#         return MOCK_ANALYSIS_TEXT
