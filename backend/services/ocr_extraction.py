"""
OCR extraction service for reading text from video frames.
Extracts metadata from body cam overlays (timestamps, device IDs, etc.) using GPT-4o.
"""
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import base64
import os
import json
from openai import OpenAI


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def analyze_frame_with_gpt4o(frame: np.ndarray) -> Dict:
    """
    Use GPT-4o to analyze a frame and extract metadata.
    """
    client = _get_openai_client()
    if not client:
        print("[OCR] OpenAI API key not found, skipping GPT-4o analysis")
        return {}

    try:
        print("[OCR] 🤖 invoking GPT-4o for enhanced metadata extraction...")
        # Encode frame to base64
        # Resize if too large to save tokens/bandwidth, though 720p is usually fine
        _, buffer = cv2.imencode('.jpg', frame)
        base64_image = base64.b64encode(buffer).decode('utf-8')

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts metadata from body camera footage. Return ONLY a JSON object."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract the following metadata from this body camera frame: Timestamp (YYYY-MM-DD HH:MM:SS), Device ID, Device Model, Badge Number. Return a JSON object with keys: timestamp, device_id, device_model, badge_number. If a field is not visible, set it to null. The timestamp is usually at the top right. Device ID often starts with X."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.0
        )
        
        content = response.choices[0].message.content
        # Clean up markdown code blocks if present
        content = content.replace("```json", "").replace("```", "").strip()
        
        print(f"[OCR] GPT-4o raw response: {content}")
        return json.loads(content)
    except Exception as e:
        print(f"[OCR] GPT-4o analysis failed: {e}")
        return {}


def extract_frame_for_ocr(video_path: str, frame_number: int = 30) -> Optional[np.ndarray]:
    """
    Extract a specific frame from video for OCR processing.
    
    Args:
        video_path: Path to video file
        frame_number: Frame number to extract (default: 30, ~1 second at 30fps)
    
    Returns:
        Frame as numpy array, or None if extraction fails
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"[OCR] Failed to open video file: {video_path}")
            return None
            
        # Get total frames to ensure we don't go out of bounds
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_number >= total_frames:
            print(f"[OCR] Frame {frame_number} is out of bounds (total: {total_frames}). Using frame 0.")
            frame_number = 0
            
        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        # Read frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            print(f"[OCR] Failed to extract frame {frame_number}")
            return None
        
        print(f"[OCR] ✓ Extracted frame {frame_number}, size: {frame.shape}")
        return frame
        
    except Exception as e:
        print(f"[OCR] Error extracting frame: {e}")
        return None


def _extract_and_analyze(video_path: str, frame_num: int) -> Dict:
    """Extract a single frame and send it to GPT-4o. Thread-safe."""
    frame = extract_frame_for_ocr(video_path, frame_num)
    if frame is None:
        return {}
    return analyze_frame_with_gpt4o(frame)


def extract_metadata_from_video(video_path: str, frames_to_try: List[int] = [30, 60, 120]) -> Dict:
    """
    Extract metadata from video using GPT-4o.
    Sends all frame analyses in parallel for speed.
    """
    best_metadata: Dict = {
        "raw_text": "",
        "timestamp": None,
        "device_id": None,
        "device_model": None,
        "badge_number": None,
        "officer_id": None,
    }

    print(f"[OCR] Analyzing {len(frames_to_try)} frames in parallel...")

    with ThreadPoolExecutor(max_workers=len(frames_to_try)) as executor:
        futures = {
            executor.submit(_extract_and_analyze, video_path, fn): fn
            for fn in frames_to_try
        }
        for future in as_completed(futures):
            frame_num = futures[future]
            try:
                metadata = future.result()
                if metadata:
                    for key, value in metadata.items():
                        if value and not best_metadata.get(key):
                            best_metadata[key] = value
            except Exception as e:
                print(f"[OCR] ⚠ Frame {frame_num} analysis failed: {e}")

    print(f"[OCR] Final metadata extraction results:")
    for k, v in best_metadata.items():
        if k != "raw_text" and v:
            print(f"[OCR]   {k}: {v}")

    return best_metadata
