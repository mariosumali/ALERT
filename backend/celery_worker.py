from celery import Celery
from models.database import SessionLocal, init_db
from models.schema import FileMetadata
from services.transcription import transcribe_file_with_timestamps
from services.audio_anomaly_detection import extract_raw_audio_from_video, analyze_audio_anomalies
from utils.helpers import get_media_duration, format_duration
import os
import tempfile
import datetime

# Initialize Celery
celery_app = Celery(
    "multimedia_events",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def save_comprehensive_transcript(file_id: str, file_path: str, transcript_text: str, 
                                  transcript_segments: list, audio_anomalies: list, 
                                  file_metadata: FileMetadata):
    """
    Save a comprehensive transcript file with timestamps.
    Note: audio_anomalies parameter is kept for API compatibility but not included in the file.
    """
    try:
        # Create transcripts directory
        # file_path is typically ./uploads/{file_id}.mp4
        # We want backend/transcripts/
        uploads_dir = os.path.dirname(os.path.abspath(file_path))
        transcripts_dir = os.path.join(uploads_dir, "..", "transcripts")
        transcripts_dir = os.path.abspath(transcripts_dir)
        os.makedirs(transcripts_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_file = os.path.join(transcripts_dir, f"{file_id}_{timestamp}.txt")
        
        with open(transcript_file, "w", encoding="utf-8") as f:
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
            f.write(f"File Path: {file_path}\n")
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
        
        print(f"[TRANSCRIPT FILE] Saved to: {transcript_file}")
        return transcript_file
        
    except Exception as e:
        print(f"[TRANSCRIPT FILE] Error: {e}")
        raise

@celery_app.task(name="transcribe_and_detect")
def transcribe_and_detect_task(file_id: str, file_path: str):
    """
    Background task to transcribe file and detect moments of interest.
    """
    try:
        db = SessionLocal()
        
        # Get file metadata
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            print(f"File {file_id} not found in database")
            return
        
        transcript_text = ""
        transcript_segments = []

        try:
            print(f"Transcribing file {file_id} prior to moment detection...")
            transcript_text, transcript_segments = transcribe_file_with_timestamps(
                file_path, use_mock=False
            )
            print(
                f"✓ Transcription complete for file {file_id}: {len(transcript_text)} characters, {len(transcript_segments)} segments with timestamps"
            )
            if transcript_segments:
                print(f"  Time range: {transcript_segments[0].get('start', 0):.1f}s - {transcript_segments[-1].get('end', 0):.1f}s")
                print(f"  First segment: [{transcript_segments[0].get('start', 0):.1f}s - {transcript_segments[0].get('end', 0):.1f}s] {transcript_segments[0].get('text', '')[:50]}...")
                if len(transcript_segments) > 1:
                    print(f"  Last segment: [{transcript_segments[-1].get('start', 0):.1f}s - {transcript_segments[-1].get('end', 0):.1f}s] {transcript_segments[-1].get('text', '')[:50]}...")
        except Exception as exc:
            print(f"Transcription failed for file {file_id}: {exc}")
        finally:
            # Persist whatever we have so the UI reflects the latest status
            file_metadata.transcript = transcript_text
            file_metadata.transcript_segments = transcript_segments
            db.commit()
        
        # Extract and save duration
        print(f"[METADATA] Extracting duration for file {file_id}...")
        duration = 0.0
        try:
            # Try ffprobe first (most reliable)
            duration = get_media_duration(file_path)
            
            # get_media_duration already tries multiple methods, so no additional fallback needed
            
            if duration > 0:
                file_metadata.duration = duration
                db.commit()
                print(f"[METADATA] ✓ Saved duration: {duration:.2f} seconds ({int(duration // 60)}:{int(duration % 60):02d})")
            else:
                print(f"[METADATA] Warning: Could not extract duration (got {duration})")
        except Exception as e:
            print(f"[METADATA] Warning: Failed to extract duration: {e}")
            import traceback
            traceback.print_exc()
        
        # Extract and analyze raw audio for anomalies
        audio_anomalies = []
        extracted_audio_path = None
        temp_audio_dir = None
        
        try:
            if file_metadata.file_type == "video":
                print(f"[AUDIO ANOMALY DETECTION] Extracting raw audio from video...")
                # Create temp directory for audio files
                temp_audio_dir = tempfile.mkdtemp(prefix="audio_analysis_")
                extracted_audio_path = extract_raw_audio_from_video(file_path, temp_audio_dir)
                print(f"[AUDIO ANOMALY DETECTION] ✓ Audio extracted to {extracted_audio_path}")
                
                print(f"[AUDIO ANOMALY DETECTION] Analyzing audio for anomalies...")
                audio_anomalies = analyze_audio_anomalies(extracted_audio_path)
                print(f"[AUDIO ANOMALY DETECTION] ✓ Found {len(audio_anomalies)} audio anomalies")
            else:
                # For audio files, analyze directly
                print(f"[AUDIO ANOMALY DETECTION] Analyzing audio file for anomalies...")
                audio_anomalies = analyze_audio_anomalies(file_path)
                print(f"[AUDIO ANOMALY DETECTION] ✓ Found {len(audio_anomalies)} audio anomalies")
        except Exception as e:
            print(f"[AUDIO ANOMALY DETECTION] ⚠ Error in audio anomaly detection: {e}")
            import traceback
            traceback.print_exc()
        
        # Save comprehensive transcript file with timestamps and anomalies
        try:
            print(f"[TRANSCRIPT FILE] Saving comprehensive transcript with anomalies...")
            save_comprehensive_transcript(
                file_id=file_id,
                file_path=file_path,
                transcript_text=transcript_text,
                transcript_segments=transcript_segments,
                audio_anomalies=audio_anomalies,
                file_metadata=file_metadata
            )
            print(f"[TRANSCRIPT FILE] ✓ Transcript file saved")
        except Exception as e:
            print(f"[TRANSCRIPT FILE] ⚠ Error saving transcript file: {e}")
            import traceback
            traceback.print_exc()
        
        # Cleanup extracted audio file if it was created
        if extracted_audio_path and os.path.exists(extracted_audio_path):
            try:
                os.unlink(extracted_audio_path)
                print(f"[AUDIO ANOMALY DETECTION] ✓ Cleaned up extracted audio file")
            except Exception as e:
                print(f"[AUDIO ANOMALY DETECTION] ⚠ Could not delete audio file: {e}")
        
        if temp_audio_dir and os.path.exists(temp_audio_dir):
            try:
                import shutil
                shutil.rmtree(temp_audio_dir)
            except Exception as e:
                print(f"[AUDIO ANOMALY DETECTION] ⚠ Could not delete temp directory: {e}")
        
    except Exception as e:
        print(f"Error processing file {file_id}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

@celery_app.task(name="transcribe")
def transcribe_task(file_id: str, file_path: str):
    """
    Background task to transcribe file with timestamps.
    """
    try:
        db = SessionLocal()
        
        # Get file metadata
        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            print(f"File {file_id} not found in database")
            return
        
        print(f"Transcribing file {file_id} with timestamps...")
        transcript_text = ""
        transcript_segments = []

        try:
            transcript_text, transcript_segments = transcribe_file_with_timestamps(
                file_path, use_mock=False
            )
            print(
                f"Transcription complete for file {file_id}. {len(transcript_segments)} segments created."
            )
        except Exception as exc:
            print(f"Transcription failed for file {file_id}: {exc}")
        finally:
            file_metadata.transcript = transcript_text
            file_metadata.transcript_segments = transcript_segments
            
            # Extract and save duration if not already set
            if not file_metadata.duration or file_metadata.duration == 0:
                print(f"[METADATA] Extracting duration for file {file_id}...")
                duration = 0.0
                try:
                    # Try ffprobe first (most reliable)
                    duration = get_media_duration(file_path)
                    
                    # Fallback to feature extraction methods if ffprobe failed
                    if duration == 0.0:
                        if file_metadata.file_type == "video":
                            video_features = extract_video_features(file_path)
                            duration = video_features.get("duration", 0.0)
                        else:
                            audio_features = extract_audio_features(file_path)
                            duration = audio_features.get("duration", 0.0)
                    
                    if duration > 0:
                        file_metadata.duration = duration
                        print(f"[METADATA] ✓ Saved duration: {duration:.2f} seconds ({int(duration // 60)}:{int(duration % 60):02d})")
                    else:
                        print(f"[METADATA] Warning: Could not extract duration (got {duration})")
                except Exception as e:
                    print(f"[METADATA] Warning: Failed to extract duration: {e}")
                    import traceback
                    traceback.print_exc()
            
            db.commit()
        
    except Exception as e:
        print(f"Error in transcription task: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database
    init_db()
    # Start Celery worker
    celery_app.start()

