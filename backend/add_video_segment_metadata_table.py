"""
Migration: Create the video_segment_metadata table for Gemini multimodal analysis results.
"""

from models.database import engine
from sqlalchemy import text


def create_video_segment_metadata_table():
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS video_segment_metadata (
                    id SERIAL PRIMARY KEY,
                    file_id UUID NOT NULL,
                    segment_idx INTEGER NOT NULL,
                    start_sec DOUBLE PRECISION NOT NULL,
                    end_sec DOUBLE PRECISION NOT NULL,
                    scene_type VARCHAR,
                    time_of_day VARCHAR,
                    lighting VARCHAR,
                    weather VARCHAR,
                    camera_motion VARCHAR,
                    camera_obfuscation_present BOOLEAN DEFAULT FALSE,
                    officers_count INTEGER DEFAULT 0,
                    civilians_count INTEGER DEFAULT 0,
                    use_of_force_present BOOLEAN DEFAULT FALSE,
                    use_of_force_types JSON,
                    potential_excessive_force BOOLEAN DEFAULT FALSE,
                    key_moments_summary TEXT,
                    summary TEXT,
                    raw_metadata JSON
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_vsm_file_id ON video_segment_metadata (file_id)"
            ))
            conn.commit()
            print("Successfully created video_segment_metadata table.")
        except Exception as e:
            print(f"Error creating video_segment_metadata table: {e}")


if __name__ == "__main__":
    create_video_segment_metadata_table()
