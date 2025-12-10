"""
Service for extracting frames from videos at specific timestamps.
"""

import cv2
import numpy as np
from typing import List, Optional
import base64
import io


def extract_frame_at_timestamp(video_path: str, timestamp_seconds: float) -> Optional[bytes]:
    """
    Extract a single frame from a video at the specified timestamp.
    
    Args:
        video_path: Path to the video file
        timestamp_seconds: Timestamp in seconds to extract the frame
        
    Returns:
        JPEG image bytes, or None if extraction fails
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Failed to open video: {video_path}")
            return None
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # Validate timestamp
        if timestamp_seconds < 0 or timestamp_seconds > duration:
            print(f"Timestamp {timestamp_seconds}s is out of range (0-{duration}s)")
            cap.release()
            return None
        
        # Calculate frame number
        frame_number = int(timestamp_seconds * fps)
        
        # Seek to the frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        # Read the frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            print(f"Failed to read frame at {timestamp_seconds}s")
            return None
        
        # Encode frame as JPEG
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        if not success:
            print(f"Failed to encode frame at {timestamp_seconds}s")
            return None
        
        return buffer.tobytes()
    
    except Exception as e:
        print(f"Error extracting frame at {timestamp_seconds}s: {str(e)}")
        return None


def extract_multiple_frames(video_path: str, timestamps: List[float]) -> List[Optional[bytes]]:
    """
    Extract multiple frames from a video at the specified timestamps.
    
    Args:
        video_path: Path to the video file
        timestamps: List of timestamps in seconds
        
    Returns:
        List of JPEG image bytes (None for failed extractions)
    """
    frames = []
    for timestamp in timestamps:
        frame = extract_frame_at_timestamp(video_path, timestamp)
        frames.append(frame)
    
    return frames


def frame_to_base64(frame_bytes: bytes) -> str:
    """
    Convert frame bytes to base64 string for API transmission.
    
    Args:
        frame_bytes: JPEG image bytes
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(frame_bytes).decode('utf-8')
