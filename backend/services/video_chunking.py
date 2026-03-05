"""
Video chunking service for splitting long videos into segments for Gemini analysis.
Ported and adapted from SAGE's pre_process_videos approach.
"""

import json
import math
import os
import re
import shlex
import subprocess
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union


def probe_duration_sec(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = f'ffprobe -v error -show_entries format=duration -of json "{video_path}"'
    out = subprocess.check_output(shlex.split(cmd))
    return float(json.loads(out)["format"]["duration"])


def slice_video(
    video_path: str,
    chunk_sec: int,
    out_dir: str,
) -> List[Tuple[int, str, float, float]]:
    """
    Slice a video into chunk_sec segments, re-encoded to H.264+AAC for
    compatibility with Gemini's video API.

    Returns list of (segment_idx, output_path, start_sec, end_sec).
    """
    os.makedirs(out_dir, exist_ok=True)
    total = probe_duration_sec(video_path)
    n = max(1, math.ceil(total / chunk_sec))
    results = []

    for i in range(n):
        start = i * chunk_sec
        dur = min(chunk_sec, max(0.001, total - start))
        if dur <= 0:
            break

        out_path = os.path.join(out_dir, f"chunk_{i:02d}_{uuid.uuid4().hex[:8]}.mp4")
        cmd = (
            f'ffmpeg -hide_banner -loglevel error '
            f'-i "{video_path}" -ss {start:.3f} -t {dur:.3f} '
            f'-analyzeduration 100M -probesize 100M '
            f'-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p '
            f'-c:a aac -b:a 128k '
            f'-movflags +faststart "{out_path}"'
        )
        subprocess.check_call(shlex.split(cmd))
        results.append((i, out_path, start, start + dur))

    return results


def extract_segment(
    video_path: str,
    start_sec: float,
    end_sec: float,
    out_path: str,
    target_mb: float = 25.0,
) -> str:
    """
    Extract a specific segment from a video, compressed for Gemini upload.
    Caches the result at out_path; returns out_path.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if os.path.exists(out_path):
        return out_path

    duration = max(0.1, end_sec - start_sec)
    v_kbps = _calc_target_bitrate_kbps(target_mb * 0.8, duration)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-t", str(duration),
        "-i", video_path,
        "-vf", "scale=640:-1,fps=10",
        "-c:v", "libx264", "-preset", "ultrafast", "-b:v", f"{v_kbps}k",
        "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-ar", "16000",
        "-movflags", "+faststart",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def make_segment_path(segments_dir: str, video_path: str, start_ts: str, end_ts: str) -> str:
    """Create a deterministic filename for a cached segment."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    safe_start = start_ts.replace(":", "-")
    safe_end = end_ts.replace(":", "-")
    return os.path.join(segments_dir, f"{base}__{safe_start}_to_{safe_end}.mp4")


def seconds_to_timestamp(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def timestamp_to_seconds(t: str) -> int:
    parts = list(map(int, re.findall(r"\d+", t)))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0


def shift_timestamps_in_json(
    json_obj: Union[Dict, List],
    segment_start_sec: float,
    numeric_keys: Tuple[str, ...] = ("start_sec", "end_sec", "time_sec"),
) -> Union[Dict, List]:
    """
    Shift all timestamp values from local segment time to global video time.
    Handles both numeric keys ending in _sec and mm:ss / h:mm:ss strings.
    """
    ts_pattern = re.compile(r"\b(?:(\d{1,2}):)?([0-5]?\d):([0-5]\d)\b")

    def shift_string_ts(text: str) -> str:
        def repl(m: re.Match) -> str:
            h = m.group(1)
            mm = int(m.group(2))
            ss = int(m.group(3))
            total = (int(h) * 3600 if h is not None else 0) + mm * 60 + ss
            total += segment_start_sec
            if total >= 3600:
                hh = int(total // 3600)
                rem = int(total % 3600)
                return f"{hh}:{rem // 60:02d}:{rem % 60:02d}"
            return f"{int(total // 60)}:{int(total % 60):02d}"
        return ts_pattern.sub(repl, text)

    def should_shift(key: str, val: Any) -> bool:
        if not isinstance(val, (int, float)):
            return False
        return key in numeric_keys or key.endswith("_sec")

    def walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: (float(v) + float(segment_start_sec) if should_shift(k, v) else walk(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        if isinstance(obj, str):
            return shift_string_ts(obj)
        return obj

    return walk(json_obj)


def _calc_target_bitrate_kbps(target_mb: float, duration_sec: float) -> int:
    size_bits = target_mb * 8 * 1024 * 1024
    bps = size_bits / max(duration_sec, 0.1)
    return int(bps / 1000)
