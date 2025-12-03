"""
Gunshot detection service.
Detects gunshots by analyzing transcripts for "shots fired" mentions
and checking for frequency anomalies in the period before the mention.
"""
import re
from typing import List, Dict, Optional, Tuple
import numpy as np
import librosa


def detect_gunshots_from_transcript(
    transcript_segments: List[Dict],
    audio_path: str,
    duration: float
) -> List[Dict]:
    """
    Detect gunshots by:
    1. Searching transcript for "shots fired" or similar phrases
    2. Checking the period before (5-10 seconds) for frequency anomalies
    
    Args:
        transcript_segments: List of transcript segments with 'start', 'end', 'text'
        audio_path: Path to audio file for frequency analysis
        duration: Total duration of the audio/video
    
    Returns:
        List of gunshot detection events with start_time, end_time, confidence, description
    """
    gunshot_events = []
    
    if not transcript_segments or not audio_path:
        return gunshot_events
    
    # Patterns to detect "shots fired" mentions
    shot_patterns = [
        r"shots?\s+fired",
        r"shot['']?s?\s+fired",
        r"gunshot",
        r"gun\s+shot",
        r"fired\s+shots?",
        r"discharged\s+weapon",
        r"weapon\s+discharged",
        r"pop\s+pop",
        r"bang",
        r"pow",
        r"shooting",
        r"open\s+fire",
    ]
    
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in shot_patterns]
    
    # Find all mentions of shots fired in transcript
    shot_mentions = []
    for segment in transcript_segments:
        text = segment.get('text', '')
        start_time = segment.get('start', 0.0)
        end_time = segment.get('end', 0.0)
        
        for pattern in compiled_patterns:
            if pattern.search(text):
                shot_mentions.append({
                    'text': text,
                    'mention_time': start_time,  # Time when "shots fired" was mentioned
                    'segment_start': start_time,
                    'segment_end': end_time
                })
                print(f"[GUNSHOT DETECTION] Found mention: '{text[:50]}...' at {start_time:.2f}s")
                break
    
    if not shot_mentions:
        print("[GUNSHOT DETECTION] No 'shots fired' mentions found in transcript")
        return gunshot_events
    
    # Load audio for frequency analysis
    try:
        y, sr = librosa.load(audio_path, sr=None)
        if len(y) == 0:
            print("[GUNSHOT DETECTION] Empty audio file")
            return gunshot_events
        
        # Extract spectral features
        hop_length = 512
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        
        # Calculate frequency statistics
        centroid_mean = np.mean(spectral_centroids)
        centroid_std = np.std(spectral_centroids)
        rolloff_mean = np.mean(spectral_rolloff)
        rolloff_std = np.std(spectral_rolloff)
        zcr_mean = np.mean(zero_crossing_rate)
        zcr_std = np.std(zero_crossing_rate)
        
        # Thresholds for frequency anomalies (gunshots often have distinctive frequency signatures)
        # Gunshots typically have sharp transients with high frequency content
        centroid_high_threshold = centroid_mean + 2.5 * centroid_std
        rolloff_threshold = rolloff_mean + 2.5 * rolloff_std
        zcr_threshold = zcr_mean + 2.5 * zcr_std
        
        print(f"[GUNSHOT DETECTION] Analyzing {len(shot_mentions)} mentions for frequency anomalies...")
        
        # For each mention, check the period before (5-10 seconds) for frequency anomalies
        for mention in shot_mentions:
            mention_time = mention['mention_time']
            
            # Look back 5-10 seconds before the mention
            lookback_start = max(0.0, mention_time - 10.0)
            lookback_end = mention_time - 1.0  # End 1 second before mention to avoid overlap
            
            if lookback_end <= lookback_start:
                continue
            
            # Find frequency anomalies in this period
            anomaly_scores = []
            anomaly_times = []
            
            for i, time in enumerate(rms_times):
                if lookback_start <= time <= lookback_end:
                    centroid = spectral_centroids[i] if i < len(spectral_centroids) else centroid_mean
                    rolloff = spectral_rolloff[i] if i < len(spectral_rolloff) else rolloff_mean
                    zcr = zero_crossing_rate[i] if i < len(zero_crossing_rate) else zcr_mean
                    
                    score = 0
                    # High frequency content (gunshots have sharp transients)
                    if centroid > centroid_high_threshold:
                        score += 1
                    # High spectral rolloff (energy concentrated in high frequencies)
                    if rolloff > rolloff_threshold:
                        score += 1
                    # High zero crossing rate (sharp transients)
                    if zcr > zcr_threshold:
                        score += 1
                    
                    if score >= 1:  # At least 1 indicator (relaxed from 2)
                        anomaly_scores.append(score)
                        anomaly_times.append(time)
            
            if anomaly_times:
                # Find the most significant anomaly (highest score, closest to mention)
                best_idx = 0
                best_score = anomaly_scores[0]
                best_time = anomaly_times[0]
                
                for idx, (score, time) in enumerate(zip(anomaly_scores, anomaly_times)):
                    # Prefer higher scores, and if tied, prefer times closer to mention
                    time_proximity = 1.0 / (1.0 + abs(time - mention_time))
                    combined_score = score + time_proximity
                    
                    current_best_proximity = 1.0 / (1.0 + abs(best_time - mention_time))
                    if combined_score > best_score + current_best_proximity:
                        best_score = score
                        best_time = time
                        best_idx = idx
                
                # Create gunshot event
                # Mark a 0.5-2 second window around the anomaly
                gunshot_start = max(0.0, best_time - 0.5)
                gunshot_end = min(duration, best_time + 1.5)
                
                # Confidence based on anomaly score and proximity to mention
                proximity_factor = 1.0 / (1.0 + abs(best_time - mention_time))
                confidence = min(0.95, 0.75 + (best_score - 1) * 0.1 + proximity_factor * 0.1)
                
                # Only include if confidence >= 0.7 (relaxed from 0.8)
                if confidence >= 0.7:
                    gunshot_events.append({
                        'start_time': gunshot_start,
                        'end_time': gunshot_end,
                        'category': 'Gunshot',
                        'confidence': confidence,
                        'description': f"Gunshot detected. Mentioned at {mention_time:.1f}s, frequency anomaly at {best_time:.1f}s",
                        'intensity': float(best_score / 3.0)  # Normalize to 0-1
                    })
                    print(f"[GUNSHOT DETECTION] ✓ Detected gunshot at {best_time:.1f}s (confidence: {confidence:.2f}, mentioned at {mention_time:.1f}s)")
            else:
                # No frequency anomaly found, but still mark the mention time as potential gunshot
                # with lower confidence
                gunshot_start = max(0.0, mention_time - 2.0)
                gunshot_end = min(duration, mention_time + 1.0)
                
                # ALWAYS add the event if mentioned, but with lower confidence
                # This ensures it shows up in the UI if the user filters for it
                gunshot_events.append({
                    'start_time': gunshot_start,
                    'end_time': gunshot_end,
                    'category': 'Gunshot',
                    'confidence': 0.75,  # Increased base confidence for explicit mentions
                    'description': f"Gunshot mentioned at {mention_time:.1f}s (transcript match)",
                    'intensity': 0.5
                })
                print(f"[GUNSHOT DETECTION] ⚠ Gunshot mentioned at {mention_time:.1f}s - Added as event despite no frequency anomaly")
        
    except Exception as e:
        print(f"[GUNSHOT DETECTION] ⚠ Error analyzing audio: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"[GUNSHOT DETECTION] ✓ Detected {len(gunshot_events)} gunshot events")
    return gunshot_events

