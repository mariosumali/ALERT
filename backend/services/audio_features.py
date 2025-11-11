import librosa
import numpy as np
from typing import List, Dict

def extract_audio_features(file_path: str) -> Dict:
    """
    Extract audio features: MFCCs, RMS energy, silence detection.
    Returns dictionary of features with temporal information.
    """
    try:
        # Load audio file
        y, sr = librosa.load(file_path, sr=None)
        duration = len(y) / sr
        
        # Extract RMS energy over time
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = np.mean(rms)
        rms_max = np.max(rms)
        rms_std = np.std(rms)
        
        # Calculate time for each frame
        # librosa.feature.rms uses default hop_length=512
        hop_length = 512
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)
        
        # Detect silence (energy below threshold)
        silence_threshold = 0.01
        silence_frames = np.where(rms < silence_threshold)[0]
        silence_ratio = len(silence_frames) / len(rms) if len(rms) > 0 else 0
        
        # Detect profanity (placeholder - would use actual profanity detection)
        # For now, return empty list
        profanity_detected = []
        
        return {
            "mfcc_mean": mfcc_mean.tolist(),
            "rms": rms.tolist(),
            "rms_times": times.tolist(),
            "rms_mean": float(rms_mean),
            "rms_max": float(rms_max),
            "rms_std": float(rms_std),
            "silence_ratio": float(silence_ratio),
            "duration": float(duration),
            "profanity_detected": profanity_detected,
            "sample_rate": sr
        }
    
    except Exception as e:
        print(f"Audio feature extraction error: {str(e)}")
        return {
            "mfcc_mean": [],
            "rms": [],
            "rms_times": [],
            "rms_mean": 0.0,
            "rms_max": 0.0,
            "rms_std": 0.0,
            "silence_ratio": 0.0,
            "duration": 0.0,
            "profanity_detected": [],
            "sample_rate": 22050
        }

def detect_audio_events(audio_features: Dict, transcript: str) -> List[Dict]:
    """
    Detect candidate audio events based on temporal features.
    Returns list of event candidates with timestamps.
    """
    events = []
    
    rms = np.array(audio_features.get("rms", []))
    rms_times = np.array(audio_features.get("rms_times", []))
    duration = audio_features.get("duration", 0.0)
    rms_mean = audio_features.get("rms_mean", 0.0)
    rms_std = audio_features.get("rms_std", 0.0)
    rms_max = audio_features.get("rms_max", 0.0)
    
    if len(rms) == 0 or duration == 0:
        return events
    
    # Detect silence periods (low energy for extended duration)
    silence_threshold = max(0.01, rms_mean * 0.3)
    silence_window_size = 2.0  # seconds
    silence_min_duration = 3.0  # minimum silence duration to be considered an event
    
    silence_start = None
    for i, (time, energy) in enumerate(zip(rms_times, rms)):
        if energy < silence_threshold:
            if silence_start is None:
                silence_start = time
        else:
            if silence_start is not None:
                silence_duration = time - silence_start
                if silence_duration >= silence_min_duration:
                    events.append({
                        "type": "Silence",
                        "start_time": max(0.0, silence_start - 0.5),
                        "end_time": min(duration, time + 0.5),
                        "confidence": min(0.9, 0.5 + silence_duration / 10.0),
                        "description": f"Extended silence period ({silence_duration:.1f}s)"
                    })
                silence_start = None
    
    # Check if silence extends to end of file
    if silence_start is not None:
        silence_duration = duration - silence_start
        if silence_duration >= silence_min_duration:
            events.append({
                "type": "Silence",
                "start_time": max(0.0, silence_start - 0.5),
                "end_time": duration,
                "confidence": min(0.9, 0.5 + silence_duration / 10.0),
                "description": f"Extended silence period ({silence_duration:.1f}s)"
            })
    
    # Detect high energy spikes (potential gunshots, yelling, loud noises)
    high_energy_threshold = rms_mean + 2 * rms_std
    if high_energy_threshold < 0.1:  # Fallback if std is too low
        high_energy_threshold = rms_max * 0.7
    
    spike_window = 1.0  # seconds around spike
    for i, (time, energy) in enumerate(zip(rms_times, rms)):
        if energy > high_energy_threshold:
            # Check if this is a local maximum (not just part of a sustained high energy)
            is_local_max = True
            window_size = max(1, int(0.5 / (rms_times[1] - rms_times[0])) if len(rms_times) > 1 else 1)
            for j in range(max(0, i - window_size), min(len(rms), i + window_size + 1)):
                if j != i and rms[j] >= energy:
                    is_local_max = False
                    break
            
            if is_local_max:
                events.append({
                    "type": "HighEnergy",
                    "start_time": max(0.0, time - spike_window),
                    "end_time": min(duration, time + spike_window),
                    "confidence": min(0.95, 0.6 + (energy - high_energy_threshold) / (rms_max - high_energy_threshold + 0.1)),
                    "description": f"Sudden loud noise detected (energy: {energy:.3f})"
                })
    
    # Detect sudden energy changes (may indicate events)
    if len(rms) > 1:
        energy_changes = np.diff(rms)
        change_threshold = rms_std * 1.5
        for i, change in enumerate(energy_changes):
            if abs(change) > change_threshold:
                time = rms_times[i]
                events.append({
                    "type": "EnergyChange",
                    "start_time": max(0.0, time - 0.5),
                    "end_time": min(duration, time + 0.5),
                    "confidence": min(0.8, 0.5 + abs(change) / (rms_std * 2)),
                    "description": f"Sudden energy {'increase' if change > 0 else 'decrease'}"
                })
    
    return events

