"""Helper utility functions."""
import subprocess
import json
import os

def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def get_media_duration(file_path: str) -> float:
    """
    Get media duration using ffprobe (most reliable method).
    Falls back to other methods if ffprobe fails.
    Returns duration in seconds, or 0.0 if extraction fails.
    """
    if not os.path.exists(file_path):
        return 0.0
    
    # Try ffprobe first (most reliable)
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            file_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=True
        )
        data = json.loads(result.stdout.decode())
        duration = float(data.get('format', {}).get('duration', 0))
        if duration > 0:
            return duration
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"ffprobe failed for {file_path}: {e}")
    
    # Fallback: try to extract from ffmpeg stderr
    try:
        cmd = ['ffmpeg', '-i', file_path]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        stderr_output = result.stderr.decode()
        import re
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr_output)
        if duration_match:
            hours, mins, secs, centisecs = duration_match.groups()
            duration_secs = int(hours)*3600 + int(mins)*60 + int(secs) + int(centisecs)/100
            if duration_secs > 0:
                return duration_secs
    except Exception as e:
        print(f"ffmpeg duration extraction failed for {file_path}: {e}")
    
    return 0.0

