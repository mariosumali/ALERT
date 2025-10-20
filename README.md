# Multimedia Event Parsing for Police Records Analysis

## Project Overview

This project develops an automated pipeline for parsing long audio and video files to identify key moments of interest in law enforcement recordings. The system is designed to support the Police Records Access Project by reducing manual review burden and highlighting critical segments in multimedia evidence.

**Team Members:** Mario Sumali, Shane Mion  
**Mentor:** Vardhan Agrawal  
**Affiliation:** Stanford CS224V – Multimedia Event Parsing

## Background & Motivation

The Police Records Access Project hosts a large public database containing millions of law enforcement records, including text, images, audio, and video. While textual data is searchable, a significant amount of meaningful context remains locked in long multimedia files. Currently, reviewers must manually watch or listen to entire recordings to identify critical moments such as verbal escalation, silence, or visual obstructions.

Our goal is to automate the first pass of this review process by using machine learning to highlight potential "moments of interest," reducing the manual review burden for journalists and researchers.

## Objectives

- Develop a lightweight and interpretable pipeline for automatic detection and classification of high-interest segments in long audio or video recordings
- Create a structured metadata output schema for integration into the Police Records Access Project database
- Provide a working prototype capable of parsing long recordings into segments labeled with "moment of interest" probabilities

## Expected Deliverables

1. **Working Prototype**: A system capable of parsing long recordings into segments labeled with "moment of interest" probabilities
2. **Metadata Schema**: A structured output format for integration into the Police Records Access Project database
3. **Research Report**: A summary of findings, limitations, and next steps for future work

## Event Detection Framework

### Audio-Based Indicators
- Sudden volume spikes or drops
- Gunshots
- Sirens
- Long silence intervals
- Microphone occlusion or muffling
- Overlapping voices
- Swearing or slurs
- Command-style speech
- Emotional tone shifts
- Changes in speaker count
- Abrupt truncation or clipping

### Video-Based Indicators
- Camera occlusion
- Fast motion or shaking
- Lighting changes
- Body orientation shifts
- Timestamp discontinuities
- GPS metadata jumps
- Frame corruption or dropped frames

### Derived Indicators
- Mentions of force usage
- Named entities (officer names, locations, times)
- Temporal language ("after arrest," "during stop")
- Emotionally charged language
- Linguistic uncertainty

### Composite Indicators
- Co-occurrence of multiple anomalies
- Long low-activity stretches
- Sudden context anomalies across modalities

## Key Detection Categories

- **Volume spikes/drops**: Audio amplitude analysis
- **Silence duration**: Temporal gap detection
- **Presence of speech**: Voice activity detection
- **Profanity or strong emotion**: Sentiment and language analysis
- **Motion or occlusion events**: Visual change detection

## Project Structure

```
224V-Project/
├── README.md
├── requirements.txt
├── src/
│   ├── audio_processing/
│   ├── video_processing/
│   ├── feature_extraction/
│   ├── event_detection/
│   └── output_schema/
├── data/
│   ├── raw/
│   ├── processed/
│   └── annotations/
├── models/
├── tests/
├── docs/
└── examples/
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/[username]/224V-Project.git
cd 224V-Project
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (if needed):
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

## Usage

### Basic Audio Processing
```python
from src.audio_processing.analyzer import AudioAnalyzer

analyzer = AudioAnalyzer()
results = analyzer.process_file("path/to/audio.wav")
```

### Basic Video Processing
```python
from src.video_processing.analyzer import VideoAnalyzer

analyzer = VideoAnalyzer()
results = analyzer.process_file("path/to/video.mp4")
```

### Event Detection Pipeline
```python
from src.event_detection.pipeline import EventDetectionPipeline

pipeline = EventDetectionPipeline()
events = pipeline.detect_events("path/to/multimedia_file")
```

## Output Schema

The system outputs structured metadata in JSON format:

```json
{
  "file_id": "unique_identifier",
  "timestamp": "2024-01-01T00:00:00Z",
  "duration": 3600.5,
  "segments": [
    {
      "start_time": 120.5,
      "end_time": 135.2,
      "event_type": "volume_spike",
      "confidence": 0.87,
      "metadata": {
        "amplitude_change": 15.3,
        "context": "sudden_loud_noise"
      }
    }
  ],
  "summary": {
    "total_events": 15,
    "high_confidence_events": 8,
    "event_types": ["volume_spike", "silence", "speech"]
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Research Ethics

This project is designed to support transparency and accountability in law enforcement through automated analysis of public records. All processing is performed on publicly available data, and the system is designed to highlight potentially significant events for human review rather than making definitive judgments.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Stanford CS224V course staff
- Police Records Access Project
- Open source multimedia processing libraries

## Contact

For questions or collaboration opportunities, please contact:
- Mario Sumali: [email]
- Shane Mion: [email]

---

*This project is part of Stanford CS224V - Multimedia Event Parsing course work.*
