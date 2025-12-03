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


def _align_transcript_with_audio(audio_path: str, transcript_text: str, chunk_start: float = 0.0, max_duration: float = 0.0) -> List[Dict]:
    """
    Align transcript text with audio by detecting when speech occurs using RMS energy.
    This is used when the API doesn't provide timestamps.
    
    Args:
        audio_path: Path to audio file
        transcript_text: Text to align
        chunk_start: Start time offset for this chunk
        max_duration: Maximum duration to cap segments at (0.0 = no cap)
    """
    try:
        import librosa
        import numpy as np
        
        # Load audio and extract RMS energy
        y, sr = librosa.load(audio_path, sr=None)
        audio_duration = len(y) / sr
        rms = librosa.feature.rms(y=y)[0]
        hop_length = 512
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        
        # Use max_duration if provided, otherwise use audio duration
        effective_duration = max_duration if max_duration > 0 else audio_duration
        
        # Detect speech regions (where energy is above threshold)
        rms_mean = np.mean(rms)
        speech_threshold = max(0.01, rms_mean * 0.3)
        
        # Find continuous speech regions
        speech_regions = []
        in_speech = False
        speech_start = None
        
        for i, (time, energy) in enumerate(zip(rms_times, rms)):
            # Cap to effective duration
            if time >= effective_duration:
                if in_speech:
                    speech_regions.append((speech_start, effective_duration))
                break
            if energy > speech_threshold:
                if not in_speech:
                    speech_start = time
                    in_speech = True
            else:
                if in_speech:
                    speech_regions.append((speech_start, time))
                    in_speech = False
        
        if in_speech:
            speech_regions.append((speech_start, min(rms_times[-1], effective_duration)))
        
        # If no speech detected, use full duration (capped)
        if not speech_regions:
            speech_regions = [(0.0, effective_duration)]
        
        # Split transcript into sentences
        import re
        sentence_endings = r'([.!?]+\s+|$)'
        sentences = re.split(sentence_endings, transcript_text)
        clean_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = (sentences[i] + sentences[i + 1]).strip()
                if sentence:
                    clean_sentences.append(sentence)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            clean_sentences.append(sentences[-1].strip())
        
        if not clean_sentences:
            clean_sentences = [transcript_text] if transcript_text else []
        
        # Distribute sentences across speech regions
        segments = []
        sentence_idx = 0
        total_speech_duration = sum(min(end, effective_duration) - start for start, end in speech_regions)
        
        if total_speech_duration > 0 and clean_sentences:
            time_per_sentence = total_speech_duration / len(clean_sentences)
            current_time = 0.0
            
            for sentence in clean_sentences:
                # Find which speech region this sentence belongs to
                target_time = current_time
                segment_start = None
                segment_end = None
                
                for region_start, region_end in speech_regions:
                    region_duration = min(region_end, effective_duration) - region_start
                    if target_time < region_duration:
                        segment_start = region_start + target_time
                        segment_end = min(region_start + target_time + time_per_sentence, min(region_end, effective_duration))
                        break
                    target_time -= region_duration
                
                if segment_start is not None:
                    # Cap to effective duration
                    segment_start = min(segment_start, effective_duration)
                    segment_end = min(segment_end, effective_duration)
                    
                    # Only add if valid
                    if segment_start < segment_end:
                        segments.append({
                            "start": round(chunk_start + segment_start, 2),
                            "end": round(chunk_start + segment_end, 2),
                            "text": sentence,
                        })
                current_time += time_per_sentence
        else:
            # Fallback: place all text at start (capped)
            segments.append({
                "start": round(chunk_start, 2),
                "end": round(chunk_start + min(1.0, effective_duration), 2),
                "text": transcript_text,
            })
        
        return segments
    except Exception as e:
        print(f"Warning: Could not align transcript with audio: {e}")
        # Fallback: estimate based on word count
        word_count = len(transcript_text.split())
        estimated_duration = max(1.0, (word_count / 150.0) * 60.0)
        return [{
            "start": round(chunk_start, 2),
            "end": round(chunk_start + estimated_duration, 2),
            "text": transcript_text,
        }]


def _parse_srt(srt_content: str, chunk_start_offset: float = 0.0) -> Tuple[List[Dict], str]:
    """
    Parse SRT (SubRip) subtitle format to extract segments with timestamps.
    Returns (segments, full_text) tuple.
    """
    segments = []
    full_text_parts = []
    
    # Split SRT into blocks (each subtitle entry)
    blocks = srt_content.strip().split('\n\n')
    
    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) < 3:
            continue
        
        # Line 0: sequence number (ignore)
        # Line 1: timestamp range (e.g., "00:00:00,000 --> 00:00:05,000")
        # Line 2+: text content
        time_range = lines[1]
        text = ' '.join(lines[2:])
        
        # Parse timestamp range
        if ' --> ' not in time_range:
            continue
        
        start_str, end_str = time_range.split(' --> ')
        
        # Convert SRT time format (HH:MM:SS,mmm) to seconds
        def srt_time_to_seconds(srt_time: str) -> float:
            """Convert SRT timestamp (00:00:00,000) to seconds."""
            time_part, millis = srt_time.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            total_seconds = hours * 3600 + minutes * 60 + seconds + int(millis) / 1000.0
            return total_seconds
        
        start_seconds = srt_time_to_seconds(start_str) + chunk_start_offset
        end_seconds = srt_time_to_seconds(end_str) + chunk_start_offset
        
        # Ensure we have valid timestamps
        if start_seconds >= 0 and end_seconds > start_seconds:
            segments.append({
                "start": round(start_seconds, 2),
                "end": round(end_seconds, 2),
                "text": text.strip(),
            })
        else:
            print(f"  Warning: Invalid SRT timestamps: start={start_seconds}, end={end_seconds}")
        full_text_parts.append(text.strip())
    
    full_text = " ".join(full_text_parts)
    return segments, full_text


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
    # Use whisper-1 which supports SRT format, or fallback to configured model
    model_name = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
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
        print(f"Total audio duration: {actual_duration:.1f}s, chunk duration: {chunk_duration}s")
        
        successful_chunks = 0
        failed_chunks = 0
        
        for chunk_idx, (chunk_path, chunk_start, chunk_end) in enumerate(chunks):
            chunk_files.append(chunk_path)  # Track for cleanup
            
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"Transcribing chunk {chunk_idx + 1}/{len(chunks)} ({chunk_start:.1f}s - {chunk_end:.1f}s)...")
                    with open(chunk_path, "rb") as audio_file:
                        # Try SRT first (best format with timestamps), then verbose_json, then json
                        use_verbose_json = False
                        format_used = None
                        
                        try:
                            # Try SRT format first - provides timestamps in subtitle format
                            response = client.audio.transcriptions.create(
                                model=model_name,
                                file=audio_file,
                                response_format="srt",
                                temperature=float(os.getenv("OPENAI_TRANSCRIPTION_TEMPERATURE", "0")),
                            )
                            format_used = "srt"
                        except Exception as e:
                            # If SRT fails, try verbose_json
                            if "srt" in str(e).lower() or "unsupported" in str(e).lower():
                                print(f"SRT format not supported by {model_name}, trying verbose_json...")
                                try:
                                    audio_file.seek(0)  # Reset file pointer
                                    response = client.audio.transcriptions.create(
                                        model=model_name,
                                        file=audio_file,
                                        response_format="verbose_json",
                                        temperature=float(os.getenv("OPENAI_TRANSCRIPTION_TEMPERATURE", "0")),
                                    )
                                    use_verbose_json = True
                                    format_used = "verbose_json"
                                except Exception as e2:
                                    # If verbose_json also fails, fall back to json
                                    if "verbose_json" in str(e2).lower() or "unsupported" in str(e2).lower():
                                        print(f"verbose_json not supported, trying json format...")
                                        audio_file.seek(0)  # Reset file pointer
                                        response = client.audio.transcriptions.create(
                                            model=model_name,
                                            file=audio_file,
                                            response_format="json",
                                            temperature=float(os.getenv("OPENAI_TRANSCRIPTION_TEMPERATURE", "0")),
                                        )
                                        format_used = "json (aligned)"
                                    else:
                                        raise
                            else:
                                raise
                    
                    # Parse response based on format
                    if format_used == "srt":
                        # Parse SRT format to extract timestamps and text
                        srt_content = response if isinstance(response, str) else str(response)
                        segments, transcript_text = _parse_srt(srt_content, chunk_start)
                    elif use_verbose_json:
                        # Parse verbose_json format which includes segments with timestamps
                        if hasattr(response, "model_dump"):
                            response_dict = response.model_dump()
                        elif hasattr(response, "to_dict"):
                            response_dict = response.to_dict()
                        elif isinstance(response, dict):
                            response_dict = response
                        else:
                            response_dict = getattr(response, "__dict__", {})
                        
                        transcript_text = response_dict.get("text", "").strip()
                        raw_segments = response_dict.get("segments", [])
                        
                        # Convert segments to our format with chunk offset
                        segments = []
                        for segment in raw_segments:
                            if hasattr(segment, "model_dump"):
                                segment = segment.model_dump()
                            elif hasattr(segment, "to_dict"):
                                segment = segment.to_dict()
                            
                            segment_start = float(segment.get("start", 0.0)) + chunk_start
                            segment_end = float(segment.get("end", 0.0)) + chunk_start
                            
                            # Ensure we have valid timestamps
                            if segment_start >= 0 and segment_end > segment_start:
                                segments.append({
                                    "start": round(segment_start, 2),
                                    "end": round(segment_end, 2),
                                    "text": str(segment.get("text", "")).strip(),
                                })
                            else:
                                print(f"  Warning: Invalid timestamps in segment: start={segment_start}, end={segment_end}")
                    else:
                        # JSON format - no timestamps, need to use audio analysis
                        if hasattr(response, "model_dump"):
                            response_dict = response.model_dump()
                        elif hasattr(response, "to_dict"):
                            response_dict = response.to_dict()
                        elif isinstance(response, dict):
                            response_dict = response
                        else:
                            response_dict = getattr(response, "__dict__", {})
                        
                        transcript_text = response_dict.get("text", "").strip()
                        # Use audio analysis to detect when speech occurs
                        # Pass actual_duration to cap segments
                        segments = _align_transcript_with_audio(chunk_path, transcript_text, chunk_start, actual_duration if actual_duration > 0 else 0.0)
                    
                    # Log transcript length for debugging
                    if transcript_text:
                        print(f"Chunk {chunk_idx + 1}: Received {len(transcript_text)} characters, {len(transcript_text.split())} words")
                        format_type = format_used or ("verbose_json" if use_verbose_json else "json (with audio alignment)")
                        print(f"Chunk {chunk_idx + 1}: Parsed {len(segments)} segments from {format_type} format")
                        if segments:
                            print(f"Chunk {chunk_idx + 1}: First segment: {segments[0]['start']:.1f}s - {segments[0]['end']:.1f}s")
                            if len(segments) > 1:
                                print(f"Chunk {chunk_idx + 1}: Last segment: {segments[-1]['start']:.1f}s - {segments[-1]['end']:.1f}s")

                    # Add chunk results to combined results
                    all_segments.extend(segments)
                    if transcript_text:
                        full_text_parts.append(transcript_text)
                    
                    print(f"✓ Chunk {chunk_idx + 1}/{len(chunks)} complete: {len(segments)} segments")
                    if segments:
                        print(f"  First segment: {segments[0]['start']:.1f}s - {segments[0]['end']:.1f}s: {segments[0]['text'][:50]}...")
                        if len(segments) > 1:
                            print(f"  Last segment: {segments[-1]['start']:.1f}s - {segments[-1]['end']:.1f}s: {segments[-1]['text'][:50]}...")
                    successful_chunks += 1
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
                        print(f"⚠ Chunk {chunk_idx + 1} failed after {max_attempts} retries: {error_message}")
                        failed_chunks += 1
                        break  # Skip this chunk and continue with others
                    
                    print(f"⚠ Chunk {chunk_idx + 1} failed: {error_message}")
                    failed_chunks += 1
                    break  # Skip this chunk and continue with others
        
        # Combine all results
        transcript_text = " ".join(full_text_parts)
        
        print(f"Transcription summary: {successful_chunks}/{len(chunks)} chunks successful, {failed_chunks} failed")
        print(f"Total segments collected: {len(all_segments)}, Total text length: {len(transcript_text)} characters")
        
        if not all_segments:
            raise TranscriptionError("openai", "no_segments", f"Failed to transcribe any chunks. {failed_chunks} chunks failed.")
        
        # Validate all segments have timestamps before sorting
        valid_segments = []
        for seg in all_segments:
            if "start" in seg and "end" in seg and seg.get("start", -1) >= 0 and seg.get("end", 0) > seg.get("start", -1):
                valid_segments.append(seg)
            else:
                print(f"  Warning: Dropping segment without valid timestamps: {seg}")
        
        all_segments = valid_segments
        
        if not all_segments:
            raise TranscriptionError("openai", "no_valid_segments", "No segments with valid timestamps were extracted.")
        
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
        seen_texts = {}  # Track text content and when it was last seen
        
        for i, segment in enumerate(deduplicated_segments):
            is_duplicate = False
            text = segment["text"].strip()
            start_time = segment["start"]
            
            # Check against all previous segments with same text (not just last 5)
            if text in seen_texts:
                last_seen_time = seen_texts[text]
                time_diff = abs(start_time - last_seen_time)
                # If same text appears within 5 seconds, it's likely a duplicate
                if time_diff < 5.0:
                    is_duplicate = True
            else:
                # Also check last 10 segments for similar text (catches variations)
                for prev_seg in final_segments[-10:]:
                    time_diff = abs(prev_seg["start"] - start_time)
                    prev_text = prev_seg["text"].strip()
                    # Check if texts are very similar (handles minor variations)
                    if time_diff < 2.0 and (text == prev_text or 
                                          (len(text) > 10 and len(prev_text) > 10 and 
                                           text[:min(50, len(text))] == prev_text[:min(50, len(prev_text))])):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                final_segments.append(segment)
                seen_texts[text] = start_time
        
        deduplicated_segments = final_segments
        
        # Cap all segments to not exceed actual video duration
        if actual_duration > 0:
            capped_segments = []
            for segment in deduplicated_segments:
                # Cap start and end times to actual duration
                capped_start = min(segment["start"], actual_duration)
                capped_end = min(segment["end"], actual_duration)
                
                # Only keep segments that are valid (start < end and within duration)
                if capped_start < capped_end and capped_start < actual_duration:
                    segment["start"] = round(capped_start, 2)
                    segment["end"] = round(capped_end, 2)
                    capped_segments.append(segment)
                else:
                    # Skip segments that are completely outside duration
                    print(f"  Warning: Dropping segment outside duration: {segment['start']:.1f}s - {segment['end']:.1f}s (duration: {actual_duration:.1f}s)")
            
            deduplicated_segments = capped_segments
            print(f"  Capped segments to video duration: {actual_duration:.1f}s")
        
        # Final pass: remove any remaining duplicates of the last segment
        if len(deduplicated_segments) > 1:
            last_segment = deduplicated_segments[-1]
            last_text = last_segment["text"].strip()
            # Remove any segments with identical text that appear near the end
            final_clean_segments = []
            for i, segment in enumerate(deduplicated_segments):
                # If this is one of the last 3 segments and has same text as the actual last segment, skip it
                if i >= len(deduplicated_segments) - 3 and segment["text"].strip() == last_text:
                    if i == len(deduplicated_segments) - 1:
                        # Keep the actual last one
                        final_clean_segments.append(segment)
                    # Otherwise skip duplicates
                else:
                    final_clean_segments.append(segment)
            
            deduplicated_segments = final_clean_segments
        
        # If we got no segments at all, raise error
        if not deduplicated_segments:
            raise TranscriptionError("openai", "unknown", "Failed to transcribe any chunks")
        
        print(f"✓ OpenAI transcription complete: {len(deduplicated_segments)} total segments from {len(chunks)} chunk(s) (deduplicated from {len(all_segments)})")
        if deduplicated_segments:
            print(f"  Time range: {deduplicated_segments[0]['start']:.1f}s - {deduplicated_segments[-1]['end']:.1f}s")
            if actual_duration > 0:
                coverage = (deduplicated_segments[-1]['end'] / actual_duration) * 100 if actual_duration > 0 else 0
                print(f"  Video duration: {actual_duration:.1f}s, Coverage: {coverage:.1f}%")
                if coverage < 50:
                    print(f"  ⚠ Warning: Low coverage ({coverage:.1f}%) - transcription may be incomplete")
            # Check for duplicate timestamps
            timestamp_counts = {}
            for seg in deduplicated_segments:
                ts = round(seg['start'], 0)
                timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
            duplicates = {ts: count for ts, count in timestamp_counts.items() if count > 1}
            if duplicates:
                print(f"  Warning: Found duplicate timestamps: {duplicates}")
        
        # Final validation - ensure we have segments covering the full duration
        if actual_duration > 0 and deduplicated_segments:
            last_segment_end = deduplicated_segments[-1]['end']
            if last_segment_end < actual_duration * 0.8:  # Less than 80% coverage
                print(f"  ⚠ Warning: Transcription may be incomplete. Last segment ends at {last_segment_end:.1f}s but video is {actual_duration:.1f}s")
        
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

