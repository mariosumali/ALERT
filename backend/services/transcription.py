import whisper
import os

# Cache the model to avoid reloading
_model_cache = None

def transcribe_file(file_path: str) -> str:
    """
    Transcribe audio/video file using OpenAI Whisper.
    Returns the transcript text.
    """
    global _model_cache
    
    try:
        # Load Whisper model (base model for faster processing)
        if _model_cache is None:
            _model_cache = whisper.load_model("base")
        
        # Transcribe
        result = _model_cache.transcribe(file_path)
        transcript = result["text"]
        
        return transcript
    
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        # Return empty transcript if Whisper fails
        return ""

