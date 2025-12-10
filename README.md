# ALERT — Audio-Visual Log Event Recognition Toolkit
# Created by Mario Sumali & Shane Mion

A toolkit for uploading, transcribing, and detecting events in long audio/video files, with a searchable web UI.

## 🎥 Demo Video

[![ALERT Demo](https://img.youtube.com/vi/qM6ZRfXLaUo/maxresdefault.jpg)](https://www.youtube.com/watch?v=qM6ZRfXLaUo)

*Click the thumbnail above to watch the full demo on YouTube.*

## Architecture

- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI (Python)
- **Transcription**: OpenAI Whisper API (with mock fallback)
- **Event Detection**: PyTorch (with placeholder model)
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Storage**: Local filesystem (S3 optional)

## Project Structure

```
├── backend/
│   ├── main.py               # FastAPI entrypoint
│   ├── routes/
│   │   ├── upload.py         # /upload endpoint
│   │   ├── moments.py        # /moments endpoint
│   ├── models/
│   │   ├── database.py       # SQLAlchemy setup
│   │   ├── schema.py         # Database models
│   ├── services/
│   │   ├── transcription.py  # Whisper wrapper
│   │   ├── audio_features.py # Audio feature extraction
│   │   ├── video_features.py # Video feature extraction
│   │   ├── detect_events.py  # Event detection (dummy implementation)
│   │   ├── train_event_detector.py # Model training script
│   ├── utils/
│   │   ├── s3_client.py      # S3 utilities
│   │   ├── helpers.py
│   ├── celery_worker.py      # Celery async tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadForm.tsx
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── MomentDropdown.tsx
│   │   ├── pages/
│   │   │   ├── index.tsx (App.tsx)
│   │   ├── utils/
│   │   │   ├── api.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Create a `.env` file with `OPENAI_API_KEY=your-key`
- OR Python 3.11+, Node.js 18+, PostgreSQL, Redis

### Option 1: Docker Compose (Recommended)

1. **Set up OpenAI API Key (for transcription):**
   ```bash
   # Get your API key from: https://platform.openai.com/api-keys
   export OPENAI_API_KEY="your-api-key-here"
   ```
   
   Alternatively, create a `.env` file in the project root:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```
   
   **Note:** If you don't set the API key, the system will use mock transcription (fast but not real).

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Initialize database:**
   ```bash
   docker-compose exec backend python -c "from models.database import init_db; init_db()"
   ```

4. **Access the application:**
   - Frontend: http://localhost:5001
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option 2: Local Development

#### Backend Setup

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL:**
   ```bash
   # Create database
   createdb multimedia_events
   ```

3. **Initialize database:**
   ```bash
   python -c "from models.database import init_db; init_db()"
   ```

4. **Start Redis:**
   ```bash
   redis-server
   ```

5. **Start FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```

6. **Start Celery worker (in another terminal):**
   ```bash
   celery -A celery_worker.celery_app worker --loglevel=info
   ```

#### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

## Usage

1. **Upload a video/audio file** through the web UI
2. The backend will:
   - Save the file
   - Launch a Celery task to transcribe and detect events
   - Return 3 dummy moments (for testing)
3. **View detected moments** in the dropdown
4. **Filter by event type** (Gunshot, Silence, Motion, etc.)
5. **Click a moment** to seek the video player to that timestamp

## API Endpoints

### POST /api/upload
Upload a video/audio file.

**Request:** Multipart form data with `file` field

**Response:**
```json
{
  "file_id": "uuid",
  "message": "File uploaded successfully. Processing started.",
  "status": "processing"
}
```

### GET /api/moments
Get detected moments of interest.

**Query Parameters:**
- `file_id` (optional): Filter by file ID

**Response:**
```json
{
  "moments": [
    {
      "moment_id": "uuid",
      "file_id": "uuid",
      "start_time": 5.0,
      "end_time": 8.0,
      "event_types": ["Gunshot"],
      "interest_score": 0.95,
      "description": "Loud noise detected, possible gunshot"
    }
  ],
  "count": 1
}
```

## Model Training (BETA FEATURE)

To train the event detector model:

1. **Prepare labeled CSV** with columns: `file_id`, `start_time`, `end_time`, `event_type`

2. **Run training:**
   ```bash
   python backend/services/train_event_detector.py labeled_data.csv
   ```

3. **Model will be saved** to `backend/models/event_detector.pt`

4. **Update `detect_events.py`** to load and use the trained model

## Environment Variables

### Backend
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost:5432/multimedia_events`)
- `CELERY_BROKER_URL`: Redis broker URL (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND`: Redis result backend (default: `redis://localhost:6379/0`)
- `AWS_ACCESS_KEY_ID`: Optional, for S3 storage
- `AWS_SECRET_ACCESS_KEY`: Optional, for S3 storage
- `AWS_REGION`: Optional, for S3 storage

### Frontend
- `VITE_API_BASE_URL`: Backend API URL (default: `/api`)

- File uploads are stored in `./uploads` directory
- Database migrations are handled via SQLAlchemy's `create_all()`

## License

MIT

