from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from models.database import SessionLocal
from models.schema import FileMetadata, VideoSegmentMetadata
from openai import OpenAI
import os
import json
import hashlib
from services.frame_extraction import extract_frame_at_timestamp, frame_to_base64
from services.gemini_client import is_gemini_enabled, ask_gemini_about_video
from services.video_chunking import (
    extract_segment,
    make_segment_path,
    seconds_to_timestamp,
    timestamp_to_seconds,
)
from utils.timestamp_parser import parse_timestamps, format_timestamp

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    file_id: str
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    message: ChatMessage
    usage: Optional[dict] = None
    visual_analysis_used: Optional[bool] = False
    analyzed_timestamps: Optional[List[float]] = None
    gemini_segments_analyzed: Optional[List[str]] = None


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    return OpenAI(api_key=api_key)


# ── Tool definitions for the agentic loop ────────────────────────────────

AGENTIC_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ask_gemini_on_segment",
            "description": "Ask Gemini a visual question about a specific video segment (max 5 minutes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The visual question to ask about the segment."},
                    "start_time": {"type": "string", "description": "Segment start in mm:ss format."},
                    "end_time": {"type": "string", "description": "Segment end in mm:ss format."},
                },
                "required": ["question", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Return the final answer to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "The final answer."},
                },
                "required": ["answer"],
            },
        },
    },
]


def _build_system_prompt(
    file_metadata: FileMetadata,
    transcript_context: str,
    moments_context: str,
    segment_metadata_context: str,
    ocr_context: str,
    use_agentic: bool,
) -> str:
    duration = file_metadata.duration or 0.0
    duration_formatted = f"{int(duration // 60)}:{int(duration % 60):02d}"
    file_size = file_metadata.file_size or 0
    file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0

    metadata_section = (
        f"Video Metadata:\n"
        f"- Duration: {duration_formatted} ({duration:.2f} seconds)\n"
        f"- File Type: {file_metadata.file_type}\n"
        f"- File Size: {file_size_mb:.2f} MB\n"
        f"- Original Filename: {file_metadata.original_filename or 'unknown'}\n"
    )

    base_prompt = f"""You are an investigative AI assistant that answers questions about body camera / dash cam footage.
You have access to:
1. The full transcript with timestamps
2. Video metadata
3. Automatically detected events (Gunshots, loud sounds, silences, audio anomalies, use-of-force, etc.)
4. OCR extracted metadata from video frames
5. Rich per-segment video analysis metadata (scene type, lighting, people counts, force events, key moments)

When answering:
- Reference specific timestamps (format: MM:SS or seconds)
- When asked about events, reference the detected events. Pay special attention to Gunshot and UseOfForce events.
- When asked about device info, timestamps, or visible metadata, use OCR data.
- Use segment metadata for visual scene questions (lighting, weather, people counts, camera motion, force).
- Be concise and helpful.
- If asked about something not in the available data, say so clearly.

{metadata_section}
{transcript_context}{moments_context}{segment_metadata_context}{ocr_context}"""

    if use_agentic:
        base_prompt += """

AGENTIC MODE: You also have a tool `ask_gemini_on_segment` to visually inspect specific video segments with Gemini.
Policy:
- First, check the metadata and transcript; if sufficient, call finish(answer).
- If the answer requires visual verification or the metadata is insufficient, call ask_gemini_on_segment(question, start_time, end_time) with a targeted question and a segment of max 5 minutes.
- After receiving Gemini's response, synthesize and call finish(answer).
- Always explain your reasoning briefly BEFORE making a tool call.
- Do NOT call Gemini more than 3 times total."""

    return base_prompt


def _build_segment_metadata_context(db, file_id: str) -> str:
    segments = (
        db.query(VideoSegmentMetadata)
        .filter(VideoSegmentMetadata.file_id == file_id)
        .order_by(VideoSegmentMetadata.segment_idx)
        .all()
    )
    if not segments:
        return ""

    ctx = f"\n\nVideo Segment Analysis ({len(segments)} segments):\n"
    for seg in segments:
        start_ts = seconds_to_timestamp(seg.start_sec)
        end_ts = seconds_to_timestamp(seg.end_sec)
        ctx += f"\n--- Segment {seg.segment_idx} [{start_ts} - {end_ts}] ---\n"
        ctx += f"  Scene: {seg.scene_type or 'unknown'} | Time: {seg.time_of_day or 'unknown'} | Lighting: {seg.lighting or 'unknown'}\n"
        ctx += f"  Weather: {seg.weather or 'unknown'} | Camera: {seg.camera_motion or 'unknown'}\n"
        ctx += f"  Officers: {seg.officers_count} | Civilians: {seg.civilians_count}\n"
        if seg.use_of_force_present:
            types_str = ", ".join(seg.use_of_force_types or [])
            ctx += f"  USE OF FORCE: {types_str}\n"
        if seg.potential_excessive_force:
            ctx += f"  *** POTENTIAL EXCESSIVE FORCE ***\n"
        if seg.camera_obfuscation_present:
            ctx += f"  Camera obfuscation detected\n"
        if seg.key_moments_summary:
            summary = seg.key_moments_summary[:500]
            ctx += f"  Key moments: {summary}\n"

    return ctx


@router.post("/chat", response_model=ChatResponse)
async def chat_with_transcript(request: ChatRequest):
    """
    Chat with GPT using video context. When Gemini is enabled, uses an agentic loop
    where GPT can request visual analysis of specific video segments from Gemini.
    """
    db = SessionLocal()
    try:
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == request.file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        if not file_metadata.transcript:
            raise HTTPException(status_code=400, detail="No transcript available. Please transcribe the video first.")

        user_message = request.messages[-1].content if request.messages else ""
        timestamps = parse_timestamps(user_message)
        video_path = os.path.join("uploads", f"{request.file_id}.mp4")

        # Build frame context for vision (legacy path, still useful)
        visual_analysis_used = False
        frame_contexts = []
        if timestamps and os.path.exists(video_path) and not is_gemini_enabled():
            visual_analysis_used = True
            for timestamp in timestamps[:3]:
                frame_bytes = extract_frame_at_timestamp(video_path, timestamp)
                if frame_bytes:
                    frame_base64 = frame_to_base64(frame_bytes)
                    frame_contexts.append({
                        "timestamp": timestamp,
                        "formatted_time": format_timestamp(timestamp),
                        "image_base64": frame_base64,
                    })

        # Build context strings
        transcript_context = _build_transcript_context(file_metadata, request.file_id)
        moments_context = _build_moments_context(db, request.file_id)
        segment_metadata_context = _build_segment_metadata_context(db, request.file_id)
        ocr_context = _build_ocr_context(file_metadata)

        use_agentic = is_gemini_enabled() and os.path.exists(video_path)

        system_prompt = _build_system_prompt(
            file_metadata,
            transcript_context,
            moments_context,
            segment_metadata_context,
            ocr_context,
            use_agentic,
        )

        if use_agentic:
            return _run_agentic_chat(
                request, system_prompt, video_path, file_metadata,
            )
        else:
            return _run_simple_chat(
                request, system_prompt, frame_contexts,
                visual_analysis_used, timestamps,
            )

    finally:
        db.close()


def _run_simple_chat(
    request: ChatRequest,
    system_prompt: str,
    frame_contexts: list,
    visual_analysis_used: bool,
    timestamps: list,
) -> ChatResponse:
    """Original single-shot chat (no Gemini)."""
    messages = [{"role": "system", "content": system_prompt}]

    for i, msg in enumerate(request.messages):
        is_last = i == len(request.messages) - 1
        if is_last and visual_analysis_used and frame_contexts:
            content_parts = [{"type": "text", "text": msg.content}]
            for frame_ctx in frame_contexts:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame_ctx['image_base64']}",
                        "detail": "high",
                    },
                })
                content_parts.append({
                    "type": "text",
                    "text": f"[Frame extracted at {frame_ctx['formatted_time']}]",
                })
            messages.append({"role": msg.role, "content": content_parts})
        else:
            messages.append({"role": msg.role, "content": msg.content})

    client = _get_openai_client()
    model = "gpt-4o" if visual_analysis_used else os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(model=model, messages=messages, temperature=0.7)
    assistant_message = response.choices[0].message

    return ChatResponse(
        message=ChatMessage(role=assistant_message.role, content=assistant_message.content),
        usage=_extract_usage(response),
        visual_analysis_used=visual_analysis_used,
        analyzed_timestamps=timestamps if visual_analysis_used else None,
    )


def _run_agentic_chat(
    request: ChatRequest,
    system_prompt: str,
    video_path: str,
    file_metadata: FileMetadata,
) -> ChatResponse:
    """
    Agentic chat loop: GPT orchestrates, Gemini visually analyzes segments on demand.
    """
    client = _get_openai_client()
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    max_turns = 5
    duration = file_metadata.duration or 0.0

    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    segments_dir = os.path.abspath(os.path.join("uploads", "..", "segments"))
    os.makedirs(segments_dir, exist_ok=True)

    analyzed_segments: List[str] = []
    asked_cache: set = set()

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=AGENTIC_TOOLS,
            tool_choice="auto",
            temperature=0.0,
        )

        msg = response.choices[0].message

        if msg.content:
            messages.append({"role": "assistant", "content": msg.content})

        if not msg.tool_calls:
            final_content = msg.content or "I was unable to determine an answer."
            return ChatResponse(
                message=ChatMessage(role="assistant", content=final_content),
                usage=_extract_usage(response),
                visual_analysis_used=bool(analyzed_segments),
                gemini_segments_analyzed=analyzed_segments or None,
            )

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if fn_name == "finish":
                return ChatResponse(
                    message=ChatMessage(role="assistant", content=args.get("answer", "")),
                    usage=_extract_usage(response),
                    visual_analysis_used=bool(analyzed_segments),
                    gemini_segments_analyzed=analyzed_segments or None,
                )

            if fn_name == "ask_gemini_on_segment":
                q = args["question"]
                start_ts = args["start_time"]
                end_ts = args["end_time"]

                s = timestamp_to_seconds(start_ts)
                e = timestamp_to_seconds(end_ts)
                if duration > 0 and e > duration:
                    e = int(duration)
                if e <= s:
                    e = min(s + 5, int(duration) if duration > 0 else s + 60)
                if (e - s) > 300:
                    e = s + 300

                start_ts_norm = seconds_to_timestamp(s)
                end_ts_norm = seconds_to_timestamp(e)

                dedup_key = hashlib.md5(f"{q}|{start_ts_norm}|{end_ts_norm}".encode()).hexdigest()
                if dedup_key in asked_cache:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "[Duplicate question on same segment — use prior Gemini answer to synthesize your final response.]",
                    })
                    continue

                asked_cache.add(dedup_key)

                try:
                    seg_path = make_segment_path(segments_dir, video_path, start_ts_norm, end_ts_norm)
                    extract_segment(video_path, s, e, seg_path)

                    full_q = (
                        f"{q} Important: This segment covers {start_ts_norm} to {end_ts_norm} of the full video. "
                        f"Report timestamps relative to the full video, not the segment."
                    )
                    gemini_answer = ask_gemini_about_video(full_q, seg_path)
                    analyzed_segments.append(f"{start_ts_norm}-{end_ts_norm}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Gemini analysis of segment {start_ts_norm}–{end_ts_norm}:\n{gemini_answer[:2000]}",
                    })
                except Exception as ex:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Gemini analysis failed: {str(ex)}",
                    })

    last_content = messages[-1].get("content", "") if messages else ""
    return ChatResponse(
        message=ChatMessage(role="assistant", content=last_content or "Analysis timed out after maximum turns."),
        visual_analysis_used=bool(analyzed_segments),
        gemini_segments_analyzed=analyzed_segments or None,
    )


# ── Context builder helpers ──────────────────────────────────────────────

def _build_transcript_context(file_metadata: FileMetadata, file_id: str) -> str:
    transcript_text = file_metadata.transcript
    transcript_segments = file_metadata.transcript_segments or []

    if isinstance(transcript_segments, str):
        try:
            transcript_segments = json.loads(transcript_segments)
        except Exception:
            transcript_segments = []

    ctx = f"Transcript from video (file_id: {file_id}):\n\n{transcript_text}\n\n"

    if transcript_segments:
        ctx += "Transcript Timestamps:\n"
        for seg in transcript_segments[:50]:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "")
            ctx += f"[{start:.1f}s - {end:.1f}s] {text}\n"

    return ctx


def _build_moments_context(db, file_id: str) -> str:
    from models.schema import MomentOfInterest

    moments = db.query(MomentOfInterest).filter(MomentOfInterest.file_id == file_id).all()
    if not moments:
        return ""

    ctx = f"\n\nDetected Events ({len(moments)} total):\n"
    for moment in moments:
        event_types = moment.event_types or ["Unknown"]
        event_type_str = ", ".join(event_types)
        start_mins = int(moment.start_time // 60)
        start_secs = int(moment.start_time % 60)
        end_mins = int(moment.end_time // 60)
        end_secs = int(moment.end_time % 60)
        time_str = f"{start_mins}:{start_secs:02d} - {end_mins}:{end_secs:02d}"
        confidence_pct = int(moment.interest_score * 100)

        ctx += f"- [{event_type_str}] at {time_str} ({moment.start_time:.1f}s-{moment.end_time:.1f}s)"
        ctx += f" [Confidence: {confidence_pct}%]\n"
        if moment.description:
            ctx += f"  Description: {moment.description}\n"

    return ctx


def _build_ocr_context(file_metadata: FileMetadata) -> str:
    if not file_metadata.ocr_metadata:
        return ""

    ocr_metadata = file_metadata.ocr_metadata
    if isinstance(ocr_metadata, str):
        try:
            ocr_metadata = json.loads(ocr_metadata)
        except Exception:
            return ""

    if not ocr_metadata or not any(v for k, v in ocr_metadata.items() if k != "raw_text" and v):
        return ""

    ctx = "\n\nOCR Extracted Metadata:\n"
    for key in ("timestamp", "device_id", "device_model", "badge_number", "officer_id"):
        if ocr_metadata.get(key):
            ctx += f"- {key.replace('_', ' ').title()}: {ocr_metadata[key]}\n"
    if ocr_metadata.get("raw_text"):
        ctx += f"- Raw OCR Text: {ocr_metadata['raw_text'][:500]}\n"

    return ctx


def _extract_usage(response) -> Optional[dict]:
    if not response.usage:
        return None
    return {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }
