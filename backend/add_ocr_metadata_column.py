"""
Add ocr_metadata column to file_metadata table.
This script adds a JSON column to store OCR-extracted metadata from video frames.
"""

from models.database import engine, SessionLocal
from sqlalchemy import text

def add_ocr_metadata_column():
    """Add ocr_metadata column to file_metadata table"""
    
    db = SessionLocal()
    try:
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='file_metadata' AND column_name='ocr_metadata'
        """)
        result = db.execute(check_query).fetchone()
        
        if result:
            print("[MIGRATION] ocr_metadata column already exists, skipping...")
            return
        
        # Add the column
        alter_query = text("""
            ALTER TABLE file_metadata 
            ADD COLUMN ocr_metadata JSON
        """)
        
        db.execute(alter_query)
        db.commit()
        
        print("[MIGRATION] ✓ Successfully added ocr_metadata column to file_metadata table")
        
    except Exception as e:
        db.rollback()
        print(f"[MIGRATION] ✗ Error adding ocr_metadata column: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("[MIGRATION] Adding ocr_metadata column...")
    add_ocr_metadata_column()
