"""
Initialize the database by creating all tables.
Run this script once to set up the database schema.
"""

from models.database import init_db
# Import models so they register with Base.metadata
from models import schema

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

