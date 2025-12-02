from models.database import engine
from sqlalchemy import text

def add_status_column():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE file_metadata ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending'"))
            conn.commit()
            print("Successfully added status column to file_metadata table.")
        except Exception as e:
            print(f"Error adding status column: {e}")

if __name__ == "__main__":
    add_status_column()
