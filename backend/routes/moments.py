from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from models.database import SessionLocal
from models.schema import MomentOfInterest, FileMetadata
from sqlalchemy.orm import Session
from utils.helpers import format_duration
import tempfile
import datetime
import os

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

@router.get("/moments/download")
async def download_moments(
    file_id: str = Query(..., description="File ID to download moments for"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Download the detected moments of interest file.
    Generates the file from database data.
    """
    db: Session = SessionLocal()
    try:
        # Get file metadata
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get moments from database
        moments = db.query(MomentOfInterest).filter(MomentOfInterest.file_id == file_id).all()
        
        if not moments:
            raise HTTPException(status_code=404, detail="No moments of interest detected for this file.")
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"moments_{file_id}_{timestamp}.txt"
        
        # Create a temporary file to write the moments
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("DETECTED MOMENTS OF INTEREST\n")
            f.write("=" * 80 + "\n\n")
            
            # File metadata
            f.write("FILE INFORMATION\n")
            f.write("-" * 80 + "\n")
            f.write(f"File ID: {file_id}\n")
            f.write(f"Original Filename: {file_metadata.original_filename or 'N/A'}\n")
            f.write(f"File Type: {file_metadata.file_type}\n")
            f.write(f"File Path: {file_metadata.path}\n")
            if file_metadata.duration:
                f.write(f"Duration: {format_duration(file_metadata.duration)} ({file_metadata.duration:.2f} seconds)\n")
            if file_metadata.file_size:
                size_mb = file_metadata.file_size / (1024 * 1024)
                f.write(f"File Size: {size_mb:.2f} MB\n")
            f.write(f"Processed: {timestamp}\n")
            f.write("\n")
            
            # Moments Section
            f.write("=" * 80 + "\n")
            f.write(f"DETECTED EVENTS ({len(moments)} total)\n")
            f.write("=" * 80 + "\n\n")
            
            for idx, moment in enumerate(moments, 1):
                event_types = moment.event_types if moment.event_types else ["Unknown"]
                event_type_str = ", ".join(event_types)
                
                # Format time as MM:SS
                start_mins = int(moment.start_time // 60)
                start_secs = int(moment.start_time % 60)
                end_mins = int(moment.end_time // 60)
                end_secs = int(moment.end_time % 60)
                time_str = f"{start_mins}:{start_secs:02d} - {end_mins}:{end_secs:02d}"
                
                confidence_pct = int(moment.interest_score * 100) if moment.interest_score else 0
                
                f.write(f"Event #{idx}: {event_type_str}\n")
                f.write(f"  Time: {time_str} ({moment.start_time:.1f}s - {moment.end_time:.1f}s)\n")
                f.write(f"  Confidence: {confidence_pct}%\n")
                if moment.description:
                    f.write(f"  Description: {moment.description}\n")
                f.write(f"  Moment ID: {moment.moment_id}\n")
                f.write("\n")
            
            temp_file_path = f.name
        
        # Clean up temp file after response
        background_tasks.add_task(os.unlink, temp_file_path)
        
        # Return the file response
        return FileResponse(
            temp_file_path,
            media_type="text/plain",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download moments: {str(e)}")
    finally:
        db.close()

