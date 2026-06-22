from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
import traceback
from datetime import datetime
from models.database import SessionLocal
from models.schema import FileMetadata
from celery_worker import transcribe_and_detect_task

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Accepted media extensions and how each maps to a processing type.
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
ALLOWED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Cap upload size to protect disk/memory (configurable). Default 2 GB.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "2048")) * 1024 * 1024

# Stream uploads to disk in 1 MB chunks instead of buffering the whole file
# in memory — body-cam footage is routinely hundreds of MB.
_CHUNK_SIZE = 1024 * 1024


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a video/audio file, save it, and launch background processing.
    Returns file_id for tracking.
    """
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Determine and validate the file extension.
        file_ext = (os.path.splitext(file.filename)[1] if file.filename else "").lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '{file_ext or 'unknown'}'. Allowed types: {allowed}",
            )

        # Stream the file to disk in chunks, enforcing the size limit as we go.
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        file_size = 0
        try:
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File exceeds the maximum upload size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                        )
                    f.write(chunk)
        except HTTPException:
            # Remove the partially written file on validation failure.
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise

        if file_size == 0:
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Determine file type (video or audio)
        file_type = "video" if file_ext in VIDEO_EXTENSIONS else "audio"

        # Save metadata to database
        db = SessionLocal()
        try:
            file_metadata = FileMetadata(
                file_id=file_id,
                path=file_path,
                file_type=file_type,
                source_agency="user_upload",
                duration=None,  # Will be updated after processing
                timestamp_start=datetime.utcnow(),
                file_size=file_size,
                original_filename=file.filename
            )
            db.add(file_metadata)
            db.commit()
            db.refresh(file_metadata)
        finally:
            db.close()
        
        # Launch Celery task for async processing
        transcribe_and_detect_task.delay(file_id, file_path)
        
        return JSONResponse({
            "file_id": file_id,
            "message": "File uploaded successfully. Processing started.",
            "status": "processing"
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Upload error: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files/{file_id}/metadata")
async def get_file_metadata(file_id: str):
    """
    Retrieve file metadata, including OCR extracted info.
    """
    db = SessionLocal()
    try:
        file_record = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "file_id": file_record.file_id,
            "original_filename": file_record.original_filename,
            "ocr_metadata": file_record.ocr_metadata,
            "duration": file_record.duration,
            "timestamp_start": file_record.timestamp_start,
            "status": file_record.status
        }
    finally:
        db.close()

