from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from models.database import Base

class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    file_id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # "video" or "audio"
    source_agency = Column(String, nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds
    timestamp_start = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    original_filename = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)  # Full transcript text
    transcript_segments = Column(JSON, nullable=True)  # List of segments with timestamps: [{"start": 0.0, "end": 5.0, "text": "..."}]
    status = Column(String, default="pending")  # pending, processing_transcription, processing_audio, processing_video_analysis, completed, failed
    ocr_metadata = Column(JSON, nullable=True)  # OCR extracted metadata: {"raw_text": "...", "timestamp": "...", "device_id": "...", ...}

class MomentOfInterest(Base):
    __tablename__ = "moments_of_interest"
    
    moment_id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(UUID(as_uuid=False), nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)  # End time in seconds
    event_types = Column(JSON, nullable=True)  # List of event types, e.g., ["Gunshot", "Silence"]
    interest_score = Column(Float, nullable=True)  # Score from 0.0 to 1.0
    description = Column(Text, nullable=True)  # Human-readable description


class VideoSegmentMetadata(Base):
    """
    Per-segment structured metadata from Gemini multimodal video analysis.
    Each row represents one chunk (typically 5 min) of a video.
    """
    __tablename__ = "video_segment_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    segment_idx = Column(Integer, nullable=False)
    start_sec = Column(Float, nullable=False)
    end_sec = Column(Float, nullable=False)

    scene_type = Column(String, nullable=True)
    time_of_day = Column(String, nullable=True)
    lighting = Column(String, nullable=True)
    weather = Column(String, nullable=True)
    camera_motion = Column(String, nullable=True)

    camera_obfuscation_present = Column(Boolean, default=False)
    officers_count = Column(Integer, default=0)
    civilians_count = Column(Integer, default=0)

    use_of_force_present = Column(Boolean, default=False)
    use_of_force_types = Column(JSON, nullable=True)
    potential_excessive_force = Column(Boolean, default=False)

    key_moments_summary = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    raw_metadata = Column(JSON, nullable=True)

