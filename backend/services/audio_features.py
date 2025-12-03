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


