# Multimedia Event Parsing

**Stanford CS224V – Multimedia Event Parsing**  
Mario Sumali, Shane Mion | Mentor: Vardhan Agrawal

Automated pipeline for parsing long audio and video files to identify key moments of interest in law enforcement recordings for the Police Records Access Project.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch GUI video browser
python download_videos.py

# Or use the Python API
python -c "from src.data_ingestion.sjpd_loader import SJPDLoader; \
           loader = SJPDLoader(); \
           print(loader.get_dataset_summary())"
```

## Dataset

SJPD spreadsheets in `src/spreadsheets/`:
- **videos w_ links.csv**: Video metadata with Google Drive links
- **transcripts.csv**: Transcript text for videos

## Key Features

### Data Ingestion
- **`sjpd_loader.py`**: Load SJPD spreadsheets, link videos with transcripts
- **`transcript_processor.py`**: Detect events in transcripts (profanity, force mentions, commands, etc.)

### Event Detection
- **Audio**: Volume spikes, silence, gunshots, sirens, speech detection
- **Video**: Occlusion, motion, lighting changes, body orientation shifts
- **Text**: Force mentions, commands, profanity, temporal language
- **Composite**: Multi-modal anomalies, context changes

## Project Structure

```
src/
├── data_ingestion/      # Spreadsheet loaders, transcript processing
├── audio_processing/    # Audio feature extraction
├── video_processing/    # Video feature extraction
└── event_detection/     # Unified event detection pipeline

data/
├── raw/                 # Downloaded videos
├── processed/           # Processed analyses
└── annotations/         # Spreadsheets
```

## Usage

### GUI Video Browser
```bash
python download_videos.py
```
Browse videos, view metadata, access transcripts, and download videos interactively.

### Python API
```python
from src.data_ingestion import SJPDLoader, TranscriptProcessor

# Load dataset
loader = SJPDLoader()
summary = loader.get_dataset_summary()
print(f"Total: {summary['total_duration_hours']:.1f} hours")

# Process transcripts
processor = TranscriptProcessor()
results = processor.process_transcript(video_id, transcript)
print(results['summary'])
```

## Deliverables

1. Working prototype for parsing and labeling recordings
2. Structured metadata output schema
3. Research report with findings and next steps

## Event Indicators

### Audio-Based
Volume spikes/drops, gunshots, sirens, silence, microphone occlusion, overlapping voices, profanity, commands, emotional shifts, speaker count changes, clipping

### Video-Based  
Camera occlusion, motion/shaking, lighting changes, body orientation, timestamp discontinuities, GPS jumps, frame corruption

### Derived
Force mentions, named entities (officers/locations/times), temporal language, emotional language, uncertainty markers

### Composite
Co-occurring anomalies, low-activity stretches, cross-modal context changes

## License

MIT License
