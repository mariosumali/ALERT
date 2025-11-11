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
    duration = video_features.get("duration", 0.0)
    motion_spikes = video_features.get("motion_spikes", [])
    brightness_changes = video_features.get("brightness_changes", [])
    occlusion_detected = video_features.get("occlusion_detected", False)
    
    if duration == 0:
        return events
    
    # Detect motion events with better temporal grouping
    if len(motion_spikes) > 0:
        # Group nearby motion spikes together
        motion_spikes_sorted = sorted(motion_spikes, key=lambda x: x["time"])
        motion_groups = []
        current_group = [motion_spikes_sorted[0]]
        
        for spike in motion_spikes_sorted[1:]:
            # If within 2 seconds of previous spike, group together
            if spike["time"] - current_group[-1]["time"] < 2.0:
                current_group.append(spike)
            else:
                motion_groups.append(current_group)
                current_group = [spike]
        motion_groups.append(current_group)
        
        # Create events for each motion group
        for group in motion_groups:
            if len(group) > 0:
                start_time = max(0.0, group[0]["time"] - 1.0)
                end_time = min(duration, group[-1]["time"] + 1.0)
                max_intensity = max(spike["intensity"] for spike in group)
                avg_intensity = sum(spike["intensity"] for spike in group) / len(group)
                
                # Calculate confidence based on intensity and number of spikes
                intensity_score = min(0.9, max_intensity / 50.0)
                group_score = min(0.3, len(group) * 0.1)
                confidence = min(0.95, intensity_score + group_score)
                
                events.append({
                    "type": "Motion",
                    "start_time": start_time,
                    "end_time": end_time,
                    "confidence": confidence,
                    "description": f"Motion spike detected ({len(group)} spikes, intensity: {max_intensity:.1f})"
                })
    
    # Detect significant brightness changes (may indicate camera adjustments, flashes, etc.)
    significant_brightness_changes = [
        change for change in brightness_changes 
        if abs(change["change"]) > 30  # Threshold for significant change
    ]
    
    if len(significant_brightness_changes) > 0:
        # Group nearby brightness changes
        brightness_groups = []
        current_group = [significant_brightness_changes[0]]
        
        for change in significant_brightness_changes[1:]:
            if change["time"] - current_group[-1]["time"] < 3.0:
                current_group.append(change)
            else:
                brightness_groups.append(current_group)
                current_group = [change]
        brightness_groups.append(current_group)
        
        for group in brightness_groups:
            if len(group) > 0:
                start_time = max(0.0, group[0]["time"] - 0.5)
                end_time = min(duration, group[-1]["time"] + 0.5)
                max_change = max(abs(c["change"]) for c in group)
                
                events.append({
                    "type": "BrightnessChange",
                    "start_time": start_time,
                    "end_time": end_time,
                    "confidence": min(0.85, 0.5 + max_change / 100.0),
                    "description": f"Significant brightness change detected ({max_change:.1f})"
                })
    
    # Detect occlusion (if multiple motion spikes indicate potential camera obstruction)
    if occlusion_detected and len(motion_spikes) > 5:
        # Find the time range where occlusion is most likely
        occlusion_start = max(0.0, min(spike["time"] for spike in motion_spikes) - 1.0)
        occlusion_end = min(duration, max(spike["time"] for spike in motion_spikes) + 1.0)
        
        events.append({
            "type": "Occlusion",
            "start_time": occlusion_start,
            "end_time": occlusion_end,
            "confidence": min(0.8, 0.5 + len(motion_spikes) / 20.0),
            "description": f"Potential camera occlusion detected ({len(motion_spikes)} motion spikes)"
        })
    
    return events

