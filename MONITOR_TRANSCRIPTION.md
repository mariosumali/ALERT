# How to Monitor Transcription in Real-Time

## Method 1: Watch Celery Worker Logs (Recommended)

Open a terminal and run:

```bash
docker-compose logs -f celery_worker
```

This will show you:
- When transcription starts
- Which mode it's using (OpenAI API vs Mock)
- Progress updates
- Any errors
- Completion status

## Method 2: Filter for Transcription Events

Watch only transcription-related logs:

```bash
docker-compose logs -f celery_worker | grep -i "transcrib\|openai\|mock\|error"
```

## Method 3: Check Recent Logs

See the last 50 lines of transcription activity:

```bash
docker-compose logs --tail=50 celery_worker | grep -i "transcrib"
```

## What to Look For

### ✅ Using OpenAI API (Real Transcription):
```
Transcribing file ... using OpenAI Whisper API...
API Key present: True
Uploading file to OpenAI API...
OpenAI API response received
Transcription complete. X segments created.
```

### ⚠️ Using Mock Transcription:
```
Transcribing file ... with timestamps (mock=True)...
Transcription complete for file ... X segments created.
```

### ❌ Error (Falling back to mock):
```
OpenAI API transcription error: [error message]
Falling back to mock transcription due to error: [error]
```

## Quick Status Check

```bash
# Check if API key is set
docker-compose exec celery_worker printenv | grep OPENAI

# See last transcription attempt
docker-compose logs --tail=20 celery_worker | tail -10
```

