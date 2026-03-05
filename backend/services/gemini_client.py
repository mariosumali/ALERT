"""
Gemini multimodal client for video analysis.
Supports structured JSON analysis of video segments and free-form visual QA.
"""

import json
import os
from typing import Optional

import google.generativeai as genai


def _get_gemini_model(model_name: Optional[str] = None) -> genai.GenerativeModel:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return genai.GenerativeModel(model_name)


def is_gemini_enabled() -> bool:
    if os.getenv("ENABLE_GEMINI_ANALYSIS", "false").lower() not in ("true", "1", "yes"):
        return False
    return bool(os.getenv("GEMINI_API_KEY"))


def analyze_video_structured(video_path: str, prompt: str, schema: dict) -> dict:
    """
    Send a video file to Gemini with a structured JSON schema constraint.
    Returns the parsed JSON response conforming to the schema.
    """
    model = _get_gemini_model()

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    response = model.generate_content(
        [
            prompt,
            {"inline_data": {"mime_type": "video/mp4", "data": video_bytes}},
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )

    raw = response.text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _extract_json_from_text(raw)


def ask_gemini_about_video(question: str, video_path: str) -> str:
    """
    Send a video segment to Gemini with a free-form question.
    Returns the text response.
    """
    model = _get_gemini_model()

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    response = model.generate_content(
        [
            {"text": question},
            {"inline_data": {"mime_type": "video/mp4", "data": video_bytes}},
        ]
    )

    return response.text.strip()


def _extract_json_from_text(raw: str) -> dict:
    """Fallback: extract JSON object from text that may contain markdown fences."""
    import re

    fence = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    m = fence.search(raw)
    if m:
        return json.loads(m.group(1).strip())

    start = raw.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found in response", raw, 0)

    depth = 0
    for i, ch in enumerate(raw[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start : i + 1])

    raise json.JSONDecodeError("Unbalanced braces in response", raw, 0)
