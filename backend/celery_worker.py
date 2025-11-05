from celery import Celery
from models.database import SessionLocal, init_db
from models.schema import FileMetadata, MomentOfInterest
from services.transcription import transcribe_file_with_timestamps
from services.detect_events import detect_moments
import os

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
                f"Stored transcript for file {file_id} with {len(transcript_segments)} segments."
            )
        except Exception as exc:
            print(f"Transcription failed for file {file_id}: {exc}")
        finally:
            # Persist whatever we have so the UI reflects the latest status
            file_metadata.transcript = transcript_text
            file_metadata.transcript_segments = transcript_segments
            db.commit()
        
        # Detect moments
        print(f"Detecting moments for file {file_id}...")
        moments = detect_moments(file_path, file_metadata.file_type)
        
        # Save moments to database
        for moment_data in moments:
            moment = MomentOfInterest(
                file_id=file_id,
                start_time=moment_data["start_time"],
                end_time=moment_data["end_time"],
                event_types=moment_data["event_types"],
                interest_score=moment_data["interest_score"],
                description=moment_data["description"]
            )
            db.add(moment)
        
        db.commit()
        print(f"Processing complete for file {file_id}. Found {len(moments)} moments.")
        
    except Exception as e:
        print(f"Error processing file {file_id}: {str(e)}")
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

