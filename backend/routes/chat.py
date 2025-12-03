from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from models.database import SessionLocal
from models.schema import FileMetadata
from openai import OpenAI
import os
import json

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    file_id: str
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    message: ChatMessage
    usage: Optional[dict] = None


def _get_openai_client():
    """Get or create OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    return OpenAI(api_key=api_key)


@router.post("/chat", response_model=ChatResponse)
async def chat_with_transcript(request: ChatRequest):
    """
    Chat with GPT using the video transcript as context.
    Automatically includes the transcript in the system message.
    """
    db = SessionLocal()
    try:
        # Get file and transcript from database
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == request.file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_metadata.transcript:
            raise HTTPException(status_code=400, detail="No transcript available for this file. Please transcribe the video first.")
        
        # Prepare transcript context
        transcript_text = file_metadata.transcript
        transcript_segments = file_metadata.transcript_segments or []
        
        # If transcript_segments is a JSON string, parse it
        if isinstance(transcript_segments, str):
            try:
                transcript_segments = json.loads(transcript_segments)
            except:
                transcript_segments = []
        
        # Format video metadata
        duration = file_metadata.duration or 0.0
        file_size = file_metadata.file_size or 0
        file_type = file_metadata.file_type or "unknown"
        original_filename = file_metadata.original_filename or "unknown"
        timestamp_start = file_metadata.timestamp_start
        
        # Format duration as MM:SS
        duration_minutes = int(duration // 60)
        duration_seconds = int(duration % 60)
        duration_formatted = f"{duration_minutes}:{duration_seconds:02d}"
        
        # Format file size
        file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
        file_size_gb = file_size_mb / 1024 if file_size_mb >= 1024 else 0
        if file_size_gb >= 1:
            file_size_str = f"{file_size_gb:.2f} GB"
        elif file_size_mb >= 1:
            file_size_str = f"{file_size_mb:.2f} MB"
        else:
            file_size_kb = file_size / 1024 if file_size > 0 else 0
            file_size_str = f"{file_size_kb:.2f} KB"
        
        # Format timestamp
        timestamp_str = ""
        if timestamp_start:
            timestamp_str = timestamp_start.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Format transcript for context
        transcript_context = f"""The following is a transcript from a video (file_id: {request.file_id}):
        
{transcript_text}

"""
        
        # Add video metadata
        metadata_context = f"""Video Metadata:
- Duration: {duration_formatted} ({duration:.2f} seconds)
- File Type: {file_type}
- File Size: {file_size_str}
- Original Filename: {original_filename}"""
        
        if timestamp_str:
            metadata_context += f"\n- Uploaded: {timestamp_str}"
        
        metadata_context += "\n"
        
        # If we have segments with timestamps, include them for better context
        if transcript_segments and len(transcript_segments) > 0:
            transcript_context += "Transcript Timestamps:\n"
            for seg in transcript_segments[:50]:  # Limit to first 50 segments to avoid token limits
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                text = seg.get("text", "")
                transcript_context += f"[{start:.1f}s - {end:.1f}s] {text}\n"
        
        # Get detected moments (events) from database
        from models.schema import MomentOfInterest
        moments = db.query(MomentOfInterest).filter(MomentOfInterest.file_id == request.file_id).all()
        
        moments_context = ""
        if moments:
            moments_context = f"\n\nDetected Events ({len(moments)} total):\n"
            moments_context += "The following events were automatically detected in the video:\n\n"
            
            for moment in moments:
                event_types = moment.event_types if moment.event_types else ["Unknown"]
                event_type_str = ", ".join(event_types)
                
                # Format time as MM:SS
                start_mins = int(moment.start_time // 60)
                start_secs = int(moment.start_time % 60)
                end_mins = int(moment.end_time // 60)
                end_secs = int(moment.end_time % 60)
                time_str = f"{start_mins}:{start_secs:02d} - {end_mins}:{end_secs:02d}"
                
                confidence_pct = int(moment.interest_score * 100)
                
                moments_context += f"- [{event_type_str}] at {time_str} ({moment.start_time:.1f}s-{moment.end_time:.1f}s)"
                moments_context += f" [Confidence: {confidence_pct}%]\n"
                if moment.description:
                    moments_context += f"  Description: {moment.description}\n"
                moments_context += "\n"
        
        # Get OCR metadata if available
        ocr_context = ""
        if file_metadata.ocr_metadata:
            ocr_metadata = file_metadata.ocr_metadata
            # If ocr_metadata is a JSON string, parse it
            if isinstance(ocr_metadata, str):
                try:
                    ocr_metadata = json.loads(ocr_metadata)
                except:
                    ocr_metadata = {}
            
            if ocr_metadata and any(v for k, v in ocr_metadata.items() if k != "raw_text" and v):
                ocr_context = "\n\nOCR Extracted Metadata:\n"
                ocr_context += "The following information was extracted from video frames using OCR:\n\n"
                
                if ocr_metadata.get("timestamp"):
                    ocr_context += f"- Timestamp: {ocr_metadata['timestamp']}\n"
                if ocr_metadata.get("device_id"):
                    ocr_context += f"- Device ID: {ocr_metadata['device_id']}\n"
                if ocr_metadata.get("device_model"):
                    ocr_context += f"- Device Model: {ocr_metadata['device_model']}\n"
                if ocr_metadata.get("badge_number"):
                    ocr_context += f"- Badge Number: {ocr_metadata['badge_number']}\n"
                if ocr_metadata.get("officer_id"):
                    ocr_context += f"- Officer ID: {ocr_metadata['officer_id']}\n"
                if ocr_metadata.get("raw_text"):
                    ocr_context += f"- Raw OCR Text: {ocr_metadata['raw_text'][:500]}"  # Limit to first 500 chars
                    if len(ocr_metadata.get("raw_text", "")) > 500:
                        ocr_context += "...\n"
                    else:
                        ocr_context += "\n"
                ocr_context += "\n"
        
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful assistant that can answer questions about video transcripts. 
You have access to:
1. The full transcript of a video, including timestamps for each segment
2. Video metadata
3. Automatically detected events (such as **Gunshots**, loud sounds, silences, and audio anomalies)
4. OCR extracted metadata from video frames (timestamps, device information, etc.)

When answering questions:
- Reference specific timestamps when relevant (format: MM:SS or seconds)
- When asked about events or moments, reference the detected events provided. **Pay special attention to Gunshot events.**
- When asked about device information, timestamps, or metadata visible in the video, use the OCR extracted metadata.
- If asked about "shots fired" or "shootings", look for both "Gunshot" events and mentions in the transcript.
- Be concise and helpful
- If asked about something not in the transcript, events, or OCR metadata, say so clearly

{metadata_context}
{transcript_context}{moments_context}{ocr_context}"""
            }
        ]
        
        # Add user messages (converting from request format)
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        try:
            client = _get_openai_client()
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.7,
            )
            
            assistant_message = response.choices[0].message
            
            return ChatResponse(
                message=ChatMessage(
                    role=assistant_message.role,
                    content=assistant_message.content
                ),
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calling OpenAI API: {str(e)}")
    finally:
        db.close()

