import cv2
import numpy as np
from typing import List, Dict
import os

def extract_video_features(file_path: str) -> Dict:
    """
    Extract video features: motion, brightness, occlusion detection.
    Returns dictionary of features.
    """
    try:
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            return {
                "motion_spikes": [],
                "brightness_changes": [],
                "occlusion_detected": False,
                "frame_count": 0,
                "fps": 0,
                "duration": 0.0
            }
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        motion_values = []
        brightness_values = []
        prev_frame = None
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate brightness
            brightness = np.mean(gray)
            brightness_values.append(brightness)
            
            # Calculate motion (difference from previous frame)
            if prev_frame is not None:
                diff = cv2.absdiff(gray, prev_frame)
                motion = np.mean(diff)
                motion_values.append(motion)
            
            prev_frame = gray
            frame_idx += 1
            
            # Sample every 10th frame for performance
            if frame_idx % 10 != 0:
                continue
        
        cap.release()
        
        # Detect motion spikes
        motion_spikes = []
        if len(motion_values) > 0:
            motion_mean = np.mean(motion_values)
            motion_std = np.std(motion_values)
            threshold = motion_mean + 2 * motion_std
            
            for i, motion in enumerate(motion_values):
                if motion > threshold:
                    time_seconds = (i * 10) / fps if fps > 0 else 0
                    motion_spikes.append({
                        "time": time_seconds,
                        "intensity": float(motion)
                    })
        
        # Detect brightness changes
        brightness_changes = []
        if len(brightness_values) > 1:
            brightness_diff = np.diff(brightness_values)
            change_threshold = np.std(brightness_diff) * 2
            
            for i, diff in enumerate(brightness_diff):
                if abs(diff) > change_threshold:
                    time_seconds = (i * 10) / fps if fps > 0 else 0
                    brightness_changes.append({
                        "time": time_seconds,
                        "change": float(diff)
                    })
        
        return {
            "motion_spikes": motion_spikes,
            "brightness_changes": brightness_changes,
            "occlusion_detected": len(motion_spikes) > 5,  # Simple heuristic
            "frame_count": frame_count,
            "fps": fps,
            "duration": duration
        }
    
    except Exception as e:
        print(f"Video feature extraction error: {str(e)}")
        return {
            "motion_spikes": [],
            "brightness_changes": [],
            "occlusion_detected": False,
            "frame_count": 0,
            "fps": 0,
            "duration": 0.0
        }

def detect_video_events(video_features: Dict) -> List[Dict]:
    """
    Detect candidate video events based on features.
    Returns list of event candidates with timestamps.
    """
    events = []
    
    # Detect motion events
    for spike in video_features.get("motion_spikes", []):
        events.append({
            "type": "Motion",
            "start_time": max(0, spike["time"] - 1.0),
            "end_time": spike["time"] + 1.0,
            "confidence": min(0.9, spike["intensity"] / 50.0)
        })
    
    # Detect occlusion
    if video_features.get("occlusion_detected", False):
        events.append({
            "type": "Occlusion",
            "start_time": 0.0,
            "end_time": video_features.get("duration", 0.0),
            "confidence": 0.7
        })
    
    return events

