from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from models.database import SessionLocal
from models.schema import VideoSegmentMetadata
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/segments")
async def get_segments(file_id: str = Query(..., description="File ID to get segments for")):
    """
    Get all video segment metadata for a given file.
    Returns the structured Gemini analysis results per video chunk.
    """
    db: Session = SessionLocal()
    try:
        segments = (
            db.query(VideoSegmentMetadata)
            .filter(VideoSegmentMetadata.file_id == file_id)
            .order_by(VideoSegmentMetadata.segment_idx)
            .all()
        )

        segments_data = []
        for seg in segments:
            segments_data.append({
                "id": seg.id,
                "file_id": seg.file_id,
                "segment_idx": seg.segment_idx,
                "start_sec": seg.start_sec,
                "end_sec": seg.end_sec,
                "scene_type": seg.scene_type,
                "time_of_day": seg.time_of_day,
                "lighting": seg.lighting,
                "weather": seg.weather,
                "camera_motion": seg.camera_motion,
                "camera_obfuscation_present": seg.camera_obfuscation_present,
                "officers_count": seg.officers_count,
                "civilians_count": seg.civilians_count,
                "use_of_force_present": seg.use_of_force_present,
                "use_of_force_types": seg.use_of_force_types or [],
                "potential_excessive_force": seg.potential_excessive_force,
                "key_moments_summary": seg.key_moments_summary,
                "summary": seg.summary,
            })

        return {
            "segments": segments_data,
            "count": len(segments_data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch segments: {str(e)}")
    finally:
        db.close()
