"""
Multimodal segment analysis using Gemini.
Sends video chunks to Gemini for structured metadata extraction,
producing rich per-segment analysis of body camera footage.
"""

import os
import shutil
from typing import Dict, List

from services.gemini_client import analyze_video_structured, is_gemini_enabled
from services.video_chunking import (
    slice_video,
    shift_timestamps_in_json,
)


LAW_ENFORCEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "speech_and_audio_cues_description": {"type": "string"},
        "audio_context_description": {"type": "string"},
        "use_of_force_description": {"type": "string"},
        "compliance_and_behavior_description": {"type": "string"},
        "excessive_force_description": {"type": "string"},
        "key_moments_summary": {"type": "string"},

        "scene_type": {
            "type": "string",
            "enum": ["indoor", "outdoor", "vehicle", "unknown"],
        },
        "time_of_day": {
            "type": "string",
            "enum": ["day", "dusk", "night", "dawn", "unknown"],
        },
        "lighting": {
            "type": "string",
            "enum": ["daylight", "night", "artificial", "low_light", "mixed", "unknown"],
        },
        "weather": {
            "type": "string",
            "enum": ["clear", "rain", "snow", "windy", "fog", "unknown"],
        },
        "camera_motion": {
            "type": "string",
            "enum": ["stable", "walking", "running", "vehicle_moving", "unknown"],
        },

        "camera_obfuscation_present": {"type": "boolean"},
        "camera_obfuscation_spans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_sec": {"type": "number"},
                    "end_sec": {"type": "number"},
                    "type": {
                        "type": "string",
                        "enum": ["occlusion", "low_resolution", "glare", "darkness", "blur", "other"],
                    },
                },
                "required": ["start_sec", "end_sec"],
            },
        },

        "officers_count": {"type": "integer"},
        "civilians_count": {"type": "integer"},
        "languages": {"type": "array", "items": {"type": "string"}},

        "use_of_force_present": {"type": "boolean"},
        "use_of_force_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "physical_contact", "takedown", "baton",
                    "taser_draw", "taser_deploy",
                    "firearm_draw", "firearm_discharge",
                    "pepper_spray", "restraint_handcuff",
                    "restraint_prone", "other",
                ],
            },
        },

        "potential_excessive_force": {"type": "boolean"},
    },
    "required": [
        "speech_and_audio_cues_description",
        "audio_context_description",
        "use_of_force_description",
        "compliance_and_behavior_description",
        "excessive_force_description",
        "key_moments_summary",
        "scene_type", "time_of_day", "lighting", "weather", "camera_motion",
        "camera_obfuscation_present", "camera_obfuscation_spans",
        "officers_count", "civilians_count", "languages",
        "use_of_force_present", "use_of_force_types",
        "potential_excessive_force",
    ],
}

ANALYSIS_PROMPT = """\
You are an expert multimodal analysis system reviewing law-enforcement body-camera footage.
You will receive a video segment. Your task is to analyze it objectively and return a
JSON object that strictly conforms to the given schema.

Follow these rules:

1. Structure
   - Output must be valid JSON.
   - Every key in the schema must appear exactly once.
   - For arrays, use [] if nothing is detected.
   - For enums, choose one of the listed values or "unknown" if unsure.
   - For booleans, use true/false.

2. Descriptive fields (STRING)
   - Provide concise, factual summaries based solely on visible or audible evidence.
   - Do not infer emotion, intent, or guilt.
   - Include timestamps relative to the segment start and all relevant details.

3. Objective metrics
   - Classify the environment: scene_type, time_of_day, lighting, weather, camera_motion.
   - camera_obfuscation_present: true/false based on visibility issues.
   - camera_obfuscation_spans: list timestamps in seconds when issues occur.
   - officers_count, civilians_count: numeric counts of visible individuals.
   - languages: array of spoken or heard languages (e.g., ["en", "es"]).
   - use_of_force_present: true if any physical contact or weapon use occurs.
   - use_of_force_types: list all detected force categories.
   - potential_excessive_force: true only if the clip contains potential overuse.

4. If information is NOT observable
   - For enums: "unknown"
   - For booleans: false
   - For integers: 0
   - For arrays: []
   - For strings: "No relevant observations."

Return ONLY the JSON. Do not include explanations or comments outside the JSON.
"""


def analyze_video_segments(
    video_path: str,
    chunk_seconds: int = 300,
) -> List[Dict]:
    """
    Split a video into chunks and analyze each with Gemini.
    Returns a list of segment metadata dicts with global timestamps.
    """
    if not is_gemini_enabled():
        print("[SEGMENT ANALYSIS] Gemini analysis is disabled")
        return []

    chunks_dir = os.path.join(
        os.path.dirname(os.path.abspath(video_path)),
        "..", "chunks",
    )
    chunks_dir = os.path.abspath(chunks_dir)

    try:
        slices = slice_video(video_path, chunk_seconds, chunks_dir)
        print(f"[SEGMENT ANALYSIS] Split video into {len(slices)} chunk(s) of ~{chunk_seconds // 60} min")

        results: List[Dict] = []

        for idx, chunk_path, start, end in slices:
            print(f"[SEGMENT ANALYSIS] Analyzing chunk {idx} [{start:.1f}s -> {end:.1f}s]")

            try:
                data = analyze_video_structured(
                    chunk_path,
                    ANALYSIS_PROMPT,
                    LAW_ENFORCEMENT_SCHEMA,
                )

                for key in LAW_ENFORCEMENT_SCHEMA["required"]:
                    data.setdefault(key, None)

                data = shift_timestamps_in_json(data, start)

                data["segment_idx"] = idx
                data["start_sec"] = start
                data["end_sec"] = end
                data["summary"] = _build_summary(data)

                results.append(data)

            except Exception as e:
                print(f"[SEGMENT ANALYSIS] Error on chunk {idx}: {e}")
                results.append({
                    "segment_idx": idx,
                    "start_sec": start,
                    "end_sec": end,
                    "error": str(e),
                })

        return results

    finally:
        _cleanup_chunks(chunks_dir, slices if "slices" in dir() else [])


def _build_summary(data: Dict) -> str:
    """Build a human-readable summary from structured metadata."""
    parts = []
    skip_keys = {"start_sec", "end_sec", "segment_idx", "summary"}
    for k, v in data.items():
        if k in skip_keys:
            continue
        if v is None or v == [] or v == "No relevant observations.":
            continue
        parts.append(f"{k}: {v}")
    return "\n".join(parts)


def _cleanup_chunks(chunks_dir: str, slices: list):
    """Remove temporary chunk files after analysis."""
    for _, chunk_path, _, _ in slices:
        try:
            if os.path.exists(chunk_path):
                os.unlink(chunk_path)
        except OSError:
            pass
    try:
        if os.path.exists(chunks_dir) and not os.listdir(chunks_dir):
            os.rmdir(chunks_dir)
    except OSError:
        pass
