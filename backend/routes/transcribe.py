from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from models.database import SessionLocal
from models.schema import FileMetadata
from celery_worker import transcribe_task
import traceback
import os
import glob

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
            "has_transcription": file_metadata.transcript is not None,
            "status": file_metadata.status or "pending"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcription: {str(e)}")
    finally:
        db.close()

@router.get("/transcribe/download")
async def download_transcript(file_id: str = Query(..., description="File ID to download transcript for")):
    """
    Download the comprehensive transcript file with timestamps and anomalies.
    """
    try:
        # Find the transcript file for this file_id
        # Transcripts are saved in backend/transcripts/ directory
        # __file__ is backend/routes/transcribe.py, so go up one level to backend/
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        transcripts_dir = os.path.join(backend_dir, "transcripts")
        
        if not os.path.exists(transcripts_dir):
            raise HTTPException(status_code=404, detail="Transcript file not found. File may not have been processed yet.")
        
        # Find the most recent transcript file for this file_id
        pattern = os.path.join(transcripts_dir, f"{file_id}_*.txt")
        transcript_files = glob.glob(pattern)
        
        if not transcript_files:
            raise HTTPException(status_code=404, detail="Transcript file not found. File may not have been processed yet.")
        
        # Get the most recent file (by modification time)
        transcript_file = max(transcript_files, key=os.path.getmtime)
        
        # Get filename for download
        filename = os.path.basename(transcript_file)
        
        return FileResponse(
            transcript_file,
            media_type="text/plain",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download transcript: {str(e)}")

