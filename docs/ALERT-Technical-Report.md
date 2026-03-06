# ALERT — Technical Report

## Automated Law Enforcement Review Technology

**Version:** 1.0.0
**Date:** March 2026
**Authors:** Mario Sumali

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Infrastructure & Deployment](#3-infrastructure--deployment)
4. [Backend API Layer](#4-backend-api-layer)
5. [Database Schema & Data Model](#5-database-schema--data-model)
6. [The Agentic Processing Pipeline](#6-the-agentic-processing-pipeline)
7. [Phase 1: Parallel Ingestion & Feature Extraction](#7-phase-1-parallel-ingestion--feature-extraction)
8. [Phase 2: Multi-Modal Event Detection](#8-phase-2-multi-modal-event-detection)
9. [Phase 3: Visual Segment Analysis via Gemini](#9-phase-3-visual-segment-analysis-via-gemini)
10. [Transcription Engine](#10-transcription-engine)
11. [Audio Analysis & Anomaly Detection](#11-audio-analysis--anomaly-detection)
12. [Gunshot Detection System](#12-gunshot-detection-system)
13. [Profanity Detection](#13-profanity-detection)
14. [GPT-Powered Transcript Event Detection](#14-gpt-powered-transcript-event-detection)
15. [OCR & Metadata Extraction](#15-ocr--metadata-extraction)
16. [Agentic Chat System](#16-agentic-chat-system)
17. [Frontend Architecture](#17-frontend-architecture)
18. [Real-Time Synchronization & Reactive UI](#18-real-time-synchronization--reactive-ui)
19. [Event Classification & Taxonomy](#19-event-classification--taxonomy)
20. [Security, Configuration & Environment](#20-security-configuration--environment)
21. [Appendix: Full API Reference](#21-appendix-full-api-reference)

---

## 1. Executive Summary

ALERT (Automated Law Enforcement Review Technology) is a full-stack, AI-powered multimedia analysis platform designed for automated review and annotation of law enforcement body-worn camera (BWC) footage. The system ingests video or audio files and autonomously runs a multi-phase, multi-modal detection pipeline that combines:

- **Speech-to-text transcription** via OpenAI Whisper with intelligent chunking and deduplication
- **Statistical audio signal analysis** using librosa for anomaly detection (loud sounds, silence, distortion, frequency anomalies, sudden changes)
- **Acoustic gunshot detection** combining transcript keyword matching with spectral frequency analysis
- **NLP-based profanity detection** via regex pattern matching with temporal grouping
- **LLM-powered semantic event detection** using GPT-4o-mini for high-level event classification from transcripts
- **Visual scene understanding** via Google Gemini 2.5 Flash for structured video analysis (use of force, scene context, camera obfuscation)
- **An agentic chat interface** that orchestrates GPT-4o-mini and Gemini in a tool-calling loop for interactive video Q&A

The platform processes a 16-minute BWC video in approximately 8–12 minutes, producing a comprehensive event timeline, searchable transcript, structured scene metadata, and an interactive AI assistant — all through a modern, reactive web interface.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Browser                             │
│                                                                     │
│   ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│   │  Video    │  │  Event   │  │ Transcript│  │  AI Assistant    │  │
│   │  Player   │  │  Panel   │  │  Panel    │  │  (Agentic Chat)  │  │
│   └────┬─────┘  └────┬─────┘  └─────┬─────┘  └───────┬──────────┘   │
│        │              │              │                 │            │
│        └──────────────┴──────────────┴─────────────────┘            │
│                              │                                      │
│                    React 18 + Vite + Tailwind                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP (Proxy :5001 → :8000)
┌──────────────────────────────┴───────────────────────────────────────┐
│                         FastAPI Backend (:8000)                      │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Upload   │ │ Moments  │ │Transcribe│ │  Chat    │ │ Segments │    │
│  │ Router   │ │ Router   │ │ Router   │ │ Router   │ │ Router   │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       │             │            │             │            │        │
│       └─────────────┴────────────┴─────────────┴────────────┘        │
│                              │                                       │
│                    SQLAlchemy ORM + PostgreSQL                       │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ Celery Task Dispatch
┌──────────────────────────────┴────────────────────────────────────────┐
│                       Celery Worker Cluster                           │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                  transcribe_and_detect_task                     │  │
│  │                                                                 │  │
│  │  Phase 1 (Parallel I/O)    Phase 2 (Parallel Detection)         │  │
│  │  ┌──────────────────┐      ┌─────────────────────────┐          │  │
│  │  │ Transcription    │      │ Audio Anomaly Detection │          │  │
│  │  │ OCR Extraction   │      │ Gunshot Detection       │          │  │
│  │  │ Duration Probe    │      │ Profanity Detection     │          │  │
│  │  │ Audio Extraction  │      │ GPT Event Detection     │          │  │
│  │  └──────────────────┘      └─────────────────────────┘          │  │
│  │                                                                  │  │
│  │  Phase 3 (Sequential Gemini)                                     │  │
│  │  ┌──────────────────────────────────────────────────┐           │  │
│  │  │ Video Chunking → Gemini Structured Analysis      │           │  │
│  │  │ → Scene Metadata → Force Detection → Moments     │           │  │
│  │  └──────────────────────────────────────────────────┘           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────┴─────┐         ┌─────┴─────┐         ┌──────┴──────┐
   │ Redis 7  │         │ Postgres  │         │ External AI │
   │ (Broker) │         │   15      │         │   APIs      │
   └──────────┘         └───────────┘         │             │
                                              │ OpenAI      │
                                              │ - Whisper   │
                                              │ - GPT-4o    │
                                              │ - GPT-4o-mini│
                                              │             │
                                              │ Google      │
                                              │ - Gemini    │
                                              │   2.5 Flash │
                                              └─────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Frontend** | React + TypeScript | 18.2.0 / 5.2.2 |
| **Build Tool** | Vite | 5.0.8 |
| **Styling** | Tailwind CSS | 3.3.6 |
| **Layout** | react-resizable-panels | 4.7.1 |
| **HTTP Client** | Axios | 1.6.2 |
| **Backend** | FastAPI + Uvicorn | 0.104.1 / 0.24.0 |
| **ORM** | SQLAlchemy | 2.0.23 |
| **Database** | PostgreSQL | 15 |
| **Task Queue** | Celery | 5.3.4 |
| **Message Broker** | Redis | 7 (Alpine) |
| **Audio Processing** | librosa + numpy | 0.10.1 / 1.24.3 |
| **Video Processing** | OpenCV + ffmpeg | 4.8.1.78 |
| **ML Framework** | PyTorch | 2.1.0 |
| **OCR** | Tesseract (pytesseract) | 0.3.10 |
| **AI - Transcription** | OpenAI Whisper API | whisper-1 |
| **AI - NLP** | OpenAI GPT-4o-mini | gpt-4o-mini |
| **AI - Vision** | OpenAI GPT-4o | gpt-4o |
| **AI - Video** | Google Gemini | 2.5 Flash |
| **Containerization** | Docker + Docker Compose | — |

### 2.3 Design Principles

- **Parallelism First**: All independent I/O and detection tasks run concurrently via `ThreadPoolExecutor` with 4 workers
- **Multi-Modal Fusion**: Audio, text, and visual signals are independently analyzed then merged into a unified event timeline
- **Progressive Status**: The UI polls the backend every 3 seconds and displays granular pipeline status (`processing_transcription` → `processing_audio` → `processing_video_analysis` → `completed`)
- **Agentic Architecture**: The chat system uses tool-calling to dynamically invoke Gemini on specific video segments, with deduplication and turn limits
- **Confidence-Gated Events**: All detected events must exceed configurable confidence thresholds before being stored (0.5–0.6 depending on source)

---

## 3. Infrastructure & Deployment

### 3.1 Docker Compose Services

The system runs as 5 containerized services:

| Service | Image | Port | Role |
|---------|-------|------|------|
| `db` | `postgres:15` | 5432 | Persistent storage, healthcheck via `pg_isready` |
| `redis` | `redis:7-alpine` | 6379 | Celery message broker + result backend, healthcheck via `redis-cli ping` |
| `backend` | Custom (python:3.11-slim) | 8000 | FastAPI API server, depends on db + redis healthy |
| `celery_worker` | Custom (python:3.11-slim) | — | Async task processing, depends on backend started |
| `frontend` | Custom (node:18-alpine) | 3000 | Vite production build serving React app |

### 3.2 Backend Dockerfile

```dockerfile
FROM python:3.11-slim
# System dependencies for audio/video/OCR processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    tesseract-ocr \
    tesseract-ocr-eng
# Whisper requires special install flags
RUN pip install --no-build-isolation openai-whisper==20231117
RUN pip install -r requirements.txt
```

Key decisions:
- **python:3.11-slim** balances image size with compatibility
- **ffmpeg** is required for audio extraction, video chunking, and duration probing
- **libsndfile1** is a runtime dependency for librosa/soundfile
- **tesseract-ocr** provides local OCR fallback capability
- **openai-whisper** is installed with `--no-build-isolation` due to build system conflicts with newer setuptools

### 3.3 Networking

All services share a Docker bridge network (`alert_default`). The frontend Vite dev server proxies `/api` requests to the backend container, enabling same-origin API calls from the browser. The local development server (port 5001) also proxies to the backend.

### 3.4 Volume Mounts

- `./backend:/app` — Backend source code (hot reload via Uvicorn `--reload`)
- `./uploads:/app/uploads` — Persistent video/audio file storage
- `postgres_data` — Named volume for database persistence

---

## 4. Backend API Layer

### 4.1 FastAPI Application Structure

The backend is organized into routers, services, models, and utilities:

```
backend/
├── main.py                          # App factory, CORS, router mounting
├── celery_worker.py                 # Task definitions, pipeline orchestration
├── init_db.py                       # Schema creation on startup
├── models/
│   ├── database.py                  # SQLAlchemy engine, SessionLocal
│   └── schema.py                    # ORM models
├── routes/
│   ├── upload.py                    # POST /upload, GET /files/{id}/metadata
│   ├── moments.py                   # GET /moments, GET /moments/download
│   ├── transcribe.py                # POST/GET /transcribe, downloads
│   ├── chat.py                      # POST /chat (agentic)
│   └── segments.py                  # GET /segments
├── services/                        # Business logic (detailed in sections 10–15)
└── utils/
    ├── helpers.py
    ├── timestamp_parser.py
    └── s3_client.py
```

### 4.2 CORS & Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.3 Request Flow

1. File uploaded via `POST /api/upload` → saved to `./uploads/{uuid}{ext}`
2. `FileMetadata` record created in PostgreSQL with `status=pending`
3. Celery task `transcribe_and_detect_task` dispatched asynchronously
4. Frontend polls `GET /api/files/{id}/metadata` (status) and `GET /api/moments` (results) every 3 seconds
5. Celery worker updates status through phases; stores events to `moments_of_interest` table
6. On `status=completed`, frontend stops polling and renders the full event timeline

---

## 5. Database Schema & Data Model

### 5.1 FileMetadata

The central record for each uploaded file:

| Column | Type | Description |
|--------|------|-------------|
| `file_id` | UUID (PK) | Unique file identifier, generated on upload |
| `path` | String | Filesystem path to the uploaded file |
| `file_type` | String | `"video"` or `"audio"` |
| `source_agency` | String (nullable) | Originating agency |
| `duration` | Float | Duration in seconds (from ffprobe) |
| `timestamp_start` | DateTime | Upload timestamp |
| `file_size` | Integer | File size in bytes |
| `original_filename` | String | Original filename from upload |
| `transcript` | Text | Full concatenated transcript text |
| `transcript_segments` | JSON | Array of `{start, end, text}` objects |
| `status` | String | Pipeline state machine (see below) |
| `ocr_metadata` | JSON | Extracted camera metadata |

**Status State Machine:**

```
pending → processing_transcription → processing_audio → processing_video_analysis → completed
                                                                                  → failed
```

### 5.2 MomentOfInterest

Each detected event is stored as a moment:

| Column | Type | Description |
|--------|------|-------------|
| `moment_id` | UUID (PK) | Unique moment identifier |
| `file_id` | UUID (FK) | Reference to FileMetadata |
| `start_time` | Float | Event start time in seconds |
| `end_time` | Float | Event end time in seconds |
| `event_types` | JSON | Array of type labels, e.g. `["Gunshot", "LoudSound"]` |
| `interest_score` | Float | Confidence score (0.0–1.0) |
| `description` | Text | Human-readable event description |

### 5.3 VideoSegmentMetadata

Structured output from Gemini visual analysis:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `file_id` | UUID (FK) | Reference to FileMetadata |
| `segment_idx` | Integer | Chunk index (0-based) |
| `start_sec` / `end_sec` | Float | Time range |
| `scene_type` | String | indoor, outdoor, vehicle, unknown |
| `time_of_day` | String | day, dusk, night, dawn, unknown |
| `lighting` | String | daylight, night, artificial, low_light, mixed, unknown |
| `weather` | String | clear, rain, snow, windy, fog, unknown |
| `camera_motion` | String | stable, walking, running, vehicle_moving, unknown |
| `camera_obfuscation_present` | Boolean | Whether camera was obstructed |
| `officers_count` / `civilians_count` | Integer | People counts |
| `use_of_force_present` | Boolean | Force detected |
| `use_of_force_types` | JSON | Array of force type labels |
| `potential_excessive_force` | Boolean | Flagged as potentially excessive |
| `key_moments_summary` | Text | Notable moments in segment |
| `summary` | Text | Narrative summary |
| `raw_metadata` | JSON | Complete Gemini response |

---

## 6. The Agentic Processing Pipeline

### 6.1 Pipeline Overview

The core of ALERT is the `transcribe_and_detect_task` Celery task — a three-phase, parallelized pipeline that orchestrates 8+ independent analysis modules:

```
Upload
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 1: Parallel Ingestion (ThreadPoolExecutor×4)  │
│                                                      │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────┐ │
│  │ Transcription │  │   OCR    │  │ Audio Extract │ │
│  │ (Whisper API) │  │ (GPT-4o) │  │  (ffmpeg)    │ │
│  └──────┬───────┘  └────┬─────┘  └──────┬───────┘ │
│         │               │               │          │
│  ┌──────┴───────┐       │        ┌──────┴───────┐  │
│  │   Duration   │       │        │  Raw WAV     │  │
│  │  (ffprobe)   │       │        │  44.1kHz     │  │
│  └──────────────┘       │        └──────────────┘  │
└─────────────┬───────────┴───────────────┬──────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 2: Parallel Detection (ThreadPoolExecutor×4)  │
│                                                      │
│  ┌─────────────────┐  ┌────────────────────────┐   │
│  │ Audio Anomalies  │  │ Gunshot Detection      │   │
│  │ (librosa/numpy)  │  │ (transcript + spectral)│   │
│  └─────────────────┘  └────────────────────────┘   │
│  ┌─────────────────┐  ┌────────────────────────┐   │
│  │ Profanity        │  │ GPT Event Detection    │   │
│  │ (regex patterns) │  │ (gpt-4o-mini)          │   │
│  └─────────────────┘  └────────────────────────┘   │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 3: Gemini Visual Analysis (Sequential)        │
│                                                      │
│  Video → ffmpeg chunk (5 min) → Gemini 2.5 Flash    │
│       → Structured JSON → Scene Metadata             │
│       → Use of Force → Moments                       │
│                                                      │
│  Repeat for each chunk (4 chunks for 16-min video)  │
└─────────────────────────────────────────────────────┘
              │
              ▼
         ┌─────────┐
         │Completed │
         └─────────┘
```

### 6.2 Parallelism Strategy

Each phase uses Python's `concurrent.futures.ThreadPoolExecutor` with `max_workers=4`:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    future_transcription = executor.submit(_run_transcription, ...)
    future_ocr = executor.submit(_run_ocr, ...)
    future_duration = executor.submit(_run_duration, ...)
    future_audio = executor.submit(_run_audio_extract, ...)
```

This is particularly effective because:
- **Phase 1** tasks are I/O-bound (API calls to Whisper, ffmpeg subprocess calls)
- **Phase 2** mixes I/O-bound (GPT API call) with CPU-bound (librosa analysis), which still benefits from threading due to the GIL being released during I/O
- **Phase 3** is sequential because Gemini API calls are rate-limited and each chunk depends on video slicing completing first

### 6.3 Error Handling & Resilience

- Each phase catches exceptions individually — a failure in OCR does not block transcription
- Failed tasks log warnings but allow the pipeline to continue with available data
- The file status is set to `failed` only if the entire pipeline crashes
- Individual detection modules return empty results on failure rather than raising

---

## 7. Phase 1: Parallel Ingestion & Feature Extraction

### 7.1 Transcription (`_run_transcription`)

Calls `transcribe_file_with_timestamps()` which routes to the configured provider (OpenAI Whisper by default). Returns `(full_text, segments[])`. See [Section 10](#10-transcription-engine) for full details.

### 7.2 OCR Extraction (`_run_ocr`)

Extracts camera metadata from video overlay text. Uses GPT-4o vision on frames at 30s, 60s, and 120s. Extracts: timestamp, device_id, device_model, badge_number, officer_id. See [Section 15](#15-ocr--metadata-extraction).

### 7.3 Duration Probing (`_run_duration`)

Uses ffprobe to extract media duration:

```python
def get_media_duration(file_path: str) -> float:
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())
```

### 7.4 Audio Extraction (`_run_audio_extract`)

Extracts raw audio for signal analysis using ffmpeg:

```
ffmpeg -i <input> -vn -acodec pcm_s16le -ar 44100 -ac 2 <output.wav>
```

Parameters: PCM 16-bit signed little-endian, 44.1 kHz sample rate, stereo. The higher sample rate (vs. 16 kHz for transcription) preserves frequency detail needed for spectral analysis and gunshot detection.

---

## 8. Phase 2: Multi-Modal Event Detection

Phase 2 runs four independent detection modules in parallel, each producing a list of events with timestamps and confidence scores.

### 8.1 Event Storage Strategy

All events flow through `_store_events()`:

```python
def _store_events(db, file_id, events, label, min_confidence=0.6):
    for event in events:
        if event['confidence'] >= min_confidence:
            moment = MomentOfInterest(
                file_id=file_id,
                start_time=event['start_time'],
                end_time=event['end_time'],
                event_types=event['event_types'],
                interest_score=event['confidence'],
                description=event.get('description', '')
            )
            db.add(moment)
```

Confidence thresholds by source:

| Source | Min Confidence | Rationale |
|--------|---------------|-----------|
| Audio Anomalies | 0.6 | Statistical methods have known false-positive rates |
| Gunshot Detection | 0.6 | Combined transcript+spectral reduces noise |
| Profanity | 0.6 | Regex patterns are high-precision |
| GPT Events | 0.5 | Lower threshold to capture semantic events that may have lower model confidence |
| Gemini Visual | 0.5 | Boolean flags from structured output converted to 0.8 confidence |

### 8.2 Results Aggregation

Phase 2 produces:

```python
results = {
    'audio_anomalies': 151,    # loud sounds, silence, frequency, etc.
    'gunshots': 1,              # transcript + spectral confirmed
    'profanity': 7,             # regex-detected instances
    'gpt_events': 8             # semantic events from GPT-4o-mini
}
```

---

## 9. Phase 3: Visual Segment Analysis via Gemini

### 9.1 Video Chunking Strategy

Long videos are split into analyzable chunks (default 5 minutes / 300 seconds):

```python
VIDEO_CHUNK_SECONDS = int(os.environ.get('VIDEO_CHUNK_SECONDS', '300'))
```

Chunking uses ffmpeg with optimized encoding:

```
ffmpeg -ss <start> -i <input> -t <duration> \
    -c:v libx264 -preset veryfast -crf 23 \
    -c:a aac -b:a 128k \
    <output.mp4>
```

- **libx264 veryfast** + **CRF 23**: Fast encoding with acceptable quality
- **AAC 128k**: Preserves speech intelligibility
- For Gemini upload, segments are further compressed: `scale=640`, 10 fps, target ~25 MB, AAC 32k mono 16 kHz

### 9.2 Gemini Structured Analysis

Each chunk is sent to Gemini 2.5 Flash with a law-enforcement-specific analysis prompt and a structured JSON schema (`LAW_ENFORCEMENT_SCHEMA`):

**Schema Fields:**

| Field | Type | Values |
|-------|------|--------|
| `scene_type` | enum | indoor, outdoor, vehicle, unknown |
| `time_of_day` | enum | day, dusk, night, dawn, unknown |
| `lighting` | enum | daylight, night, artificial, low_light, mixed, unknown |
| `weather` | enum | clear, rain, snow, windy, fog, unknown |
| `camera_motion` | enum | stable, walking, running, vehicle_moving, unknown |
| `camera_obfuscation_present` | boolean | — |
| `camera_obfuscation_spans` | array | `[{start, end, description}]` |
| `officers_count` | integer | — |
| `civilians_count` | integer | — |
| `use_of_force_present` | boolean | — |
| `use_of_force_types` | array | strings |
| `potential_excessive_force` | boolean | — |
| `key_moments` | array | `[{timestamp, description, severity}]` |
| `summary` | string | Narrative summary |

### 9.3 Timestamp Alignment

Gemini returns timestamps relative to each chunk's start. The system realigns them to global video time:

```python
def shift_timestamps_in_json(data, offset_seconds):
    # Recursively find timestamp fields (MM:SS, HH:MM:SS)
    # Add offset_seconds to each
```

### 9.4 Gemini → Moment Derivation

Structured Gemini output is converted to `MomentOfInterest` records:

- `use_of_force_present=True` → Event types: `["UseOfForce", "Force:{type}"]`, confidence 0.8
- `potential_excessive_force=True` → Event type: `["PotentialExcessiveForce"]`, confidence 0.8
- `camera_obfuscation_present=True` → One event per obfuscation span: `["CameraObfuscation"]`

---

## 10. Transcription Engine

### 10.1 Provider Hierarchy

The transcription service supports multiple backends with automatic fallback:

```
1. Mock (testing) ← USE_MOCK_TRANSCRIPTION=true
2. OpenAI Whisper API ← OPENAI_API_KEY set (default)
3. Local Whisper ← ENABLE_LOCAL_WHISPER=true
4. Mock (final fallback)
```

### 10.2 OpenAI Whisper Pipeline

This is the primary transcription path and involves several sophisticated steps:

#### Step 1: Audio Extraction

```
ffmpeg -i <video> -vn -acodec pcm_s16le -ar 16000 -ac 1 <output.wav>
```

- PCM 16-bit, 16 kHz mono — optimal for Whisper's training distribution
- Different from the 44.1 kHz extraction used for audio analysis

#### Step 2: Intelligent Chunking

Long audio is split into overlapping chunks to handle Whisper's context window:

| Parameter | Default | Env Variable |
|-----------|---------|-------------|
| Chunk duration | 60 seconds | `OPENAI_CHUNK_DURATION` |
| Overlap | 5 seconds | `OPENAI_CHUNK_OVERLAP` |
| Temperature | 0 | `OPENAI_TRANSCRIPTION_TEMPERATURE` |
| Max retries | 3 | `OPENAI_TRANSCRIPTION_MAX_RETRIES` |

Chunks are generated as:
```
[0s-60s], [55s-120s], [115s-180s], ...
```

The 5-second overlap ensures no speech at chunk boundaries is lost.

#### Step 3: Per-Chunk API Call

Each chunk attempts three response formats in order:

1. **SRT format** (preferred): Parsed with regex for precise timestamps
2. **verbose_json**: Contains native `segments` array with `start`/`end`/`text`
3. **json**: Plain text only — requires alignment (see below)

#### Step 4: RMS-Based Alignment (Fallback)

When only plain text is returned, the system aligns it against audio energy:

```python
def _align_transcript_with_audio(audio_path, text, chunk_start, chunk_end):
    y, sr = librosa.load(audio_path, sr=None)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    speech_threshold = max(0.01, rms.mean() * 0.3)
    
    # Find speech regions where RMS > threshold
    # Split text into sentences
    # Map sentences to speech regions proportionally
    # Fallback: word-count-based duration estimate
```

#### Step 5: Cross-Chunk Deduplication

Overlapping chunks produce duplicate segments. The deduplication strategy:

1. **Exact match**: Drop segments with identical `(start_time, end_time)` and text
2. **Temporal proximity**: Same text within 5 seconds → duplicate
3. **Fuzzy match**: First 50 characters match within 2 seconds → duplicate
4. **Duration cap**: Segments beyond video duration are discarded

```python
# Deduplication pseudocode
for segment in all_segments:
    is_dup = False
    for existing in unique_segments:
        if (same_text and within_5s) or (same_prefix_50 and within_2s):
            is_dup = True
            break
    if not is_dup:
        unique_segments.append(segment)
```

### 10.3 Local Whisper (Alternative)

For offline or cost-sensitive deployments:

- Model: configurable via `WHISPER_MODEL_SIZE` (default `tiny`, fallback `base`)
- Options: `word_timestamps=False`, `fp16=False` (CPU-compatible)
- Runs the full model in-container

---

## 11. Audio Analysis & Anomaly Detection

### 11.1 Architecture

The audio analysis module (`audio_anomaly_detection.py`) is a comprehensive statistical signal processing system that runs 6 independent detectors on the extracted WAV file:

```
Raw WAV (44.1kHz stereo)
        │
        ▼
┌─────────────────────────────────────┐
│ Feature Extraction (librosa)        │
│ - RMS energy (hop_length=512)       │
│ - Spectral centroid                 │
│ - Spectral rolloff                  │
│ - Zero-crossing rate (ZCR)          │
└───────────┬─────────────────────────┘
            │
   ┌────────┼────────┬────────┬────────┬────────┐
   ▼        ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Loud  │ │Sudden│ │Silence│ │Distor│ │Freq  │ │Gun-  │
│Sound │ │Change│ │      │ │tion  │ │Anom. │ │shot  │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

### 11.2 Feature Extraction

All features are computed from the full audio signal using librosa:

```python
rms = librosa.feature.rms(y=y, hop_length=512)[0]
spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=512)[0]
zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=512)[0]
```

With `hop_length=512` at 44.1 kHz, each frame represents ~11.6 ms of audio.

### 11.3 Loud Sound Detection

**Strategy**: Identify frames where RMS energy significantly exceeds the statistical norm, with contextual validation.

**Threshold calculation** (adaptive):
```python
threshold = max(
    rms_mean + 3.5 * rms_std,     # Statistical: 3.5 standard deviations
    percentile_95,                  # Percentile-based
    rms_mean * 2.0                  # Proportional floor
)
```

**Contextual validation**:
- Compute rolling average over surrounding frames
- Event must have intensity ≥ 1.8× the local rolling average
- Event duration must be 0.1–2.0 seconds (filters clicks and sustained noise)

**Confidence scoring**:
```python
intensity_ratio = peak_rms / rms_mean
confidence = min(0.95, 0.65 + (intensity_ratio - 0.70) * 1.2)
# Only emitted if confidence >= 0.60
```

### 11.4 Sudden Change Detection

**Strategy**: Detect abrupt transitions in audio energy (e.g., door slams, sudden shouting).

**Threshold**:
```python
threshold = max(
    4 * rms_std,        # 4 standard deviations of change magnitude
    percentile_98,       # 98th percentile
    2 * rms_mean         # 2× mean energy
)
```

**Detection**: Frame-to-frame RMS difference; change ratio > 2.0 triggers an event.

**Confidence**: `min(0.9, 0.6 + (change_ratio - 2) / 3)`

### 11.5 Silence Detection

**Strategy**: Find extended periods of abnormally low energy, which may indicate equipment issues or deliberate muting.

**Thresholds**:
```python
silence_threshold = max(0.005, rms_mean * 0.08)  # Very strict
min_duration = 2.0  # seconds
```

**Validation**: Silent region must be < 0.3× the local average energy. Quiet ratio > 5.0 required.

### 11.6 Distortion Detection

**Strategy**: Identify audio clipping (digital distortion) by finding samples near maximum amplitude.

**Algorithm**:
1. Find samples exceeding 0.95× max amplitude
2. Cluster adjacent samples within 50 ms
3. Filter: cluster size ≥ 50 samples, duration ≥ 100 ms
4. Clip fraction (clipped/total in window) must exceed 0.3

### 11.7 Frequency Anomaly Detection

**Strategy**: Use spectral features to detect unusual audio characteristics (screams, sirens, electronic interference).

**Thresholds** (per-feature, ±2.5 standard deviations):
```python
centroid_low  = centroid_mean - 2.5 * centroid_std
centroid_high = centroid_mean + 2.5 * centroid_std
rolloff_threshold = rolloff_mean + 2.5 * rolloff_std
zcr_threshold = zcr_mean + 2.5 * zcr_std
```

**Multi-indicator scoring**: Multiple simultaneous anomalies increase confidence. Score ≥ 3 or deviation ≥ 4.0 may also tag the event as `LoudSound`.

### 11.8 Output Filtering

All detected anomalies pass through a final confidence gate:
```python
anomalies = [a for a in all_anomalies if a['confidence'] >= 0.6]
```

---

## 12. Gunshot Detection System

### 12.1 Dual-Modal Approach

Gunshot detection combines two independent signals for higher reliability:

```
┌────────────────────────┐     ┌──────────────────────────────┐
│  Transcript Analysis   │     │  Spectral Audio Analysis     │
│                        │     │                              │
│  Regex patterns for    │────▶│  Analyze frequency spectrum  │
│  gunshot mentions      │     │  5-10s before each mention   │
│  in speech             │     │                              │
└────────────────────────┘     └──────────────┬───────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ Fused Event with  │
                                    │ Combined Confidence│
                                    └──────────────────┘
```

### 12.2 Transcript Pattern Matching

Regex patterns (case-insensitive):
```python
GUNSHOT_PATTERNS = [
    r'shots?\s+fired',
    r'gunshot',
    r'gun\s+shot',
    r'fired\s+shots?',
    r'discharged\s+weapon',
    r'weapon\s+discharged',
    r'pop\s+pop',
    r'bang',
    r'pow',
    r'shooting',
    r'open\s+fire'
]
```

### 12.3 Spectral Confirmation

For each transcript mention:
1. Extract audio window: 5–10 seconds before the mention timestamp
2. Compute spectral features: centroid, rolloff, zero-crossing rate
3. Compare against `mean + 2*std` thresholds
4. Score = count of triggered indicators (≥ 1 required)

**Event window**: 0.5 seconds before to 1.5 seconds after the spectral anomaly peak.

### 12.4 Confidence Fusion

```python
confidence = min(0.95, 0.65 + (score - 1) * 0.1 + proximity_factor * 0.15)
```

Where `proximity_factor` measures how close the spectral anomaly is to the transcript mention. If no spectral anomaly is found, the event is still created at the mention timestamp with a baseline confidence of 0.65.

---

## 13. Profanity Detection

### 13.1 Pattern-Based Approach

The profanity detector uses compiled regex patterns that handle common misspellings and letter repetition:

```python
PROFANITY_PATTERNS = [
    r'\bf+u+c+k+\w*\b',       # fuck and variants
    r'\bs+h+i+t+\w*\b',       # shit and variants
    r'\bb+i+t+c+h+\w*\b',     # bitch and variants
    r'\ba+s+s+h+o+l+e+\w*\b', # asshole and variants
    r'\bd+a+m+n+\w*\b',       # damn and variants
    # ... additional patterns
]
```

### 13.2 Temporal Grouping

Matches are grouped into 10-second windows to avoid generating redundant events for rapid profanity:

```python
window_size = 10  # seconds
# Group profanity instances by floor(timestamp / 10)
# Each group becomes one event
```

### 13.3 Density-Based Confidence

| Instances in Window | Confidence |
|--------------------|-----------|
| 1 | 0.60 |
| 2–3 | 0.75 |
| 4+ | up to 0.95 |

---

## 14. GPT-Powered Transcript Event Detection

### 14.1 Architecture

The GPT event detector sends the full transcript to GPT-4o-mini with a law-enforcement-specific system prompt to identify high-level semantic events.

### 14.2 System Prompt

The model is instructed to act as a law enforcement transcript analyst with the following event taxonomy:

| Event Type | Description |
|-----------|------------|
| Verbal Confrontation | Heated exchanges, arguments, raised voices |
| Threat | Direct or implied threats of violence |
| Weapon Mention | References to weapons, firearms |
| Use of Force | Physical force described or occurring |
| Miranda Rights | Rights being read |
| Medical Emergency | Medical distress or need for EMS |
| Emotional Distress | Crying, panic, extreme emotional states |
| Pursuit | Chases, foot pursuits, vehicle pursuits |
| Compliance Issue | Refusal to comply, resistance |
| De-escalation | Attempts to calm a situation |

### 14.3 API Configuration

```python
model = "gpt-4o-mini"
temperature = 0.1      # Near-deterministic
max_tokens = 2000
response_format = JSON  # Structured output
```

### 14.4 Output Format

```json
[
  {
    "start_time": 780.0,
    "end_time": 795.0,
    "event_type": "Use of Force",
    "confidence": 0.85,
    "description": "Officer reports shots fired, suspect engaged"
  }
]
```

---

## 15. OCR & Metadata Extraction

### 15.1 Frame Selection Strategy

Three frames are extracted at strategic timestamps:

| Frame | Timestamp | Rationale |
|-------|-----------|-----------|
| 1 | 30s | Early in video, overlay usually visible |
| 2 | 60s | Redundancy in case of motion blur |
| 3 | 120s | Further into video for additional data |

Frames are extracted using OpenCV and encoded as JPEG at 85% quality, then converted to base64 for API transmission.

### 15.2 GPT-4o Vision Analysis

Each frame is sent to GPT-4o with a specialized prompt requesting extraction of:

- **timestamp**: Camera-embedded date/time (e.g., "2019-05-06 17:47:39")
- **device_id**: Hardware serial number (e.g., "X81241157")
- **device_model**: Camera model (e.g., "AXON BODY 2")
- **badge_number**: Officer badge number (if visible)
- **officer_id**: Officer identifier (if visible)

### 15.3 Multi-Frame Merging

Results from all three frames are merged using first-non-null strategy:

```python
merged = {}
for field in ['timestamp', 'device_id', 'device_model', 'badge_number']:
    for frame_result in results:
        if frame_result.get(field):
            merged[field] = frame_result[field]
            break
```

### 15.4 File Output

OCR metadata is saved to `backend/ocr_data/{file_id}_{timestamp}.txt` for audit trail purposes.

---

## 16. Agentic Chat System

### 16.1 Architecture

The chat system implements an agentic loop where GPT-4o-mini can dynamically invoke Gemini to analyze specific video segments based on user questions:

```
User Question
      │
      ▼
┌──────────────┐
│  GPT-4o-mini │ ◄──── Context: transcript + moments + segments
│  (Orchestrator)│
└──────┬───────┘
       │
       ├─── Tool Call: ask_gemini_on_segment(question, start, end)
       │         │
       │         ▼
       │    ┌──────────────┐
       │    │ Gemini 2.5   │ ◄── Video segment extracted via ffmpeg
       │    │ Flash         │
       │    └──────┬───────┘
       │           │
       │           ▼
       │    Gemini response fed back as tool result
       │
       ├─── Tool Call: finish(answer)
       │
       ▼
  Final Answer to User
```

### 16.2 Tool Definitions

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "ask_gemini_on_segment",
            "description": "Ask Gemini to analyze a specific video segment",
            "parameters": {
                "question": "string",
                "start_timestamp": "string (MM:SS or HH:MM:SS)",
                "end_timestamp": "string"
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Return the final answer",
            "parameters": {
                "answer": "string"
            }
        }
    }
]
```

### 16.3 Safety Guardrails

| Guard | Value | Purpose |
|-------|-------|---------|
| Max turns | 5 | Prevent infinite loops |
| Max Gemini calls | 3 | Cost control |
| Max segment length | 300s (5 min) | Gemini upload limits |
| Query deduplication | MD5 of `question|start|end` | Avoid redundant API calls |

### 16.4 Context Construction

The chat system builds rich context from all available data:

```python
context = f"""
Transcript: {transcript}
Moments of Interest: {moments_json}
Video Segments: {segments_json}
OCR Metadata: {ocr_json}
"""
```

### 16.5 Non-Agentic Fallback

When Gemini is disabled, the chat falls back to:
- **With timestamp in question**: Extract frame → GPT-4o vision analysis
- **Without timestamp**: GPT-4o-mini text-only analysis with transcript context

---

## 17. Frontend Architecture

### 17.1 Component Hierarchy

```
main.tsx
├── ThemeProvider (light/dark theme via localStorage + system preference)
│   └── VideoProvider (centralized video playback state)
│       └── App
│           ├── CaseHeader (upload, file info, theme toggle)
│           ├── ProcessingPipeline (status visualization)
│           ├── [Desktop: ResizablePanels]
│           │   ├── Left Panel
│           │   │   ├── EventPanel (event list + filters)
│           │   │   └── SegmentPanel (Gemini segments)
│           │   ├── Center Panel
│           │   │   ├── VideoPlayer (video + timeline + controls)
│           │   │   └── TranscriptPanel (searchable transcript)
│           │   └── Right Panel
│           │       └── AIAssistant (agentic chat)
│           └── [Mobile: Tab Navigation]
│               └── (same components, one at a time)
```

### 17.2 State Architecture

**Global State (Context API)**:

- `ThemeContext`: `theme` (light/dark), `toggle()`, persisted to `localStorage`
- `VideoContext`: `videoElement`, `currentTime`, `duration`, `isPlaying`, `seekTo()`, `play()`, `pause()`, `setPlaybackRate()`, `skipForward()`, `skipBackward()`

**App-Level State** (React useState):

- `fileId`, `videoUrl`, `events[]`, `caseInfo`, `processingStatus`, `selectedEventId`
- `mobileTab`, `leftTab` (UI navigation)
- `pollRef` (polling interval reference)

**Component-Local State**:

- `EventPanel`: `activeFilter`, `search`, `expandedId`
- `TranscriptPanel`: `segments[]`, `status`, `autoFollow`, `search`
- `AIAssistant`: `mode`, `messages[]`, `input`, `loading`, `activeAction`
- `VideoPlayer`: `speed`, `showSpeedMenu`, `hoverTime`, `hoverX`

### 17.3 Video Playback

The video is played from a local blob URL (`URL.createObjectURL(file)`) — the file never streams from the backend. This eliminates server-side video streaming complexity and provides instant seek/playback.

**Playback Controls**:
- Play/Pause (K or Space)
- Skip ±5 seconds (J/L keys)
- Previous/Next event (Q/E keys)
- Speed: 0.5x, 1x, 1.25x, 1.5x, 2x

### 17.4 Responsive Layout

- **Desktop (≥ 1024px)**: Three-panel resizable layout via `react-resizable-panels`
- **Mobile (< 1024px)**: Bottom tab bar with Video, Events, Transcript, AI tabs
- Detected via `window.matchMedia` hook

### 17.5 Design System

Built on Tailwind CSS with a comprehensive token system:

**CSS Variables** (light/dark):
```css
:root {
    --bg, --surface-1/2/3, --border,
    --text, --muted, --muted-2,
    --primary, --primary-2,
    --success, --warning, --danger
}
```

**Component Classes**: `.panel`, `.panel-elevated`, `.panel-nested`, `.event-badge`, `.btn-primary`, `.btn-ghost`, `.input-base`, `.timeline-playhead`

**Typography**: Inter (Google Fonts) for sans-serif, SF Mono/Menlo for monospace.

**Animations**: `pulse-slow`, `slide-up`, `fade-in` for processing indicators and event transitions.

---

## 18. Real-Time Synchronization & Reactive UI

### 18.1 Polling Architecture

The frontend uses two independent polling loops:

**App-level polling** (3-second interval):
```
Every 3s:
  ├── GET /api/moments?file_id=...    → Update events
  └── GET /api/files/{id}/metadata    → Update processing status
  
Stop when: status === 'completed' || status === 'failed'
```

**Transcript polling** (3-second interval, in TranscriptPanel):
```
Every 3s:
  └── GET /api/transcribe?file_id=...  → Update segments
  
Stop when: segments.length > 0 || has_transcription === true
```

### 18.2 Video–Event Synchronization

Multiple components react to `currentTime` from `VideoContext`:

| Component | Behavior |
|-----------|----------|
| **VideoPlayer** | Playhead position, current-event overlay badge |
| **EventPanel** | Highlights active event, auto-scrolls to it |
| **TranscriptPanel** | Highlights active segment, auto-scrolls when `autoFollow` enabled |
| **SegmentPanel** | Highlights active Gemini segment |

**Active event computation**:
```typescript
const currentEvent = events.find(
    ev => currentTime >= ev.timestamp && currentTime <= ev.endTime
);
```

### 18.3 Event → Video Navigation

Clicking an event in EventPanel calls `seekTo(event.timestamp)` via VideoContext, which:
1. Sets `video.currentTime = timestamp`
2. Triggers `timeupdate` events
3. All synchronized components update reactively

### 18.4 Timeline Visualization

The video player timeline renders events as colored segments:

```typescript
events.map(event => ({
    left: `${(event.timestamp / duration) * 100}%`,
    width: `${((event.endTime - event.timestamp) / duration) * 100}%`,
    color: EVENT_TIMELINE_COLORS[event.type] || '#6366f1'  // indigo default
}))
```

---

## 19. Event Classification & Taxonomy

### 19.1 Complete Event Type Catalog

| Event Type | Source | Color | Description |
|-----------|--------|-------|-------------|
| **Gunshot** | Audio + Transcript | Red (#ef4444) | Confirmed gunfire via dual-modal detection |
| **LoudSound** | Audio Analysis | Orange (#f97316) | Statistically significant energy spike |
| **SuddenChange** | Audio Analysis | Amber (#f59e0b) | Abrupt transition in audio energy |
| **Silence** | Audio Analysis | Gray (#6b7280) | Extended abnormal silence period |
| **Distortion** | Audio Analysis | Yellow (#eab308) | Audio clipping / digital distortion |
| **FrequencyAnomaly** | Audio Analysis | Cyan (#06b6d4) | Unusual spectral characteristics |
| **Profanity** | Transcript Regex | Purple (#a855f7) | Explicit language detected |
| **Verbal Confrontation** | GPT Analysis | Rose (#f43f5e) | Heated verbal exchange |
| **Threat** | GPT Analysis | Red (#dc2626) | Threat of violence |
| **Weapon Mention** | GPT Analysis | Red (#b91c1c) | Weapon referenced in speech |
| **Use of Force** | GPT + Gemini | Red (#991b1b) | Physical force applied |
| **Miranda Rights** | GPT Analysis | Blue (#3b82f6) | Rights being read |
| **Medical Emergency** | GPT Analysis | Red (#ef4444) | Medical distress |
| **Emotional Distress** | GPT Analysis | Pink (#ec4899) | Extreme emotional state |
| **Pursuit** | GPT Analysis | Orange (#ea580c) | Chase in progress |
| **Compliance Issue** | GPT Analysis | Amber (#d97706) | Refusal to comply |
| **De-escalation** | GPT Analysis | Green (#22c55e) | Calming attempt |
| **UseOfForce** | Gemini Visual | Red (#dc2626) | Force observed in video |
| **PotentialExcessiveForce** | Gemini Visual | Dark Red (#991b1b) | Flagged as potentially excessive |
| **CameraObfuscation** | Gemini Visual | Gray (#4b5563) | Camera blocked or obstructed |

### 19.2 Multi-Label Events

A single moment can carry multiple event types. For example, a gunshot event might be labeled:
```json
["Gunshot", "LoudSound", "Weapon Mention"]
```

This occurs when multiple detection modules identify the same temporal region independently.

---

## 20. Security, Configuration & Environment

### 20.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/multimedia_events` | PostgreSQL connection |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Redis broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Redis results |
| `OPENAI_API_KEY` | — | OpenAI API authentication |
| `OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | Whisper model |
| `OPENAI_CHUNK_DURATION` | `60` | Transcription chunk size (seconds) |
| `OPENAI_CHUNK_OVERLAP` | `5` | Chunk overlap (seconds) |
| `OPENAI_TRANSCRIPTION_TEMPERATURE` | `0` | Whisper temperature |
| `OPENAI_TRANSCRIPTION_MAX_RETRIES` | `3` | Retry count |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Chat model |
| `TRANSCRIPTION_PROVIDER` | auto-detect | `openai`, `local`, `mock` |
| `USE_MOCK_TRANSCRIPTION` | `false` | Enable mock mode |
| `ENABLE_LOCAL_WHISPER` | `false` | Enable local Whisper |
| `WHISPER_MODEL_SIZE` | `tiny` | Local Whisper model |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `ENABLE_GEMINI_ANALYSIS` | `false` | Enable visual analysis |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `VIDEO_CHUNK_SECONDS` | `300` | Visual analysis chunk size |
| `AWS_ACCESS_KEY_ID` | — | Optional S3 integration |
| `AWS_SECRET_ACCESS_KEY` | — | Optional S3 integration |
| `AWS_REGION` | — | Optional S3 region |

### 20.2 API Key Management

- API keys are passed via environment variables, never hardcoded
- Docker Compose propagates `.env` values to backend and celery containers
- CORS is configured to allow all origins (development mode)

### 20.3 File Storage

- Uploaded files: `./uploads/{uuid}{extension}`
- Transcripts: `backend/transcripts/{file_id}_{timestamp}.txt`
- OCR data: `backend/ocr_data/{file_id}_{timestamp}.txt`
- Moments reports: `backend/moments/{file_id}_{timestamp}.txt`

---

## 21. Appendix: Full API Reference

### POST `/api/upload`

Upload a video or audio file for processing.

- **Content-Type**: `multipart/form-data`
- **Body**: `file` (video/* or audio/*)
- **Response**: `{ file_id, message, status }`
- **Side Effects**: Creates `FileMetadata` record, dispatches `transcribe_and_detect_task`

### GET `/api/files/{file_id}/metadata`

Get file processing status and metadata.

- **Response**: `{ file_id, original_filename, ocr_metadata, duration, timestamp_start, status }`

### GET `/api/moments?file_id={file_id}`

List detected moments of interest.

- **Response**: `{ moments: [...], count }`

### GET `/api/moments/download?file_id={file_id}`

Download moments report as plain text.

- **Response**: `text/plain` file

### POST `/api/transcribe`

Start transcription for a file (standalone, outside main pipeline).

- **Body**: `{ file_id }`

### GET `/api/transcribe?file_id={file_id}`

Get transcript and segments.

- **Response**: `{ segments: [...], has_transcription, status }`

### GET `/api/transcribe/download?file_id={file_id}`

Download transcript as plain text.

### GET `/api/ocr/download?file_id={file_id}`

Download OCR metadata as plain text.

### POST `/api/chat`

Chat with AI about the video.

- **Body**: `{ file_id, messages: [{role, content}] }`
- **Response**: `{ message, usage, visual_analysis_used, analyzed_timestamps, gemini_segments_analyzed }`
- **Behavior**: Agentic loop with Gemini if enabled; GPT-4o vision fallback otherwise

### GET `/api/segments?file_id={file_id}`

Get Gemini visual analysis segments.

- **Response**: `{ segments: [...], count }`

### GET `/health`

Health check endpoint.

- **Response**: `{ status: "healthy" }`

---

*This document provides a comprehensive technical reference for the ALERT system. For deployment instructions, see the project README. For the presentation version, see `docs/ALERT-Technical-Presentation.html`.*
