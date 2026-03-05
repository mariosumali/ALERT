from celery import Celery
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.database import SessionLocal, init_db
from models.schema import FileMetadata, MomentOfInterest
from services.transcription import transcribe_file_with_timestamps
from services.audio_anomaly_detection import extract_raw_audio_from_video, analyze_audio_anomalies
from utils.helpers import get_media_duration, format_duration
import os
import shutil
import tempfile
import datetime
import traceback

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

def _run_transcription(file_path):
    """Phase-1 helper: transcribe the file."""
    return transcribe_file_with_timestamps(file_path, use_mock=False)


def _run_ocr(file_path, file_type):
    """Phase-1 helper: extract OCR metadata from video frames."""
    if file_type != "video":
        return None
    from services.ocr_extraction import extract_metadata_from_video
    return extract_metadata_from_video(file_path)


def _run_duration(file_path):
    """Phase-1 helper: extract media duration."""
    return get_media_duration(file_path)


def _run_audio_extract(file_path, file_type):
    """Phase-1 helper: extract raw audio for downstream analysis."""
    temp_audio_dir = tempfile.mkdtemp(prefix="audio_analysis_")
    if file_type == "video":
        extracted = extract_raw_audio_from_video(file_path, temp_audio_dir)
        return extracted, temp_audio_dir
    return file_path, temp_audio_dir


def _store_events(db, file_id, events, event_type_label, min_confidence=0.6):
    """Store a list of detection events as MomentOfInterest rows. Returns count stored."""
    count = 0
    for event in events:
        try:
            if event.get("confidence", 0.0) < min_confidence:
                continue
            category = event.get("category") or event.get("event_types") or event_type_label
            if isinstance(category, list):
                etypes = category
            elif isinstance(category, str):
                etypes = [category]
            else:
                etypes = [event_type_label]
            moment = MomentOfInterest(
                file_id=file_id,
                start_time=event["start_time"],
                end_time=event["end_time"],
                event_types=etypes,
                interest_score=event.get("confidence", 0.7),
                description=event.get("description", ""),
            )
            db.add(moment)
            count += 1
        except Exception as e:
            print(f"[MOMENTS] ⚠ Failed to store {event_type_label} moment: {e}")
    return count


@celery_app.task(name="transcribe_and_detect")
def transcribe_and_detect_task(file_id: str, file_path: str):
    """
    Background task to transcribe file and detect moments of interest.
    Uses two parallel phases to maximise throughput.
    """
    temp_audio_dir = None
    extracted_audio_path = None
    try:
        db = SessionLocal()

        file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
        if not file_metadata:
            print(f"File {file_id} not found in database")
            return

        file_metadata.status = "processing_transcription"
        db.commit()

        # ── Phase 1: run independent I/O-bound tasks in parallel ──────────
        transcript_text = ""
        transcript_segments = []
        ocr_metadata = None
        duration = 0.0

        phase1_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_run_transcription, file_path): "transcription",
                executor.submit(_run_ocr, file_path, file_metadata.file_type): "ocr",
                executor.submit(_run_duration, file_path): "duration",
                executor.submit(_run_audio_extract, file_path, file_metadata.file_type): "audio_extract",
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    phase1_results[key] = future.result()
                except Exception as exc:
                    print(f"[PHASE 1] ⚠ {key} failed: {exc}")
                    traceback.print_exc()
                    phase1_results[key] = None

        # Unpack transcription
        if phase1_results.get("transcription"):
            transcript_text, transcript_segments = phase1_results["transcription"]
            print(f"✓ Transcription: {len(transcript_text)} chars, {len(transcript_segments)} segments")
        else:
            print("[PHASE 1] ⚠ Transcription produced no results")

        file_metadata.transcript = transcript_text
        file_metadata.transcript_segments = transcript_segments

        # Unpack OCR
        ocr_metadata = phase1_results.get("ocr")
        if ocr_metadata:
            has_metadata = any(ocr_metadata.get(k) for k in ("raw_text", "timestamp", "device_id", "device_model", "badge_number", "officer_id"))
            if has_metadata:
                file_metadata.ocr_metadata = ocr_metadata
                print(f"[OCR] ✓ Metadata extracted")
                try:
                    save_ocr_metadata(file_id, file_path, ocr_metadata, file_metadata)
                except Exception as e:
                    print(f"[OCR FILE] ⚠ Error saving OCR file: {e}")

        # Unpack duration
        duration = phase1_results.get("duration") or 0.0
        if duration > 0:
            file_metadata.duration = duration
            print(f"[METADATA] ✓ Duration: {duration:.2f}s")

        # Unpack audio extraction
        audio_result = phase1_results.get("audio_extract")
        if audio_result:
            extracted_audio_path, temp_audio_dir = audio_result
            print(f"[AUDIO] ✓ Audio extracted to {extracted_audio_path}")
        else:
            extracted_audio_path = file_path if file_metadata.file_type == "audio" else None

        db.commit()

        # ── Phase 2: run detection algorithms in parallel ─────────────────
        file_metadata.status = "processing_audio"
        db.commit()

        audio_anomalies = []
        gunshot_events = []
        profanity_events = []
        gpt_events = []

        def _detect_audio_anomalies():
            if extracted_audio_path:
                return analyze_audio_anomalies(extracted_audio_path)
            return []

        def _detect_gunshots():
            if not transcript_segments or not extracted_audio_path:
                return []
            from services.gunshot_detection import detect_gunshots_from_transcript
            return detect_gunshots_from_transcript(
                transcript_segments=transcript_segments,
                audio_path=extracted_audio_path,
                duration=duration,
            )

        def _detect_profanity():
            if not transcript_segments:
                return []
            from services.profanity_detection import detect_profanity_from_transcript
            return detect_profanity_from_transcript(
                transcript_segments=transcript_segments,
                duration=duration,
            )

        def _detect_gpt_events():
            if not transcript_segments:
                return []
            try:
                from services.gpt_event_detection import detect_events_from_transcript
                return detect_events_from_transcript(
                    transcript_segments=transcript_segments,
                    duration=duration,
                )
            except Exception as e:
                print(f"[GPT EVENTS] ⚠ {e}")
                return []

        phase2_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_detect_audio_anomalies): "audio_anomalies",
                executor.submit(_detect_gunshots): "gunshot",
                executor.submit(_detect_profanity): "profanity",
                executor.submit(_detect_gpt_events): "gpt_events",
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    phase2_results[key] = future.result()
                except Exception as exc:
                    print(f"[PHASE 2] ⚠ {key} failed: {exc}")
                    traceback.print_exc()
                    phase2_results[key] = []

        audio_anomalies = phase2_results.get("audio_anomalies", [])
        gunshot_events = phase2_results.get("gunshot", [])
        profanity_events = phase2_results.get("profanity", [])
        gpt_events = phase2_results.get("gpt_events", [])

        print(f"[PHASE 2] Results: {len(audio_anomalies)} audio anomalies, "
              f"{len(gunshot_events)} gunshots, {len(profanity_events)} profanity, "
              f"{len(gpt_events)} GPT events")

        # ── Store all detected moments ────────────────────────────────────
        total_stored = 0
        total_stored += _store_events(db, file_id, audio_anomalies, "AudioAnomaly", min_confidence=0.6)
        total_stored += _store_events(db, file_id, gunshot_events, "Gunshot", min_confidence=0.6)
        total_stored += _store_events(db, file_id, profanity_events, "Profanity", min_confidence=0.6)
        total_stored += _store_events(db, file_id, gpt_events, "Event", min_confidence=0.5)

        if total_stored > 0:
            db.commit()
            print(f"[MOMENTS] ✓ Stored {total_stored} total moments")

            try:
                stored_moments = db.query(MomentOfInterest).filter(MomentOfInterest.file_id == file_id).all()
                save_moments_of_interest(file_id, file_path, stored_moments, file_metadata)
                print(f"[MOMENTS FILE] ✓ Saved")
            except Exception as e:
                print(f"[MOMENTS FILE] ⚠ {e}")

        # Save transcript file
        try:
            save_comprehensive_transcript(
                file_id, file_path, transcript_text,
                transcript_segments, audio_anomalies, file_metadata,
            )
            print(f"[TRANSCRIPT FILE] ✓ Saved")
        except Exception as e:
            print(f"[TRANSCRIPT FILE] ⚠ {e}")

        file_metadata.status = "completed"
        db.commit()

    except Exception as e:
        print(f"Error processing file {file_id}: {e}")
        traceback.print_exc()
        try:
            if "db" in locals():
                file_metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
                if file_metadata:
                    file_metadata.status = "failed"
                    db.commit()
        except Exception:
            pass
    finally:
        # Cleanup temp audio
        if extracted_audio_path and extracted_audio_path != file_path:
            try:
                if os.path.exists(extracted_audio_path):
                    os.unlink(extracted_audio_path)
            except Exception:
                pass
        if temp_audio_dir and os.path.exists(temp_audio_dir):
            try:
                shutil.rmtree(temp_audio_dir)
            except Exception:
                pass
        if "db" in locals():
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

