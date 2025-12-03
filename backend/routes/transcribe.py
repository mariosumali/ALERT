from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from models.database import SessionLocal
from models.schema import FileMetadata
from celery_worker import transcribe_task
from utils.helpers import format_duration
import traceback
import os
import glob
import tempfile
import datetime
import json

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
async def download_transcript(
    file_id: str = Query(..., description="File ID to download transcript for"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Download the comprehensive transcript file with timestamps.
    Generates the file from database data instead of looking for pre-existing files.
    """
    db = SessionLocal()
    try:
        # Get file metadata from database
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_metadata.transcript and not file_metadata.transcript_segments:
            raise HTTPException(status_code=404, detail="No transcript available for this file. Please transcribe the video first.")
        
        # Get transcript data
        transcript_text = file_metadata.transcript or ""
        transcript_segments = file_metadata.transcript_segments or []
        
        # If transcript_segments is a JSON string, parse it
        if isinstance(transcript_segments, str):
            try:
                transcript_segments = json.loads(transcript_segments)
            except:
                transcript_segments = []
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{file_id}_{timestamp}.txt"
        
        # Create a temporary file to write the transcript
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("COMPREHENSIVE TRANSCRIPT\n")
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
            
            # Transcript Section
            f.write("=" * 80 + "\n")
            f.write("TRANSCRIPT WITH TIMESTAMPS\n")
            f.write("=" * 80 + "\n\n")
            
            if transcript_segments:
                # Filter to only segments with valid timestamps
                valid_segments = [s for s in transcript_segments if s.get("start") is not None and s.get("end") is not None and s.get("start", -1) >= 0]
                f.write(f"Total Segments: {len(valid_segments)} (from {len(transcript_segments)} total)\n")
                if valid_segments:
                    f.write(f"Time Range: {format_duration(valid_segments[0].get('start', 0))} - {format_duration(valid_segments[-1].get('end', 0))}\n")
                f.write("\n")
                for segment in valid_segments:
                    start = segment.get("start", 0.0)
                    end = segment.get("end", 0.0)
                    text = segment.get("text", "")
                    f.write(f"[{format_duration(start)} - {format_duration(end)}] {text}\n")
            else:
                f.write("No transcript segments available.\n\n")
            
            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write("FULL TRANSCRIPT TEXT\n")
            f.write("=" * 80 + "\n\n")
            f.write(transcript_text if transcript_text else "No transcript text available.")
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
        raise HTTPException(status_code=500, detail=f"Failed to download transcript: {str(e)}")
    finally:
        db.close()

@router.get("/ocr/download")
async def download_ocr_metadata(
    file_id: str = Query(..., description="File ID to download OCR metadata for"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Download the OCR extracted metadata file.
    Generates the file from database data.
    """
    db = SessionLocal()
    try:
        # Get file metadata from database
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_metadata.ocr_metadata:
            raise HTTPException(status_code=404, detail="No OCR metadata available for this file. OCR extraction may not have been performed or no metadata was found.")
        
        # Get OCR metadata
        ocr_metadata = file_metadata.ocr_metadata
        
        # If ocr_metadata is a JSON string, parse it
        if isinstance(ocr_metadata, str):
            try:
                ocr_metadata = json.loads(ocr_metadata)
            except:
                raise HTTPException(status_code=500, detail="Failed to parse OCR metadata")
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ocr_{file_id}_{timestamp}.txt"
        
        # Create a temporary file to write the OCR metadata
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("OCR EXTRACTED METADATA\n")
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
            
            # OCR Metadata Section
            f.write("=" * 80 + "\n")
            f.write("EXTRACTED METADATA\n")
            f.write("=" * 80 + "\n\n")
            
            if ocr_metadata:
                if ocr_metadata.get("timestamp"):
                    f.write(f"Timestamp: {ocr_metadata['timestamp']}\n")
                if ocr_metadata.get("device_id"):
                    f.write(f"Device ID: {ocr_metadata['device_id']}\n")
                if ocr_metadata.get("device_model"):
                    f.write(f"Device Model: {ocr_metadata['device_model']}\n")
                if ocr_metadata.get("badge_number"):
                    f.write(f"Badge Number: {ocr_metadata['badge_number']}\n")
                if ocr_metadata.get("officer_id"):
                    f.write(f"Officer ID: {ocr_metadata['officer_id']}\n")
                
                f.write("\n")
                f.write("=" * 80 + "\n")
                f.write("RAW OCR TEXT\n")
                f.write("=" * 80 + "\n\n")
                f.write(ocr_metadata.get("raw_text", "No raw text available."))
                f.write("\n")
            else:
                f.write("No OCR metadata available.\n")
            
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
        raise HTTPException(status_code=500, detail=f"Failed to download OCR metadata: {str(e)}")
    finally:
        db.close()

