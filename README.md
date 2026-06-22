# ALERT — Audio-Visual Log Event Recognition Toolkit

**Created by Mario Sumali**

An investigative workspace for analyzing body camera and dash cam footage. Upload video, get automated transcription, audio event detection, and AI-powered analysis — all in one view.

![ALERT Screenshot](docs/alert-screenshot.png)

## Demo Video

[![ALERT Demo](https://img.youtube.com/vi/qM6ZRfXLaUo/maxresdefault.jpg)](https://www.youtube.com/watch?v=qM6ZRfXLaUo)

*Click the thumbnail above to watch the full demo on YouTube.*

## Features

- **Automated transcription** — Speech-to-text synced to video playback.
- **Audio event detection** — Gunshots, profanity, anomalies, and more flagged with confidence scores.
- **Multimodal video analysis** — Gemini-powered analysis of video segments for scene classification, people counting, use-of-force detection, camera obfuscation, and more.
- **Agentic AI chat** — GPT orchestrator with Gemini visual QA: the AI can request and analyze specific video segments on demand to answer visual questions.
- **AI-powered analysis** — Ask questions, generate incident reports, and get contextual summaries.
- **Interactive timeline** — Color-coded event markers with click-to-seek navigation.
- **Searchable & filterable** — Full-text search across events and transcript.
- **Responsive UI** — Resizable layout with light and dark mode.

## Architecture

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, react-resizable-panels
- **Backend**: FastAPI (Python)
- **Transcription**: OpenAI Whisper API
- **Audio Analysis**: Librosa + custom detection (gunshot, profanity, anomaly, silence)
- **Video Analysis**: Google Gemini 2.5 Flash (structured video chunk analysis)
- **AI Chat**: GPT-4o-mini orchestrator with Gemini visual QA tool calling (agentic loop)
- **OCR**: Frame extraction + metadata parsing
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Storage**: Local filesystem

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── celery_worker.py         # Celery async tasks
│   ├── routes/
│   │   ├── upload.py            # /upload, /files, /transcribe, /chat endpoints
│   │   └── moments.py           # /moments endpoint
│   ├── models/
│   │   ├── database.py          # SQLAlchemy setup
│   │   └── schema.py            # Database models
│   ├── services/
│   │   ├── transcription.py     # Whisper transcription
│   │   ├── audio_anomaly_detection.py
│   │   ├── gunshot_detection.py
│   │   ├── profanity_detection.py
│   │   ├── ocr_extraction.py    # Video frame OCR
│   │   ├── gpt_event_detection.py
│   │   ├── gemini_client.py     # Gemini API wrapper (structured + free-form)
│   │   ├── video_chunking.py    # ffmpeg video segmentation
│   │   └── segment_analysis.py  # Multimodal segment metadata extraction
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main layout
│   │   ├── components/
│   │   │   ├── CaseHeader.tsx   # Header bar + metadata popover
│   │   │   ├── VideoPlayer.tsx  # Video + timeline + controls
│   │   │   ├── EventPanel.tsx   # Left sidebar events list
│   │   │   ├── TranscriptPanel.tsx
│   │   │   ├── AIAssistant.tsx  # Right sidebar AI chat
│   │   │   └── ProcessingPipeline.tsx
│   │   ├── contexts/
│   │   │   ├── VideoContext.tsx  # Shared video state
│   │   │   └── ThemeContext.tsx  # Light/dark mode
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An OpenAI API key (for transcription and AI chat)
- OR for local development: Python 3.11+, Node.js 18+, PostgreSQL, Redis, plus
  the system tools `ffmpeg`, `tesseract-ocr`, and `libsndfile`
  (macOS: `brew install ffmpeg tesseract libsndfile`).

### Option 1: Docker Compose (Recommended)

1. **Set up your API keys:**
   ```bash
   cp .env.example .env
   # then edit .env and fill in OPENAI_API_KEY (and GEMINI_API_KEY if desired)
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

   The backend creates its database tables automatically on startup.

3. **Open the app:**
   - Frontend: http://localhost:5001
   - API docs: http://localhost:8000/docs

> The schema is auto-created on startup. To (re)initialize it manually:
> `docker-compose exec backend python init_db.py`

### Option 2: Local Development

#### Backend

```bash
cd backend
cp ../.env.example ../.env      # fill in your keys
pip install -r requirements.txt
createdb multimedia_events
redis-server &
uvicorn main:app --reload &      # tables are created on startup
celery -A celery_worker.celery_app worker --loglevel=info
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usage

1. **Upload footage** — Click "Upload Footage" or drag and drop a video/audio file.
2. **Watch processing** — The pipeline indicator shows transcription, audio analysis, and event detection progress.
3. **Review events** — The left panel lists detected events with category badges, timestamps, confidence scores, and expandable descriptions. Filter by type or search.
4. **Read the transcript** — The bottom center panel shows the full transcript synced to playback. Click any line to seek. Active lines highlight automatically.
5. **Ask the AI** — The right panel provides contextual analysis. Use quick prompts or type custom questions. Generate incident summaries, timelines, or reports.
6. **Navigate** — Click event markers on the timeline, use keyboard shortcuts, or adjust playback speed.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `K` or `Space` | Play / Pause |
| `J` | Skip back 5s |
| `L` | Skip forward 5s |
| `Q` | Jump to previous event |
| `E` | Jump to next event |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a video/audio file |
| `GET` | `/api/moments` | Get detected events (optional `?file_id=`) |
| `GET` | `/api/segments?file_id=` | Get Gemini video segment analysis |
| `GET` | `/api/files/{id}/metadata` | Get file metadata + OCR data |
| `GET` | `/api/transcribe?file_id=` | Get transcription segments |
| `POST` | `/api/chat` | Chat with AI about the footage (agentic when Gemini enabled) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Required for transcription and AI chat | — |
| `GEMINI_API_KEY` | Google Gemini API key (enables multimodal video analysis) | — |
| `ENABLE_GEMINI_ANALYSIS` | Toggle Gemini video analysis on/off | `false` |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.5-flash` |
| `VIDEO_CHUNK_SECONDS` | Duration of video chunks for analysis | `300` (5 min) |
| `OPENAI_CHAT_MODEL` | Chat model used by the AI assistant | `gpt-4o-mini` |
| `MAX_UPLOAD_MB` | Maximum upload size in MB | `2048` |
| `CORS_ALLOW_ORIGINS` | Comma-separated allowed browser origins | `http://localhost:5001,http://localhost:5173` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/multimedia_events` |
| `CELERY_BROKER_URL` | Redis broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis result backend | `redis://localhost:6379/0` |
| `VITE_API_BASE_URL` | Backend API URL (frontend) | `/api` |

See [`.env.example`](.env.example) for a copy-paste template.

## Testing

```bash
# Backend — pure-Python unit tests (no ML stack required)
cd backend
pip install pytest
pytest

# Frontend — type-check and production build
cd frontend
npm install
npx tsc --noEmit
npm run build
```

Continuous integration runs both suites on every push and pull request
(see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## License

MIT
