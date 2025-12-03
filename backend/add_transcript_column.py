"""
Add transcript_segments column to file_metadata table.
"""
from models.database import engine
from sqlalchemy import text

def add_column():
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='file_metadata' AND column_name='transcript_segments'
            """))
            if result.fetchone():
                print("Column already exists")
                return
            
            # Add column
            conn.execute(text("ALTER TABLE file_metadata ADD COLUMN transcript_segments JSON"))
            conn.commit()
            print("Column transcript_segments added successfully")
        except Exception as e:
            print(f"Error: {str(e)}")
            conn.rollback()

if __name__ == "__main__":
    add_column()

