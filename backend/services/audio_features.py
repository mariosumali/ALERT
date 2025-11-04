import librosa
import numpy as np
from typing import List, Dict

def extract_audio_features(file_path: str) -> Dict:
    """
    Extract audio features: MFCCs, RMS energy, silence detection.
    Returns dictionary of features.
    """
    try:
        # Load audio file
        y, sr = librosa.load(file_path, sr=None)
        
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)
        
        # Extract RMS energy
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = np.mean(rms)
        rms_max = np.max(rms)
        
        # Detect silence (energy below threshold)
        silence_threshold = 0.01
        silence_frames = np.where(rms < silence_threshold)[0]
        silence_ratio = len(silence_frames) / len(rms) if len(rms) > 0 else 0
        
        # Detect profanity (placeholder - would use actual profanity detection)
        # For now, return empty list
        profanity_detected = []
        
        return {
            "mfcc_mean": mfcc_mean.tolist(),
            "rms_mean": float(rms_mean),
            "rms_max": float(rms_max),
            "silence_ratio": float(silence_ratio),
            "duration": len(y) / sr,
            "profanity_detected": profanity_detected
        }
    
    except Exception as e:
        print(f"Audio feature extraction error: {str(e)}")
        return {
            "mfcc_mean": [],
            "rms_mean": 0.0,
            "rms_max": 0.0,
            "silence_ratio": 0.0,
            "duration": 0.0,
            "profanity_detected": []
        }

def detect_audio_events(audio_features: Dict, transcript: str) -> List[Dict]:
    """
    Detect candidate audio events based on features.
    Returns list of event candidates with timestamps.
    """
    events = []
    
    # Example: Detect silence events
    if audio_features.get("silence_ratio", 0) > 0.3:
        events.append({
            "type": "Silence",
            "start_time": 0.0,
            "end_time": audio_features.get("duration", 0.0),
            "confidence": 0.7
        })
    
    # Example: Detect high energy events (potential gunshots/yelling)
    if audio_features.get("rms_max", 0) > 0.5:
        duration = audio_features.get("duration", 0.0)
        events.append({
            "type": "HighEnergy",
            "start_time": 0.0,
            "end_time": min(5.0, duration),
            "confidence": 0.6
        })
    
    return events

