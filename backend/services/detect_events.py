from typing import List, Dict, Optional
from services.audio_features import extract_audio_features, detect_audio_events
from services.video_features import extract_video_features, detect_video_events
from services.transcription import transcribe_file

def detect_moments(file_path: str, file_type: str, transcript_segments: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Main function to detect moments of interest by combining audio/video/text features.
    Returns list of detected moments.
    
    Args:
        file_path: Path to the media file
        file_type: "video" or "audio"
        transcript_segments: Optional list of transcript segments with timestamps
    """
    all_events = []
    
    try:
        # 1. Extract and detect audio events
        print(f"Extracting audio features from {file_path}...")
        audio_features = extract_audio_features(file_path)
        transcript_text = " ".join([seg.get("text", "") for seg in (transcript_segments or [])])
        audio_events = detect_audio_events(audio_features, transcript_text)
        print(f"Found {len(audio_events)} audio events")
        all_events.extend(audio_events)
        
        # 2. Extract and detect video events (if video)
        if file_type == "video":
            print(f"Extracting video features from {file_path}...")
            video_features = extract_video_features(file_path)
            video_events = detect_video_events(video_features)
            print(f"Found {len(video_events)} video events")
            all_events.extend(video_events)
        
        # 3. Detect transcript-based events
        if transcript_segments:
            print(f"Analyzing {len(transcript_segments)} transcript segments...")
            transcript_events = detect_transcript_events(transcript_segments)
            print(f"Found {len(transcript_events)} transcript events")
            all_events.extend(transcript_events)
        
        # 4. Fuse and classify events
        moments = fuse_and_classify(all_events)
        
        print(f"Total moments detected: {len(moments)}")
        return moments
        
    except Exception as e:
        print(f"Error in moment detection: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty list on error instead of crashing
        return []

def fuse_and_classify(events: List[Dict]) -> List[Dict]:
    """
    Fuse multiple event signals and classify final moments.
    Combines events that occur at similar times and calculates interest scores.
    """
    if not events:
        return []
    
    # Sort events by start time
    events_sorted = sorted(events, key=lambda x: x.get("start_time", 0.0))
    
    # Group nearby events (within 3 seconds)
    fused_moments = []
    current_group = []
    merge_window = 3.0  # seconds
    
    for event in events_sorted:
        if not current_group:
            current_group = [event]
        else:
            # Check if this event overlaps or is close to the current group
            last_event_end = max(e.get("end_time", 0.0) for e in current_group)
            if event.get("start_time", 0.0) <= last_event_end + merge_window:
                current_group.append(event)
            else:
                # Fuse the current group
                fused_moment = fuse_event_group(current_group)
                if fused_moment:
                    fused_moments.append(fused_moment)
                current_group = [event]
    
    # Fuse the last group
    if current_group:
        fused_moment = fuse_event_group(current_group)
        if fused_moment:
            fused_moments.append(fused_moment)
    
    # Sort by interest score (highest first)
    fused_moments.sort(key=lambda x: x.get("interest_score", 0.0), reverse=True)
    
    # Limit to top 20 moments to avoid overwhelming the UI
    return fused_moments[:20]

def fuse_event_group(events: List[Dict]) -> Optional[Dict]:
    """
    Fuse a group of overlapping or nearby events into a single moment.
    """
    if not events:
        return None
    
    # Calculate time bounds
    start_times = [e.get("start_time", 0.0) for e in events]
    end_times = [e.get("end_time", 0.0) for e in events]
    start_time = min(start_times)
    end_time = max(end_times)
    
    # Collect all event types
    event_types = set()
    descriptions = []
    confidences = []
    
    type_mapping = {
        "HighEnergy": "Gunshot",
        "Silence": "Silence",
        "Motion": "Motion",
        "Occlusion": "Occlusion",
        "BrightnessChange": "BrightnessChange",
        "EnergyChange": "EnergyChange",
        "UrgentKeyword": "UrgentKeyword",
        "Profanity": "Profanity",
        "Conflict": "Conflict",
        "Multiple": "Multiple"
    }
    
    for event in events:
        event_type = event.get("type", "")
        mapped_type = type_mapping.get(event_type, event_type)
        event_types.add(mapped_type)
        
        desc = event.get("description", "")
        if desc:
            descriptions.append(desc)
        
        conf = event.get("confidence", 0.5)
        confidences.append(conf)
    
    # Calculate interest score based on:
    # - Number of different event types (more = more interesting)
    # - Average confidence
    # - Number of events
    num_types = len(event_types)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    num_events = len(events)
    
    # Interest score formula
    type_bonus = min(0.3, num_types * 0.1)
    confidence_score = avg_confidence * 0.6
    event_count_bonus = min(0.1, num_events * 0.02)
    
    interest_score = min(0.99, confidence_score + type_bonus + event_count_bonus)
    
    # Generate description
    if len(descriptions) == 1:
        description = descriptions[0]
    elif len(descriptions) > 1:
        # Combine descriptions intelligently
        unique_descriptions = list(set(descriptions))[:3]  # Limit to 3 unique descriptions
        description = f"Multiple events: {'; '.join(unique_descriptions)}"
    else:
        description = f"Detected {', '.join(sorted(event_types))}"
    
    return {
        "start_time": round(start_time, 2),
        "end_time": round(end_time, 2),
        "event_types": sorted(list(event_types)),
        "interest_score": round(interest_score, 3),
        "description": description
    }

def detect_transcript_events(transcript_segments: List[Dict]) -> List[Dict]:
    """
    Detect events based on transcript content.
    Analyzes transcript segments for keywords, profanity, urgency indicators.
    """
    events = []
    
    if not transcript_segments:
        return events
    
    # Keywords that indicate important events
    urgency_keywords = [
        "gun", "gunshot", "shoot", "fire", "weapon", "knife", "threat",
        "arrest", "suspect", "backup", "emergency", "help", "assistance",
        "stop", "freeze", "hands", "warrant", "search", "pat down",
        "rights", "miranda", "lawyer", "attorney"
    ]
    
    profanity_keywords = [
        "fuck", "shit", "damn", "bitch", "asshole", "bastard", "crap",
        "hell", "piss", "dammit", "fucking", "fucked"
    ]
    
    # Keywords indicating potential violence or conflict
    conflict_keywords = [
        "fight", "struggle", "resist", "resisting", "assault", "attack",
        "hit", "strike", "punch", "kick", "taser", "tase", "cuff", "handcuff"
    ]
    
    for segment in transcript_segments:
        text = segment.get("text", "").lower()
        start_time = segment.get("start", 0.0)
        end_time = segment.get("end", 0.0)
        
        if not text:
            continue
        
        event_types = []
        confidence = 0.0
        description_parts = []
        
        # Check for urgency keywords
        urgency_matches = [kw for kw in urgency_keywords if kw in text]
        if urgency_matches:
            event_types.append("UrgentKeyword")
            confidence = max(confidence, 0.7)
            description_parts.append(f"Urgent keywords detected: {', '.join(urgency_matches[:3])}")
        
        # Check for profanity
        profanity_matches = [kw for kw in profanity_keywords if kw in text]
        if profanity_matches:
            event_types.append("Profanity")
            confidence = max(confidence, 0.75)
            description_parts.append("Profanity detected")
        
        # Check for conflict keywords
        conflict_matches = [kw for kw in conflict_keywords if kw in text]
        if conflict_matches:
            event_types.append("Conflict")
            confidence = max(confidence, 0.8)
            description_parts.append(f"Conflict indicators: {', '.join(conflict_matches[:2])}")
        
        # Check for high volume of keywords (multiple indicators)
        all_keywords = urgency_matches + conflict_matches
        if len(all_keywords) >= 3:
            confidence = min(0.95, confidence + 0.1)
            description_parts.append("Multiple indicators detected")
        
        # Create event if any indicators found
        if event_types:
            events.append({
                "type": event_types[0] if len(event_types) == 1 else "Multiple",
                "event_types": event_types,
                "start_time": start_time,
                "end_time": end_time,
                "confidence": confidence,
                "description": ". ".join(description_parts) if description_parts else "Transcript event detected"
            })
    
    return events

def load_event_detector_model(model_path: str = "models/event_detector.pt"):
    """
    Load trained event detector model.
    Placeholder for future implementation.
    """
    # TODO: Implement model loading
    # import torch
    # model = torch.load(model_path)
    # model.eval()
    # return model
    return None

