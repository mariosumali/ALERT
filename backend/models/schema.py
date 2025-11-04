from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Text
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

class MomentOfInterest(Base):
    __tablename__ = "moments_of_interest"
    
    moment_id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(UUID(as_uuid=False), nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)  # End time in seconds
    event_types = Column(JSON, nullable=True)  # List of event types, e.g., ["Gunshot", "Silence"]
    interest_score = Column(Float, nullable=True)  # Score from 0.0 to 1.0
    description = Column(Text, nullable=True)  # Human-readable description

