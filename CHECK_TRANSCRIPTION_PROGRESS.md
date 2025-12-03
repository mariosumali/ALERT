# How to Check Transcription Progress

## Method 1: API Endpoint (Recommended)

### Check status via API:
```bash
curl "http://localhost:8000/api/transcribe?file_id=YOUR_FILE_ID"
```

### Response when processing:
```json
{
  "file_id": "abc123...",
  "transcript": null,
  "segments": [],
  "has_transcription": false
}
```

### Response when complete:
```json
{
  "file_id": "abc123...",
  "transcript": "Full transcript text here...",
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "First segment..."},
    {"start": 5.2, "end": 10.5, "text": "Second segment..."}
  ],
  "has_transcription": true
}
```

## Method 2: Watch Celery Worker Logs (Real-Time)

### Watch all transcription activity:
```bash
docker-compose logs -f celery_worker | grep -i "transcrib\|whisper\|complete\|error"
```

### Watch only transcription events:
```bash
docker-compose logs -f celery_worker | grep -E "Transcribing|Loading Whisper|Transcription complete|segments created|error"
```

### What you'll see:
```
[2025-11-05 00:43:28] Transcribing file abc123... with timestamps...
[2025-11-05 00:43:28] Transcribing ./uploads/abc123.mp4 using local OpenAI Whisper...
[2025-11-05 00:43:28] Loading Whisper 'tiny' model...
[2025-11-05 00:43:30] Starting transcription...
[2025-11-05 00:45:15] Transcription complete. 15 segments created.
```

## Method 3: Check Database Directly

### Connect to database and check:
```bash
docker-compose exec db psql -U postgres -d multimedia_events -c "SELECT file_id, transcript IS NOT NULL as has_transcript, array_length(transcript_segments, 1) as segment_count FROM file_metadata WHERE file_id = 'YOUR_FILE_ID';"
```

### Get full transcription:
```bash
docker-compose exec db psql -U postgres -d multimedia_events -c "SELECT transcript, transcript_segments FROM file_metadata WHERE file_id = 'YOUR_FILE_ID';"
```

## Method 4: Browser/API Docs

1. **Open API Docs**: http://localhost:8000/docs
2. **Find GET `/api/transcribe` endpoint**
3. **Click "Try it out"**
4. **Enter your `file_id`**
5. **Click "Execute"**
6. **See the response** - `has_transcription: false` means still processing

## Method 5: Frontend UI (Automatic)

The frontend automatically polls every 3 seconds:
- Visit: http://localhost:5001
- Upload a file and click "Transcribe"
- The TranscriptionView component will automatically show:
  - "Processing" status while transcribing
  - Progress updates
  - Segments when complete

## Quick Status Check Script

Create a simple script to check status:

```bash
#!/bin/bash
# check_transcription.sh
FILE_ID=$1
if [ -z "$FILE_ID" ]; then
  echo "Usage: ./check_transcription.sh <file_id>"
  exit 1
fi

curl -s "http://localhost:8000/api/transcribe?file_id=$FILE_ID" | python3 -m json.tool
```

## Understanding the Status

- **`has_transcription: false`** = Still processing or not started
- **`has_transcription: true`** = Complete (even if transcript is empty)
- **`segments: []`** = No segments yet (still processing)
- **`segments: [...]`** = Transcription complete with segments

## Troubleshooting

If transcription seems stuck:
1. Check Celery logs for errors: `docker-compose logs --tail=50 celery_worker`
2. Check if Celery worker is running: `docker-compose ps celery_worker`
3. Restart Celery worker if needed: `docker-compose restart celery_worker`

