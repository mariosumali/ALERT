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


def save_ocr_metadata(file_id: str, file_path: str, ocr_metadata: dict, file_metadata: FileMetadata):
    """
    Save OCR extracted metadata to a file.
    """
    try:
        # Create ocr_data directory
        # file_path is typically ./uploads/{file_id}.mp4
        # We want backend/ocr_data/
        uploads_dir = os.path.dirname(os.path.abspath(file_path))
        ocr_data_dir = os.path.join(uploads_dir, "..", "ocr_data")
        ocr_data_dir = os.path.abspath(ocr_data_dir)
        os.makedirs(ocr_data_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ocr_file = os.path.join(ocr_data_dir, f"{file_id}_{timestamp}.txt")
        
        with open(ocr_file, "w", encoding="utf-8") as f:
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
            f.write(f"File Path: {file_path}\n")
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
        
        print(f"[OCR FILE] Saved to: {ocr_file}")
        return ocr_file
        
    except Exception as e:
        print(f"[OCR FILE] Error: {e}")
        raise


def save_moments_of_interest(file_id: str, file_path: str, moments: list, file_metadata: FileMetadata):
    """
    Save detected moments of interest to a file.
    """
    try:
        # Create moments directory
        # file_path is typically ./uploads/{file_id}.mp4
        # We want backend/moments/
        uploads_dir = os.path.dirname(os.path.abspath(file_path))
        moments_dir = os.path.join(uploads_dir, "..", "moments")
        moments_dir = os.path.abspath(moments_dir)
        os.makedirs(moments_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        moments_file = os.path.join(moments_dir, f"{file_id}_{timestamp}.txt")
        
        with open(moments_file, "w", encoding="utf-8") as f:
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
            f.write(f"File Path: {file_path}\n")
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
            
            if moments:
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
            else:
                f.write("No moments of interest detected.\n")
        
        print(f"[MOMENTS FILE] Saved to: {moments_file}")
        return moments_file
        
    except Exception as e:
        print(f"[MOMENTS FILE] Error: {e}")
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
        
        # Update status to processing_transcription
        file_metadata.status = "processing_transcription"
        db.commit()
        
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
            file_metadata.status = "failed"
            db.commit()
            raise exc
        finally:
            # Persist whatever we have so the UI reflects the latest status
            file_metadata.transcript = transcript_text
            file_metadata.transcript_segments = transcript_segments
            db.commit()
        
        
        # Perform OCR extraction if it's a video file
        if file_metadata.file_type == "video":
            from services.ocr_extraction import extract_metadata_from_video
            print(f"[OCR] Extracting metadata from video frames for {file_id}...")
            try:
                ocr_metadata = extract_metadata_from_video(file_path)
                # Check if we have any useful metadata (raw_text or any other field)
                has_metadata = ocr_metadata and (
                    ocr_metadata.get("raw_text") or 
                    ocr_metadata.get("timestamp") or 
                    ocr_metadata.get("device_id") or 
                    ocr_metadata.get("device_model") or 
                    ocr_metadata.get("badge_number") or 
                    ocr_metadata.get("officer_id")
                )
                
                if has_metadata:
                    file_metadata.ocr_metadata = ocr_metadata
                    db.commit()
                    print(f"[OCR] ✓ Extracted metadata for file {file_id}:")
                    for key, value in ocr_metadata.items():
                        if value and key != "raw_text":
                            print(f"[OCR]   {key}: {value}")
                    
                    # Save OCR metadata to file
                    try:
                        print(f"[OCR FILE] Saving OCR metadata to file...")
                        save_ocr_metadata(
                            file_id=file_id,
                            file_path=file_path,
                            ocr_metadata=ocr_metadata,
                            file_metadata=file_metadata
                        )
                        print(f"[OCR FILE] ✓ OCR file saved")
                    except Exception as e:
                        print(f"[OCR FILE] ⚠ Error saving OCR file: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[OCR] No metadata found in video frames for file {file_id}")
            except Exception as e:
                print(f"[OCR] ⚠ Error during OCR extraction for file {file_id}: {e}")
                import traceback
                traceback.print_exc()
        
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
        
        # Update status to processing_audio
        file_metadata.status = "processing_audio"
        db.commit()

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
        
        # Store audio anomalies as MomentOfInterest records
        if audio_anomalies:
            from models.schema import MomentOfInterest
            print(f"[MOMENTS] Storing {len(audio_anomalies)} audio anomalies as moments...")
            
            stored_count = 0
            for anomaly in audio_anomalies:
                try:
                    # Only store high-confidence anomalies (≥0.8)
                    if anomaly.get('confidence', 0.0) >= 0.8:
                        moment = MomentOfInterest(
                            file_id=file_id,
                            start_time=anomaly['start_time'],
                            end_time=anomaly['end_time'],
                            event_types=[anomaly['category']],  # e.g., ["LoudSound", "Distortion"]
                            interest_score=anomaly['confidence'],
                            description=anomaly['description']
                        )
                        db.add(moment)
                        stored_count += 1
                        print(f"[MOMENTS]   - {anomaly['category']} at {anomaly['start_time']:.1f}s-{anomaly['end_time']:.1f}s (confidence: {anomaly['confidence']:.2f})")
                except Exception as e:
                    print(f"[MOMENTS] ⚠ Failed to store moment: {e}")
            
            if stored_count > 0:
                db.commit()
                print(f"[MOMENTS] ✓ Stored {stored_count} moments in database")
                
                # Save moments to file
                try:
                    # Query the stored moments from database
                    stored_moments = db.query(MomentOfInterest).filter(MomentOfInterest.file_id == file_id).all()
                    print(f"[MOMENTS FILE] Saving {len(stored_moments)} moments to file...")
                    save_moments_of_interest(
                        file_id=file_id,
                        file_path=file_path,
                        moments=stored_moments,
                        file_metadata=file_metadata
                    )
                    print(f"[MOMENTS FILE] ✓ Moments file saved")
                except Exception as e:
                    print(f"[MOMENTS FILE] ⚠ Error saving moments file: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[MOMENTS] No high-confidence anomalies to store")
        
        # Detect gunshots from transcript mentions and frequency analysis
        gunshot_events = []
        if transcript_segments and (extracted_audio_path or file_metadata.file_type == "audio"):
            from services.gunshot_detection import detect_gunshots_from_transcript
            print(f"[GUNSHOT DETECTION] Analyzing transcript for gunshot mentions...")
            try:
                audio_path_for_gunshot = extracted_audio_path if extracted_audio_path else file_path
                gunshot_events = detect_gunshots_from_transcript(
                    transcript_segments=transcript_segments,
                    audio_path=audio_path_for_gunshot,
                    duration=file_metadata.duration or 0.0
                )
                print(f"[GUNSHOT DETECTION] ✓ Found {len(gunshot_events)} gunshot events")
            except Exception as e:
                print(f"[GUNSHOT DETECTION] ⚠ Error detecting gunshots: {e}")
                import traceback
                traceback.print_exc()
        
        # Store gunshot events as MomentOfInterest records
        if gunshot_events:
            from models.schema import MomentOfInterest
            print(f"[GUNSHOT DETECTION] Storing {len(gunshot_events)} gunshot events as moments...")
            
            stored_gunshot_count = 0
            for event in gunshot_events:
                try:
                    # Only store high-confidence events (≥0.7 for gunshots)
                    if event.get('confidence', 0.0) >= 0.7:
                        moment = MomentOfInterest(
                            file_id=file_id,
                            start_time=event['start_time'],
                            end_time=event['end_time'],
                            event_types=["Gunshot"],
                            interest_score=event['confidence'],
                            description=event['description']
                        )
                        db.add(moment)
                        stored_gunshot_count += 1
                        print(f"[GUNSHOT DETECTION]   - Gunshot at {event['start_time']:.1f}s-{event['end_time']:.1f}s (confidence: {event['confidence']:.2f})")
                except Exception as e:
                    print(f"[GUNSHOT DETECTION] ⚠ Failed to store gunshot moment: {e}")
            
            if stored_gunshot_count > 0:
                db.commit()
                print(f"[GUNSHOT DETECTION] ✓ Stored {stored_gunshot_count} gunshot moments in database")
        
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
        
        # Update status to completed
        file_metadata.status = "completed"
        db.commit()

    except Exception as e:
        print(f"Error processing file {file_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Try to update status to failed
        try:
            if 'db' in locals():
                file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
                if file_metadata:
                    file_metadata.status = "failed"
                    db.commit()
        except:
            pass
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

