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
        
        # Format transcript for context
        transcript_context = f"""The following is a transcript from a video (file_id: {request.file_id}):
        
{transcript_text}

"""
        
        # If we have segments with timestamps, include them for better context
        if transcript_segments and len(transcript_segments) > 0:
            transcript_context += "Timestamps:\n"
            for seg in transcript_segments[:50]:  # Limit to first 50 segments to avoid token limits
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                text = seg.get("text", "")
                transcript_context += f"[{start:.1f}s - {end:.1f}s] {text}\n"
        
        # Build messages with system context
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful assistant that can answer questions about video transcripts. 
You have access to the full transcript of a video, including timestamps for each segment.
When answering questions, you can reference specific timestamps if relevant.
Be concise and helpful. If asked about something not in the transcript, say so clearly.

{transcript_context}"""
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

