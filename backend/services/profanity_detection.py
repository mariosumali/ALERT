"""
Profanity detection service.
Detects profanity by analyzing transcripts for offensive language.
"""
import re
from typing import List, Dict


def detect_profanity_from_transcript(
    transcript_segments: List[Dict],
    duration: float
) -> List[Dict]:
    """
    Detect profanity by scanning transcript for offensive language.
    
    Args:
        transcript_segments: List of transcript segments with 'start', 'end', 'text'
        duration: Total duration of the audio/video
    
    Returns:
        List of profanity detection events with start_time, end_time, confidence, description
    """
    profanity_events = []
    
    if not transcript_segments:
        return profanity_events
    
    profanity_patterns = [
        r'\bf+u+c+k+\w*\b',
        r'\bs+h+i+t+\w*\b',
        r'\bd+a+m+n+\w*\b',
        r'\ba+s+s+\b',
        r'\ba+s+s+h+o+l+e+\w*\b',
        r'\bb+i+t+c+h+\w*\b',
        r'\bc+r+a+p+\b',
        r'\bh+e+l+l+\b',
        r'\bp+i+s+s+\w*\b',
        r'\bg+o+d+d+a+m+n+\w*\b',
        r'\bb+u+l+l+s+h+i+t+\w*\b',
        r'\bm+o+t+h+e+r+f+u+c+k+\w*\b',
        r'\bw+t+f+\b',
        r'\bs+o+b\b',
        r'\bd+i+c+k+\w*\b',
        r'\bb+a+s+t+a+r+d+\w*\b',
        r'\bslur\w*\b',
        r'\bn+i+g+g+\w*\b',
        r'\bf+a+g+\w*\b',
        r'\bc+u+n+t+\w*\b',
        r'\bw+h+o+r+e+\w*\b',
        r'\bstfu\b',
    ]
    
    print("[PROFANITY DETECTION] Analyzing transcript for profanity...")
    
    # Track all profanity mentions with timestamps
    profanity_mentions = []
    
    for segment in transcript_segments:
        text = segment.get('text', '').lower()
        start_time = segment.get('start', 0.0)
        end_time = segment.get('end', start_time)
        
        # Check for profanity patterns
        for pattern in profanity_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                word = match.group(0)
                profanity_mentions.append({
                    'time': start_time,
                    'end_time': end_time,
                    'word': word,
                    'text': text
                })
    
    if not profanity_mentions:
        print("[PROFANITY DETECTION] No profanity detected")
        return profanity_events
    
    print(f"[PROFANITY DETECTION] Found {len(profanity_mentions)} profanity instances")
    
    # Group profanity into events based on time windows (10 seconds)
    # This captures heated exchanges vs isolated instances
    window_size = 10.0  # seconds
    current_window = None
    
    for mention in profanity_mentions:
        mention_time = mention['time']
        
        if current_window is None:
            # Start new window
            current_window = {
                'start': mention_time,
                'end': mention['end_time'],
                'count': 1,
                'words': [mention['word']]
            }
        elif mention_time <= current_window['start'] + window_size:
            # Add to current window
            current_window['end'] = max(current_window['end'], mention['end_time'])
            current_window['count'] += 1
            current_window['words'].append(mention['word'])
        else:
            # Close current window and create event
            if current_window['count'] >= 1:
                event = _create_profanity_event(current_window, duration)
                profanity_events.append(event)
            
            # Start new window
            current_window = {
                'start': mention_time,
                'end': mention['end_time'],
                'count': 1,
                'words': [mention['word']]
            }
    
    # Don't forget the last window
    if current_window and current_window['count'] >= 1:
        event = _create_profanity_event(current_window, duration)
        profanity_events.append(event)
    
    print(f"[PROFANITY DETECTION] ✓ Detected {len(profanity_events)} profanity events")
    return profanity_events


def _create_profanity_event(window: Dict, duration: float) -> Dict:
    """
    Create a profanity event from a time window.
    
    Confidence based on profanity density:
    - 1 word = 0.70
    - 2-3 words = 0.80
    - 4+ words = 0.90+ (heated exchange)
    """
    count = window['count']
    
    # Calculate confidence based on density
    if count == 1:
        confidence = 0.60
        intensity = "isolated"
    elif count <= 3:
        confidence = 0.75
        intensity = "moderate"
    else:
        confidence = min(0.95, 0.85 + (count - 4) * 0.02)
        intensity = "heated"
    
    # Get unique words for description
    unique_words = len(set(window['words']))
    
    description = f"Profanity detected: {count} instance{'s' if count > 1 else ''} ({intensity} exchange)"
    
    return {
        'start_time': max(0.0, window['start'] - 0.5),  # Small buffer
        'end_time': min(duration, window['end'] + 0.5),
        'confidence': confidence,
        'description': description,
        'category': 'Profanity',
        'intensity': count / 10.0  # Normalized intensity
    }
