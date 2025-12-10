"""
Utility for parsing timestamp references from natural language text.
"""

import re
from typing import List


def parse_timestamps(text: str) -> List[float]:
    """
    Parse timestamp references from natural language text.
    
    Supports formats:
    - "at 2:30" or "at 2:30s" -> 150 seconds
    - "at 1:23:45" -> 1 hour 23 minutes 45 seconds
    - "at 45 seconds" or "at 45s" -> 45 seconds
    - "at 2 minutes 30 seconds" -> 150 seconds
    - "around 1 minute 45 seconds" -> 105 seconds
    - "0:45" or "00:45" -> 45 seconds
    
    Args:
        text: Natural language text potentially containing timestamp references
        
    Returns:
        List of timestamps in seconds
    """
    timestamps = []
    text_lower = text.lower()
    
    # Pattern 1: HH:MM:SS or MM:SS format
    # Matches: "1:23:45", "2:30", "00:03:15", "0:45"
    time_pattern = r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b'
    for match in re.finditer(time_pattern, text):
        if match.group(3):  # HH:MM:SS
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
        else:  # MM:SS
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            total_seconds = minutes * 60 + seconds
        
        timestamps.append(float(total_seconds))
    
    # Pattern 2: "X minutes Y seconds" or "X minute Y second"
    # Matches: "2 minutes 30 seconds", "1 minute 45 seconds"
    min_sec_pattern = r'\b(\d+)\s*(?:minute|minutes|min|mins)\s*(?:and\s*)?(\d+)?\s*(?:second|seconds|sec|secs)?\b'
    for match in re.finditer(min_sec_pattern, text_lower):
        minutes = int(match.group(1))
        seconds = int(match.group(2)) if match.group(2) else 0
        total_seconds = minutes * 60 + seconds
        timestamps.append(float(total_seconds))
    
    # Pattern 3: "X seconds" or "X second" (standalone)
    # Only match if not already captured by pattern 2
    sec_pattern = r'\b(\d+)\s*(?:second|seconds|sec|secs)\b'
    for match in re.finditer(sec_pattern, text_lower):
        # Check if this isn't part of a "X minutes Y seconds" pattern
        start_pos = match.start()
        # Look back for "minutes" keyword
        look_back = text_lower[max(0, start_pos-30):start_pos]
        if 'minute' not in look_back and 'min' not in look_back:
            seconds = int(match.group(1))
            timestamps.append(float(seconds))
    
    # Pattern 4: "X minutes" (standalone)
    min_pattern = r'\b(\d+)\s*(?:minute|minutes|min|mins)\b'
    for match in re.finditer(min_pattern, text_lower):
        # Check if this isn't part of a "X minutes Y seconds" pattern
        end_pos = match.end()
        # Look ahead for "seconds" keyword
        look_ahead = text_lower[end_pos:min(len(text_lower), end_pos+20)]
        if not re.search(r'\d+\s*(?:second|seconds|sec|secs)', look_ahead):
            minutes = int(match.group(1))
            timestamps.append(float(minutes * 60))
    
    # Remove duplicates and sort
    timestamps = sorted(list(set(timestamps)))
    
    return timestamps


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as a human-readable timestamp.
    
    Args:
        seconds: Timestamp in seconds
        
    Returns:
        Formatted string (e.g., "2:30", "1:23:45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"
