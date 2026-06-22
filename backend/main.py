import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, moments, transcribe, chat, segments


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the database schema exists on startup (idempotent)."""
    try:
        from models.database import init_db
        init_db()
    except Exception as exc:  # pragma: no cover - startup best-effort
        # Don't crash the API if the DB is briefly unavailable; the schema can
        # also be created manually via `python init_db.py`.
        print(f"[startup] init_db skipped: {exc}")
    yield


app = FastAPI(
    title="ALERT — Audio-Visual Log Event Recognition Toolkit",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend access. Origins are configurable so the app can
# be deployed behind a real domain without code changes.
_default_origins = "http://localhost:5001,http://localhost:5173"
allow_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOW_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(moments.router, prefix="/api", tags=["moments"])
app.include_router(transcribe.router, prefix="/api", tags=["transcribe"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(segments.router, prefix="/api", tags=["segments"])

@app.get("/")
async def root():
    return {"message": "Multimedia Event Parsing Platform API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

