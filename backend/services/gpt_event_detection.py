"""
GPT-powered semantic event detection from transcripts.
Identifies moments of interest that keyword matching and audio analysis cannot catch.
"""

import json
import os
from typing import Dict, List

from openai import OpenAI


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


EVENT_DETECTION_PROMPT = """\
You are an expert analyst reviewing body-camera transcript segments from law enforcement.
Identify ALL moments of interest in the transcript below.

For EACH moment return a JSON object with these keys:
  - start_time  (float, seconds – use the segment timestamp)
  - end_time    (float, seconds)
  - event_type  (string – one of the categories listed below)
  - confidence  (float 0.0-1.0)
  - description (string – brief explanation)

Categories to look for:
  - Verbal Confrontation  (raised voices, arguments, heated exchanges)
  - Threat                (threats of violence, intimidation)
  - Weapon Mention        (mention of gun, knife, weapon)
  - Use of Force          (descriptions of physical force)
  - Miranda Rights        (Miranda warning being read)
  - Medical Emergency     (requests for medical help, injury descriptions)
  - Emotional Distress    (crying, screaming, panic)
  - Pursuit               (foot chase, vehicle pursuit language)
  - Compliance Issue      (refusal to follow commands, resistance)
  - De-escalation         (calming language, negotiation)

Return a JSON array. If nothing notable is found, return an empty array [].
Do NOT wrap in markdown. Return ONLY valid JSON.

TRANSCRIPT:
{transcript_block}
"""


def _format_transcript(segments: List[Dict]) -> str:
    """Build a readable transcript block with timestamps."""
    lines = []
    for seg in segments:
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{start:.1f}s - {end:.1f}s] {text}")
    return "\n".join(lines)


def detect_events_from_transcript(
    transcript_segments: List[Dict],
    duration: float = 0.0,
) -> List[Dict]:
    """
    Use GPT to semantically analyse transcript segments and detect
    moments of interest that rule-based detectors miss.
    """
    client = _get_openai_client()
    if not client:
        print("[GPT EVENTS] No OpenAI API key – skipping GPT event detection")
        return []

    if not transcript_segments:
        return []

    transcript_block = _format_transcript(transcript_segments)

    if not transcript_block.strip():
        return []

    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    try:
        print(f"[GPT EVENTS] Sending {len(transcript_segments)} segments to {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise JSON-only analyst. Never output anything other than valid JSON.",
                },
                {
                    "role": "user",
                    "content": EVENT_DETECTION_PROMPT.format(transcript_block=transcript_block),
                },
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        raw_events: List[Dict] = json.loads(content)

        events: List[Dict] = []
        for evt in raw_events:
            start = float(evt.get("start_time", 0.0))
            end = float(evt.get("end_time", start + 1.0))
            conf = float(evt.get("confidence", 0.7))
            etype = evt.get("event_type", "Event")
            desc = evt.get("description", "")

            if duration > 0:
                start = min(start, duration)
                end = min(end, duration)
            if end <= start:
                end = start + 1.0

            events.append({
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "event_types": [etype],
                "confidence": round(conf, 2),
                "description": desc,
                "category": etype,
            })

        print(f"[GPT EVENTS] ✓ Detected {len(events)} events")
        return events

    except json.JSONDecodeError as e:
        print(f"[GPT EVENTS] ⚠ Failed to parse GPT response: {e}")
        return []
    except Exception as e:
        print(f"[GPT EVENTS] ⚠ Error: {e}")
        return []
