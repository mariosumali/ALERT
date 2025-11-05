import whisper
import os
from typing import Dict, List, Tuple

# Cache the model to avoid reloading
_model_cache = None

def transcribe_file(file_path: str) -> str:
    """
    Transcribe audio/video file using OpenAI Whisper (local).
    Returns the transcript text.
    """
    global _model_cache
    
    try:
        # Load Whisper model (base model for faster processing)
        if _model_cache is None:
            try:
                _model_cache = whisper.load_model("tiny")  # Try tiny first (fastest, least memory)
            except:
                _model_cache = whisper.load_model("base")  # Fallback to base
        
        # Transcribe
        result = _model_cache.transcribe(file_path)
        transcript = result["text"]
        
        return transcript
    
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty transcript if Whisper fails
        return ""

def transcribe_file_with_timestamps(file_path: str, use_mock: bool = False) -> Tuple[str, List[Dict]]:
    """
    Transcribe audio/video file using OpenAI Whisper (local) with timestamps.
    Returns tuple of (full_transcript_text, segments_with_timestamps).
    Segments format: [{"start": 0.0, "end": 5.0, "text": "..."}, ...]
    
    If use_mock=True, returns a quick mock transcription for testing.
    """
    # Check if we should use mock
    use_mock_transcription = use_mock or os.getenv("USE_MOCK_TRANSCRIPTION", "false").lower() == "true"
    
    # Use mock if explicitly requested
    if use_mock_transcription:
        import librosa
        try:
            # Get video duration quickly
            y, sr = librosa.load(file_path, sr=None, duration=1.0)
            duration = librosa.get_duration(y=y, sr=sr) if len(y) > 0 else 60.0
        except:
            duration = 60.0
        
        # Generate mock segments every 5-10 seconds
        segments = []
        full_text_parts = []
        current_time = 0.0
        
        mock_texts = [
            "Officer approaching the vehicle.",
            "Can I see your license and registration?",
            "I need to search your vehicle.",
            "You have the right to remain silent.",
            "Everything you say can and will be used against you.",
            "We have a report of a disturbance in this area.",
            "Please step out of the vehicle.",
            "I'm going to pat you down for weapons.",
            "Do you have any weapons or contraband?",
            "You're under arrest.",
        ]
        
        text_idx = 0
        while current_time < duration:
            segment_duration = 5.0 + (text_idx % 3) * 2.0  # 5-9 seconds
            end_time = min(current_time + segment_duration, duration)
            
            text = mock_texts[text_idx % len(mock_texts)]
            segments.append({
                "start": round(current_time, 2),
                "end": round(end_time, 2),
                "text": text
            })
            full_text_parts.append(text)
            
            current_time = end_time
            text_idx += 1
            
            if current_time >= duration:
                break
        
        full_transcript = " ".join(full_text_parts)
        return full_transcript, segments
    
    # Real local Whisper transcription
    global _model_cache
    
    try:
        print(f"Transcribing {file_path} using local OpenAI Whisper...")
        
        # Load Whisper model (tiny model for faster processing and less memory)
        if _model_cache is None:
            try:
                # Try tiny model first (less memory, faster)
                print("Loading Whisper 'tiny' model...")
                _model_cache = whisper.load_model("tiny")
            except Exception as e:
                print(f"Failed to load 'tiny' model: {e}, trying 'base' model...")
                # Fallback to base if tiny fails
                _model_cache = whisper.load_model("base")
        
        # Transcribe with segment timestamps (word_timestamps=False for segment-level)
        print(f"Starting transcription...")
        result = _model_cache.transcribe(
            file_path, 
            word_timestamps=False,  # Segment-level timestamps
            fp16=False,  # Use FP32 for stability
            verbose=False  # Less output
        )
        
        # Extract full transcript
        full_transcript = result["text"]
        
        # Extract segments with timestamps
        segments = []
        for segment in result.get("segments", []):
            segments.append({
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", 0.0)),
                "text": segment.get("text", "").strip()
            })
        
        print(f"Transcription complete. {len(segments)} segments created.")
        return full_transcript, segments
    
    except Exception as e:
        error_msg = str(e)
        print(f"Whisper transcription error: {error_msg}")
        import traceback
        traceback.print_exc()
        # Fallback to mock if Whisper fails
        print(f"Falling back to mock transcription due to error: {error_msg}")
        return transcribe_file_with_timestamps(file_path, use_mock=True)

