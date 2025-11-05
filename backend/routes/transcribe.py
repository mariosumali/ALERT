from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from models.database import SessionLocal
from models.schema import FileMetadata
from services.transcription import transcribe_file_with_timestamps
from celery_worker import transcribe_task
import traceback

router = APIRouter()

@router.post("/transcribe")
async def transcribe_file_endpoint(file_id: str = Query(..., description="File ID to transcribe")):
    """
    Transcribe a file with timestamps.
    Can be called asynchronously via Celery or synchronously.
    """
    db = SessionLocal()
    try:
        # Get file metadata
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Launch async transcription task
        transcribe_task.delay(file_id, file_metadata.path)
        
        return JSONResponse({
            "file_id": file_id,
            "message": "Transcription started. Use GET /transcribe to check status.",
            "status": "processing"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Transcribe endpoint error: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        db.close()

@router.get("/transcribe")
async def get_transcription(file_id: str = Query(..., description="File ID to get transcription for")):
    """
    Get transcription for a file (with timestamps).
    """
    db = SessionLocal()
    try:
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return JSONResponse({
            "file_id": file_id,
            "transcript": file_metadata.transcript or "",
            "segments": file_metadata.transcript_segments or [],
            "has_transcription": file_metadata.transcript is not None
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcription: {str(e)}")
    finally:
        db.close()

