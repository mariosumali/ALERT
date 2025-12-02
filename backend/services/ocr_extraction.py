"""
OCR extraction service for reading text from video frames.
Extracts metadata from body cam overlays (timestamps, device IDs, etc.)
"""
import cv2
import pytesseract
import numpy as np
from typing import Dict, Optional, Tuple
import re
from datetime import datetime


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


def preprocess_frame_for_ocr(frame: np.ndarray, region: str = "top-right") -> np.ndarray:
    """
    Preprocess frame to improve OCR accuracy.
    Focuses on the region where body cam overlays typically appear.
    
    Args:
        frame: Input frame
        region: Region to focus on ("top-right", "top-left", "full")
    
    Returns:
        Preprocessed frame
    """
    height, width = frame.shape[:2]
    
    # Extract region of interest (body cam overlays are usually top corners)
    if region == "top-right":
        # Top-right quarter
        roi = frame[0:int(height*0.15), int(width*0.6):width]
    elif region == "top-left":
        # Top-left quarter
        roi = frame[0:int(height*0.15), 0:int(width*0.4)]
    elif region == "top":
        # Top section
        roi = frame[0:int(height*0.15), :]
    else:
        roi = frame
    
    # Convert to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to improve OCR (white text on dark background or vice versa)
    # Try adaptive thresholding first
    processed = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Optionally apply morphological operations to clean up
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
    
    return processed


def extract_text_from_frame(frame: np.ndarray, region: str = "top") -> str:
    """
    Use Tesseract OCR to extract text from frame.
    
    Args:
        frame: Input frame (numpy array)
        region: Region to process ("top-right", "top-left", "top", "full")
    
    Returns:
        Extracted text string
    """
    try:
        # Preprocess frame
        processed = preprocess_frame_for_ocr(frame, region=region)
        
        # Configure Tesseract for better accuracy with overlay text
        # --oem 3: Use default OCR Engine Mode (LSTM)
        # --psm 6: Assume uniform block of text
        custom_config = r'--oem 3 --psm 6'
        
        # Extract text
        text = pytesseract.image_to_string(processed, config=custom_config)
        
        # Clean up extracted text
        text = text.strip()
        
        print(f"[OCR] Extracted text ({len(text)} chars): {text[:100]}...")
        return text
        
    except Exception as e:
        print(f"[OCR] Error during text extraction: {e}")
        return ""


def parse_bodycam_metadata(ocr_text: str) -> Dict:
    """
    Parse body cam specific metadata from OCR text.
    
    Extracts:
    - Timestamp (various formats)
    - Device model/ID
    - Badge/Officer ID
    - Other identifiers
    
    Args:
        ocr_text: Raw OCR text output
    
    Returns:
        Dictionary of parsed metadata
    """
    metadata = {
        "raw_text": ocr_text,
        "timestamp": None,
        "device_id": None,
        "device_model": None,
        "badge_number": None,
        "officer_id": None,
    }
    
    if not ocr_text:
        return metadata
    
    # Extract timestamp (multiple formats)
    # Format 1: 2019-05-04 T19:49:09Z
    # Format 2: 2019-05-04T19:49:09Z
    # Format 3: 05/04/2019 19:49:09
    timestamp_patterns = [
        r'(\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}[Z]?)',  # ISO-like
        r'(\d{2}[-/]\d{2}[-/]\d{4}\s+\d{2}:\d{2}:\d{2})',  # US format
        r'(\d{4}\d{2}\d{2}\s+\d{2}:\d{2}:\d{2})',  # Compact format
    ]
    
    for pattern in timestamp_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            timestamp_str = match.group(1).strip()
            # Normalize: replace 'T ' with 'T'
            timestamp_str = timestamp_str.replace('T ', 'T')
            metadata["timestamp"] = timestamp_str
            print(f"[OCR] Found timestamp: {timestamp_str}")
            break
    
    # Extract device ID (e.g., X81264585, serial numbers)
    device_id_pattern = r'\b([A-Z]\d{7,10})\b'
    match = re.search(device_id_pattern, ocr_text)
    if match:
        metadata["device_id"] = match.group(1)
        print(f"[OCR] Found device ID: {metadata['device_id']}")
    
    # Extract device model (e.g., "AXON BODY 2", "GoPro")
    device_models = [
        r'(AXON\s+BODY\s+\d+)',
        r'(AXON\s+[A-Z]+\s+\d+)',
        r'(GoPro\s+[A-Z0-9]+)',
        r'(Body\s+Camera\s+[A-Z0-9]+)',
    ]
    
    for pattern in device_models:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            metadata["device_model"] = match.group(1).strip()
            print(f"[OCR] Found device model: {metadata['device_model']}")
            break
    
    # Extract badge number (various formats)
    badge_patterns = [
        r'(?:Badge|ID|Officer)[\s:#]*(\d{3,6})',
        r'\bBadge\s+(\d{3,6})\b',
        r'\b(\d{4,6})\b(?:\s+Badge)',
    ]
    
    for pattern in badge_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            metadata["badge_number"] = match.group(1)
            print(f"[OCR] Found badge number: {metadata['badge_number']}")
            break
    
    return metadata


def extract_metadata_from_video(video_path: str, frames_to_try: list = [10, 30, 60, 120]) -> Dict:
    """
    Extract metadata from video by trying multiple frames and regions.
    
    Args:
        video_path: Path to video file
        frames_to_try: List of frame numbers to try
    
    Returns:
        Best metadata found across all frames
    """
    best_metadata = None
    max_info_count = 0
    
    for frame_num in frames_to_try:
        print(f"[OCR] Trying frame {frame_num}...")
        
        # Extract frame
        frame = extract_frame_for_ocr(video_path, frame_num)
        if frame is None:
            continue
        
        # Try different regions
        for region in ["top", "top-right"]:
            text = extract_text_from_frame(frame, region=region)
            if not text:
                continue
            
            # Parse metadata
            metadata = parse_bodycam_metadata(text)
            
            # Count how much info we extracted (non-None and not raw_text)
            info_count = sum(1 for k, v in metadata.items() if k != "raw_text" and v is not None)
            
            if info_count > max_info_count:
                max_info_count = info_count
                best_metadata = metadata
                print(f"[OCR] New best: {info_count} fields extracted from frame {frame_num}, region {region}")
        
        # If we found good metadata, stop early
        if max_info_count >= 3:  # timestamp + device info + one more field
            break
    
    if best_metadata:
        print(f"[OCR] ✓ Final metadata: {max_info_count} fields extracted")
        return best_metadata
    else:
        print(f"[OCR] ⚠ No metadata extracted from any frame")
        return {
            "raw_text": "",
            "timestamp": None,
            "device_id": None,
            "device_model": None,
            "badge_number": None,
            "officer_id": None,
        }
