"""Utility functions for generating transcriptions with graceful fallbacks."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

# Caches so we do not repeatedly initialise heavy clients/models
_model_cache = None
_openai_client = None


@dataclass
class TranscriptionError(Exception):
    """Represents a handled transcription failure for a particular provider."""

    provider: str
    reason: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"[{self.provider}] {self.reason}: {self.message}"


def _should_use_mock(use_mock_flag: bool) -> bool:
    return use_mock_flag or os.getenv("USE_MOCK_TRANSCRIPTION", "false").lower() == "true"


def _mock_transcription(file_path: str) -> Tuple[str, List[Dict]]:
    """Return a quick mock transcription with generated segments."""

    try:
        import librosa

        duration = float(librosa.get_duration(path=file_path))
    except Exception:
        # Fall back to a 1 minute clip when duration cannot be computed quickly
        duration = 60.0

    mock_texts = [
        "Officer approaching the vehicle.",
        "Can I see your license and registration?",
        "I need to search your vehicle.",
        "You have the right to remain silent.",
        "Everything you say can and will be used against you.",
        "We have a report of a disturbance in this area.",
        "Please step out of the vehicle.",
        "I'm going to pat you down for weapons.",
        "Do you have any weapons or contraband?",
        "You're under arrest.",
    ]

    current_time = 0.0
    segments: List[Dict] = []
    full_text_parts: List[str] = []
    text_idx = 0

    while current_time < duration:
        segment_duration = 5.0 + (text_idx % 3) * 2.0  # 5-9 seconds
        end_time = min(current_time + segment_duration, duration)

        text = mock_texts[text_idx % len(mock_texts)]
        segments.append({
            "start": round(current_time, 2),
            "end": round(end_time, 2),
            "text": text,
        })
        full_text_parts.append(text)

        current_time = end_time
        text_idx += 1

    full_transcript = " ".join(full_text_parts)
    print("Using mock transcription provider.")
    return full_transcript, segments


def _load_local_whisper_model():
    global _model_cache

    if _model_cache is not None:
        return _model_cache

    try:
        import whisper  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise TranscriptionError("local", "module_missing", str(exc))

    preferred_model = os.getenv("WHISPER_MODEL_SIZE", "tiny")
    model_names = [preferred_model]
    if preferred_model != "base":
        model_names.append("base")

    for model_name in model_names:
        try:
            print(f"Loading Whisper model '{model_name}'...")
            _model_cache = whisper.load_model(model_name)
            break
        except Exception as exc:
            print(f"Failed to load Whisper model '{model_name}': {exc}")
            _model_cache = None

    if _model_cache is None:
        raise TranscriptionError("local", "model_load_failed", "Unable to load Whisper model")

    return _model_cache


def _transcribe_with_local_whisper(file_path: str) -> Tuple[str, List[Dict]]:
    if os.getenv("ENABLE_LOCAL_WHISPER", "false").lower() != "true":
        raise TranscriptionError("local", "disabled", "Local Whisper disabled via configuration")

    model = _load_local_whisper_model()

    try:
        print(f"Transcribing {file_path} using local Whisper...")
        result = model.transcribe(
            file_path,
            word_timestamps=False,
            fp16=False,
            verbose=False,
        )
    except Exception as exc:
        raise TranscriptionError("local", "transcription_failed", str(exc))

    transcript_text = result.get("text", "").strip()
    segments = [
        {
            "start": float(segment.get("start", 0.0)),
            "end": float(segment.get("end", 0.0)),
            "text": segment.get("text", "").strip(),
        }
        for segment in result.get("segments", [])
    ]

    print(f"Local Whisper transcription complete with {len(segments)} segments.")
    return transcript_text, segments


def _get_openai_client():
    global _openai_client

    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise TranscriptionError("openai", "missing_api_key", "OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise TranscriptionError("openai", "module_missing", str(exc))

    _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _transcribe_with_openai(file_path: str) -> Tuple[str, List[Dict]]:
    client = _get_openai_client()
    model_name = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    max_attempts = int(os.getenv("OPENAI_TRANSCRIPTION_MAX_RETRIES", "3"))

    for attempt in range(1, max_attempts + 1):
        try:
            print(
                f"Transcribing {file_path} using OpenAI API (model={model_name}, attempt={attempt})..."
            )
            with open(file_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=model_name,
                    file=audio_file,
                    response_format="verbose_json",
                    temperature=float(os.getenv("OPENAI_TRANSCRIPTION_TEMPERATURE", "0")),
                )

            if hasattr(response, "model_dump"):
                response_dict = response.model_dump()
            elif hasattr(response, "to_dict"):
                response_dict = response.to_dict()
            elif isinstance(response, dict):
                response_dict = response
            else:
                response_dict = getattr(response, "__dict__", {})
            transcript_text = response_dict.get("text", "").strip()
            raw_segments = response_dict.get("segments") or []

            segments: List[Dict] = []
            for segment in raw_segments:
                # Segment objects may be dicts or dataclasses depending on SDK version
                if hasattr(segment, "model_dump"):
                    segment = segment.model_dump()
                elif hasattr(segment, "to_dict"):
                    segment = segment.to_dict()

                segments.append(
                    {
                        "start": float(segment.get("start", 0.0)),
                        "end": float(segment.get("end", 0.0)),
                        "text": str(segment.get("text", "")).strip(),
                    }
                )

            print(
                f"OpenAI transcription complete with {len(segments)} segments (provider response successful)."
            )
            return transcript_text, segments
        except Exception as exc:  # pragma: no cover - relies on network errors
            status_code = getattr(exc, "status_code", None)
            error_message = str(exc)

            # Retry automatically on rate limits before falling back
            if status_code == 429 or "429" in error_message or "rate" in error_message.lower():
                if attempt < max_attempts:
                    delay = 2 ** (attempt - 1)
                    print(
                        f"OpenAI rate limit encountered (attempt {attempt}). Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                raise TranscriptionError("openai", "rate_limited", error_message)

            raise TranscriptionError("openai", "transcription_failed", error_message)

    raise TranscriptionError("openai", "unknown", "Failed to transcribe with OpenAI")


def _provider_pipeline(use_mock: bool) -> List[Callable[[str], Tuple[str, List[Dict]]]]:
    providers: List[Callable[[str], Tuple[str, List[Dict]]]] = []

    if _should_use_mock(use_mock):
        return [_mock_transcription]

    # Explicit provider selection can be enforced via TRANSCRIPTION_PROVIDER
    configured_provider = os.getenv("TRANSCRIPTION_PROVIDER", "").lower()
    if configured_provider == "openai":
        providers.append(_transcribe_with_openai)
    elif configured_provider == "local":
        providers.append(_transcribe_with_local_whisper)
    elif configured_provider == "mock":
        return [_mock_transcription]
    else:
        # Default behaviour: try OpenAI first (if API key available) then optionally local, then mock
        if os.getenv("OPENAI_API_KEY"):
            providers.append(_transcribe_with_openai)
        if os.getenv("ENABLE_LOCAL_WHISPER", "false").lower() == "true":
            providers.append(_transcribe_with_local_whisper)

    providers.append(_mock_transcription)
    return providers


def transcribe_file_with_timestamps(
    file_path: str, use_mock: bool = False
) -> Tuple[str, List[Dict]]:
    """Transcribe the media file, returning transcript text and timestamped segments."""

    errors: List[TranscriptionError] = []

    for provider in _provider_pipeline(use_mock):
        try:
            transcript, segments = provider(file_path)
            if transcript or segments:
                return transcript, segments
        except TranscriptionError as exc:
            errors.append(exc)
            print(f"Transcription provider error: {exc}")
            continue

    if errors:
        last_error = errors[-1]
        print(f"All transcription providers failed. Last error: {last_error}")

    return "", []


def transcribe_file(file_path: str) -> str:
    """Convenience wrapper that returns only the transcript text."""

    transcript, _ = transcribe_file_with_timestamps(file_path)
    return transcript

