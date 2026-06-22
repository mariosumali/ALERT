from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - defaults to PostgreSQL, can be overridden with env var
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/multimedia_events"
)

# pool_pre_ping recycles dead connections transparently (e.g. after the DB
# restarts or an idle connection is dropped), avoiding stale-connection errors
# in the long-lived Celery worker and API processes.
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Create all tables in the database.

    The model classes must be imported before ``create_all`` so they register
    themselves on ``Base.metadata``. Importing here makes ``init_db()`` work
    no matter how it is called (e.g. ``from models.database import init_db``),
    which the README and app startup both rely on.
    """
    from models import schema  # noqa: F401  (registers tables on Base.metadata)
    Base.metadata.create_all(bind=engine)

