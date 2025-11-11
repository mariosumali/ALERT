"""Utility functions for generating transcriptions with graceful fallbacks."""

from __future__ import annotations

import os
import time
import subprocess
import tempfile
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


def _extract_audio_from_video(video_path: str) -> str:
    """
    Extract audio from video file to a temporary WAV file.
    Returns path to the temporary audio file.
    """
    # Check if file is a video
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    file_ext = os.path.splitext(video_path)[1].lower()
    
    if file_ext not in video_extensions:
        # Not a video file, return as-is
        return video_path
    
    # Create temporary audio file
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    temp_audio_path = temp_audio.name
    temp_audio.close()
    
    try:
        # Use ffmpeg to extract audio with more robust settings
        # -i: input file
        # -map 0:a: explicitly select audio stream (prevents issues with multiple streams)
        # -vn: disable video (redundant but safe)
        # -acodec pcm_s16le: use PCM 16-bit little-endian (WAV format)
        # -ar 16000: sample rate 16kHz (good for speech)
        # -ac 1: mono channel
        # -shortest: stop at shortest stream (prevents looping)
        # -avoid_negative_ts make_zero: handle timestamp issues
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-map', '0:a',  # Explicitly select first audio stream
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-shortest',  # Stop at shortest stream (prevents looping)
            '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
            '-y',  # Overwrite output file
            temp_audio_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=300  # 5 minute timeout
        )
        
        # Verify the extracted audio file exists and has reasonable size
        if not os.path.exists(temp_audio_path):
            raise TranscriptionError("openai", "audio_extraction_failed", "Extracted audio file was not created")
        
        file_size = os.path.getsize(temp_audio_path)
        if file_size < 1000:  # Less than 1KB is suspicious
            raise TranscriptionError("openai", "audio_extraction_failed", f"Extracted audio file is too small: {file_size} bytes")
        
        # Log extraction info
        stderr_output = result.stderr.decode() if result.stderr else ""
        # Try to extract duration from ffmpeg output
        import re
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr_output)
        if duration_match:
            hours, mins, secs, centisecs = duration_match.groups()
            duration_secs = int(hours)*3600 + int(mins)*60 + int(secs) + int(centisecs)/100
            print(f"Extracted audio duration: {duration_secs:.2f} seconds, size: {file_size} bytes")
        
        return temp_audio_path
    except subprocess.CalledProcessError as e:
        # Clean up temp file on error
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
        raise TranscriptionError(
            "openai",
            "audio_extraction_failed",
            f"Failed to extract audio from video: {e.stderr.decode() if e.stderr else str(e)}"
        )
    except FileNotFoundError:
        raise TranscriptionError(
            "openai",
            "ffmpeg_not_found",
            "ffmpeg is required to extract audio from video files but was not found"
        )


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


def _split_audio_into_chunks(audio_path: str, chunk_duration: int = 60, overlap: int = 5) -> List[Tuple[str, float, float]]:
    """
    Split audio file into chunks for transcription.
    Returns list of (chunk_path, start_time, end_time) tuples.
    """
    try:
        import librosa
        duration = float(librosa.get_duration(path=audio_path))
    except Exception:
        # If we can't get duration, return single chunk
        return [(audio_path, 0.0, 0.0)]
    
    # If audio is short enough, don't chunk
    if duration <= chunk_duration:
        return [(audio_path, 0.0, duration)]
    
    chunks = []
    current_time = 0.0
    chunk_idx = 0
    
    while current_time < duration:
        end_time = min(current_time + chunk_duration, duration)
        
        # Create temporary chunk file
        chunk_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        chunk_path = chunk_file.name
        chunk_file.close()
        
        # Extract chunk using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-ss', str(current_time),
            '-t', str(chunk_duration),
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            chunk_path
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
            chunks.append((chunk_path, current_time, end_time))
            print(f"Created chunk {chunk_idx + 1}: {current_time:.1f}s - {end_time:.1f}s")
        except Exception as e:
            print(f"Warning: Failed to create chunk at {current_time}s: {e}")
            # Clean up failed chunk file
            if os.path.exists(chunk_path):
                os.unlink(chunk_path)
        
        # Move to next chunk without overlap to avoid duplicates
        # We'll handle word boundaries by using sentence-based segmentation instead
        current_time = end_time
        chunk_idx += 1
        
        # Safety limit
        if chunk_idx > 100:
            print("Warning: Too many chunks, stopping")
            break
    
    return chunks


def _transcribe_with_openai(file_path: str) -> Tuple[str, List[Dict]]:
    client = _get_openai_client()
    model_name = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    max_attempts = int(os.getenv("OPENAI_TRANSCRIPTION_MAX_RETRIES", "3"))
    chunk_duration = int(os.getenv("OPENAI_CHUNK_DURATION", "60"))  # 60 seconds per chunk
    chunk_overlap = int(os.getenv("OPENAI_CHUNK_OVERLAP", "5"))  # 5 second overlap

    # Extract audio from video if needed
    audio_path = file_path
    temp_audio_path = None
    chunk_files = []  # Track chunk files for cleanup
    
    try:
        audio_path = _extract_audio_from_video(file_path)
        if audio_path != file_path:
            temp_audio_path = audio_path
            print(f"Extracted audio from video to {audio_path}")
    except TranscriptionError as e:
        # If extraction fails, try with original file (might work for some formats)
        print(f"Warning: Could not extract audio: {e}. Trying original file...")
        audio_path = file_path

    try:
        # Split into chunks if needed
        chunks = _split_audio_into_chunks(audio_path, chunk_duration, chunk_overlap)
        
        # Get actual duration for timestamp calculation
        try:
            import librosa
            actual_duration = float(librosa.get_duration(path=audio_path))
        except Exception:
            actual_duration = 0.0
        
        # Fix chunks that have 0.0 end time (single file case)
        if len(chunks) == 1 and chunks[0][2] == 0.0:
            # Single file, no chunking needed - use actual duration
            chunk_path = chunks[0][0]
            chunks = [(chunk_path, 0.0, actual_duration)]
        
        all_segments = []
        full_text_parts = []
        
        print(f"Transcribing {len(chunks)} chunk(s) using OpenAI API (model={model_name})...")
        
        for chunk_idx, (chunk_path, chunk_start, chunk_end) in enumerate(chunks):
            chunk_files.append(chunk_path)  # Track for cleanup
            
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"Transcribing chunk {chunk_idx + 1}/{len(chunks)} ({chunk_start:.1f}s - {chunk_end:.1f}s)...")
                    with open(chunk_path, "rb") as audio_file:
                        response = client.audio.transcriptions.create(
                            model=model_name,
                            file=audio_file,
                            response_format="json",
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
                    
                    # Log transcript length for debugging (only for first chunk to avoid spam)
                    if transcript_text and chunk_idx == 0:
                        print(f"Received transcript: {len(transcript_text)} characters, {len(transcript_text.split())} words")
                        # Show first 200 chars as preview
                        preview = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
                        print(f"Transcript preview: {preview}")
                    
                    # Save transcript to file for inspection (only first chunk to avoid duplicates)
                    if chunk_idx == 0:
                        try:
                            # Create transcripts directory in the same location as uploads
                            # file_path is typically ./uploads/{file_id}.mp4
                            uploads_dir = os.path.dirname(os.path.abspath(file_path))
                            transcripts_dir = os.path.join(uploads_dir, "..", "transcripts")
                            transcripts_dir = os.path.abspath(transcripts_dir)
                            os.makedirs(transcripts_dir, exist_ok=True)
                            
                            # Save to file with timestamp
                            import datetime
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            file_id = os.path.splitext(os.path.basename(file_path))[0]
                            transcript_file = os.path.join(transcripts_dir, f"{file_id}_{timestamp}.txt")
                            
                            with open(transcript_file, "w", encoding="utf-8") as f:
                                f.write(f"File: {file_path}\n")
                                f.write(f"Transcribed: {timestamp}\n")
                                f.write(f"Characters: {len(transcript_text)}\n")
                                f.write(f"Words: {len(transcript_text.split())}\n")
                                f.write(f"Segments from API: {len(raw_segments)}\n")
                                f.write("-" * 80 + "\n\n")
                                f.write(transcript_text)
                            
                            print(f"Saved transcript to: {transcript_file}")
                        except Exception as e:
                            print(f"Warning: Could not save transcript to file: {e}")

                    segments: List[Dict] = []
                    
                    # If segments are provided (verbose_json format), use them
                    if raw_segments:
                        for segment in raw_segments:
                            # Segment objects may be dicts or dataclasses depending on SDK version
                            if hasattr(segment, "model_dump"):
                                segment = segment.model_dump()
                            elif hasattr(segment, "to_dict"):
                                segment = segment.to_dict()

                            # Adjust timestamps based on chunk start time
                            segment_start = float(segment.get("start", 0.0)) + chunk_start
                            segment_end = float(segment.get("end", 0.0)) + chunk_start
                            
                            segments.append({
                                "start": round(segment_start, 2),
                                "end": round(segment_end, 2),
                                "text": str(segment.get("text", "")).strip(),
                            })
                    else:
                        # If no segments (json format), split transcript into sentence-based segments
                        # Calculate chunk duration for timestamp estimation
                        chunk_dur = chunk_end - chunk_start
                        if chunk_dur <= 0:
                            # Try to get actual duration of the chunk file
                            try:
                                import librosa
                                chunk_dur = float(librosa.get_duration(path=chunk_path))
                            except Exception:
                                # Fallback: estimate ~150 words per minute
                                word_count = len(transcript_text.split())
                                chunk_dur = max(1.0, (word_count / 150.0) * 60.0)
                        
                        # Ensure chunk_dur is positive
                        if chunk_dur <= 0:
                            chunk_dur = 60.0  # Default to 60 seconds if we can't determine
                        
                        # Split transcript into sentences
                        import re
                        sentence_endings = r'([.!?]+\s+|$)'
                        sentences = re.split(sentence_endings, transcript_text)
                        
                        # Filter and combine sentences
                        clean_sentences = []
                        for i in range(0, len(sentences) - 1, 2):
                            if i + 1 < len(sentences):
                                sentence = (sentences[i] + sentences[i + 1]).strip()
                                if sentence:
                                    clean_sentences.append(sentence)
                        if len(sentences) % 2 == 1 and sentences[-1].strip():
                            clean_sentences.append(sentences[-1].strip())
                        
                        # Fallback splitting methods
                        if not clean_sentences:
                            parts = [p.strip() for p in transcript_text.split(',') if p.strip()]
                            if len(parts) > 1:
                                clean_sentences = parts
                            else:
                                clean_sentences = [transcript_text] if transcript_text else []
                        
                        # Create segments with timestamps relative to chunk start
                        if clean_sentences:
                            time_per_segment = chunk_dur / len(clean_sentences) if clean_sentences else chunk_dur
                            current_time = 0.0
                            
                            for sentence in clean_sentences:
                                segment_end = min(current_time + time_per_segment, chunk_dur)
                                segments.append({
                                    "start": round(chunk_start + current_time, 2),
                                    "end": round(chunk_start + segment_end, 2),
                                    "text": sentence,
                                })
                                current_time = segment_end
                        else:
                            segments.append({
                                "start": round(chunk_start, 2),
                                "end": round(chunk_start + chunk_dur, 2),
                                "text": transcript_text,
                            })

                    # Add chunk results to combined results
                    all_segments.extend(segments)
                    if transcript_text:
                        full_text_parts.append(transcript_text)
                    
                    print(f"Chunk {chunk_idx + 1} complete: {len(segments)} segments")
                    if segments:
                        print(f"  First segment: {segments[0]['start']:.1f}s - {segments[0]['end']:.1f}s: {segments[0]['text'][:50]}...")
                        if len(segments) > 1:
                            print(f"  Last segment: {segments[-1]['start']:.1f}s - {segments[-1]['end']:.1f}s: {segments[-1]['text'][:50]}...")
                    break  # Success, move to next chunk
                    
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None)
                    error_message = str(exc)

                    # Retry automatically on rate limits
                    if status_code == 429 or "429" in error_message or "rate" in error_message.lower():
                        if attempt < max_attempts:
                            delay = 2 ** (attempt - 1)
                            print(f"Chunk {chunk_idx + 1} rate limit (attempt {attempt}). Retrying in {delay}s...")
                            time.sleep(delay)
                            continue
                        print(f"Warning: Chunk {chunk_idx + 1} failed after retries: {error_message}")
                        break  # Skip this chunk and continue with others
                    
                    print(f"Warning: Chunk {chunk_idx + 1} failed: {error_message}")
                    break  # Skip this chunk and continue with others
        
        # Combine all results
        transcript_text = " ".join(full_text_parts)
        
        # Sort segments by start time
        all_segments.sort(key=lambda x: x["start"])
        
        # Deduplicate overlapping segments
        # Remove segments with duplicate timestamps or very similar text at same time
        deduplicated_segments = []
        seen_times = set()
        
        for segment in all_segments:
            start_time = round(segment["start"], 1)  # Round to 0.1s precision
            end_time = round(segment["end"], 1)
            time_key = (start_time, end_time)
            text = segment["text"].strip()
            
            # Check if we've seen this exact timestamp
            if time_key in seen_times:
                # Check if text is also the same (definite duplicate)
                for existing in deduplicated_segments:
                    if abs(existing["start"] - segment["start"]) < 0.1 and existing["text"] == text:
                        # Skip this duplicate
                        continue
                # If text is different but timestamp same, might be legitimate overlap - keep it
                deduplicated_segments.append(segment)
            else:
                seen_times.add(time_key)
                deduplicated_segments.append(segment)
        
        # Additional pass: remove segments that are too close together with identical text
        final_segments = []
        for i, segment in enumerate(deduplicated_segments):
            is_duplicate = False
            for prev_seg in final_segments[-5:]:  # Check last 5 segments
                time_diff = abs(prev_seg["start"] - segment["start"])
                if time_diff < 1.0 and prev_seg["text"] == segment["text"]:
                    is_duplicate = True
                    break
            if not is_duplicate:
                final_segments.append(segment)
        
        deduplicated_segments = final_segments
        
        # If we got no segments at all, raise error
        if not deduplicated_segments:
            raise TranscriptionError("openai", "unknown", "Failed to transcribe any chunks")
        
        print(f"OpenAI transcription complete: {len(deduplicated_segments)} total segments from {len(chunks)} chunk(s) (deduplicated from {len(all_segments)})")
        if deduplicated_segments:
            print(f"  Time range: {deduplicated_segments[0]['start']:.1f}s - {deduplicated_segments[-1]['end']:.1f}s")
            # Check for duplicate timestamps
            timestamp_counts = {}
            for seg in deduplicated_segments:
                ts = round(seg['start'], 0)
                timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
            duplicates = {ts: count for ts, count in timestamp_counts.items() if count > 1}
            if duplicates:
                print(f"  Warning: Found duplicate timestamps: {duplicates}")
        
        return transcript_text, deduplicated_segments
    finally:
        # Clean up temporary files
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except Exception:
                pass
        
        # Clean up chunk files (exclude original audio_path)
        for chunk_file in chunk_files:
            if chunk_file != audio_path and os.path.exists(chunk_file):
                try:
                    os.unlink(chunk_file)
                except Exception:
                    pass


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

