from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from models.database import SessionLocal
from models.schema import MomentOfInterest
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/moments")
async def get_moments(file_id: Optional[str] = Query(None, description="Filter by file_id")):
    """
    Get all detected moments of interest.
    Optionally filter by file_id.
    """
    db: Session = SessionLocal()
    try:
        query = db.query(MomentOfInterest)
        
        if file_id:
            query = query.filter(MomentOfInterest.file_id == file_id)
        
        moments = query.all()
        
        # Ensure event_types is always a list (handle None case)
        moments_data = []
        for moment in moments:
            event_types = moment.event_types if moment.event_types is not None else []
            # Ensure it's a list (in case it's stored as something else)
            if not isinstance(event_types, list):
                event_types = []
            
            moments_data.append({
                "moment_id": moment.moment_id,
                "file_id": moment.file_id,
                "start_time": moment.start_time,
                "end_time": moment.end_time,
                "event_types": event_types,
                "interest_score": moment.interest_score,
                "description": moment.description
            })
        
        return {
            "moments": moments_data,
            "count": len(moments_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch moments: {str(e)}")
    finally:
        db.close()

