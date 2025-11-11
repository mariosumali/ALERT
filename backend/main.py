from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, moments, transcribe, chat

app = FastAPI(title="Multimedia Event Parsing Platform", version="1.0.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(moments.router, prefix="/api", tags=["moments"])
app.include_router(transcribe.router, prefix="/api", tags=["transcribe"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Multimedia Event Parsing Platform API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

