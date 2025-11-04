"""High level video processing pipeline used by the platform."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

from src.data_ingestion.transcript_processor import TranscriptProcessor
from src.video_processing.occlusion_detector import OcclusionDetector

from .uploader import UploadedVideo, VideoUploader

try:
    import speech_recognition as sr
except Exception:  # pragma: no cover - optional dependency
    sr = None

try:
    from moviepy.editor import VideoFileClip
except Exception:  # pragma: no cover - optional dependency
    VideoFileClip = None

LOGGER = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """Single transcript segment with timing information."""

    start: float
    end: float
    text: str


@dataclass
class NotableMoment:
    """Structured representation of notable moments detected in a video."""

    label: str
    start_time: float
    end_time: float
    confidence: float
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class VideoAnalysisResult:
    """Full pipeline output including transcript and detected events."""

    uploaded_video: UploadedVideo
    transcript: str
    transcript_segments: List[TranscriptSegment]
    transcript_events: Dict[str, object]
    video_events: Dict[str, List[NotableMoment]]

    def to_dict(self) -> Dict[str, object]:
        """Serialise the result to a JSON-friendly dictionary."""

        return {
            "uploaded_video": asdict(self.uploaded_video),
            "transcript": self.transcript,
            "transcript_segments": [asdict(seg) for seg in self.transcript_segments],
            "transcript_events": self.transcript_events,
            "video_events": {
                key: [asdict(moment) for moment in moments]
                for key, moments in self.video_events.items()
            },
        }


class TranscriptGenerator:
    """Generate transcripts from a video using SpeechRecognition."""

    def __init__(self, *, energy_threshold: int = 300, pause_threshold: float = 0.8) -> None:
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.recognizer: Optional[sr.Recognizer] = None
        if sr is not None:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = energy_threshold
            self.recognizer.pause_threshold = pause_threshold

    def generate(self, video_path: Path | str) -> tuple[str, List[TranscriptSegment]]:
        """Transcribe the given video file.

        Returns an empty transcript when SpeechRecognition or moviepy is unavailable.
        The method is written defensively to keep the rest of the pipeline working in
        environments where the heavy optional dependencies cannot be installed.
        """

        if self.recognizer is None or VideoFileClip is None:
            LOGGER.warning(
                "Speech transcription skipped - missing dependencies (speech_recognition/moviepy)."
            )
            return "", []

        video = VideoFileClip(str(video_path))
        audio_path = Path("data/raw/tmp").resolve()
        audio_path.mkdir(parents=True, exist_ok=True)
        temp_audio = audio_path / "temp_audio.wav"

        video.audio.write_audiofile(str(temp_audio), logger=None)

        segments: List[TranscriptSegment] = []
        transcript_text_parts: List[str] = []

        assert sr is not None  # for type checkers
        with sr.AudioFile(str(temp_audio)) as source:
            audio_data = self.recognizer.record(source)

            try:
                text = self.recognizer.recognize_google(audio_data)
            except Exception as exc:  # pragma: no cover - depends on API/network
                LOGGER.error("Speech recognition failed: %s", exc)
                temp_audio.unlink(missing_ok=True)
                return "", []

            duration = video.duration or 0.0
            segments.append(TranscriptSegment(start=0.0, end=duration, text=text))
            transcript_text_parts.append(text)

        temp_audio.unlink(missing_ok=True)
        return " ".join(transcript_text_parts), segments


class VideoAnalysisPipeline:
    """Full workflow orchestrating uploads, transcripts, and event detection."""

    def __init__(
        self,
        *,
        uploader: Optional[VideoUploader] = None,
        transcript_generator: Optional[TranscriptGenerator] = None,
        transcript_processor: Optional[TranscriptProcessor] = None,
        occlusion_detector: Optional[OcclusionDetector] = None,
    ) -> None:
        self.uploader = uploader or VideoUploader()
        self.transcript_generator = transcript_generator or TranscriptGenerator()
        self.transcript_processor = transcript_processor or TranscriptProcessor()
        self.occlusion_detector = occlusion_detector or OcclusionDetector()

    def process(self, video_path: Path | str, *, video_id: Optional[str] = None) -> VideoAnalysisResult:
        """Run the entire pipeline for ``video_path``."""

        uploaded = self.uploader.store(video_path, video_id=video_id)
        transcript, segments = self.transcript_generator.generate(uploaded.stored_path)

        transcript_events = (
            self.transcript_processor.process_transcript(
                video_id=uploaded.video_id,
                transcript=transcript,
            )
            if transcript
            else {
                "video_id": uploaded.video_id,
                "transcript_length": 0,
                "temporal_phrases": [],
                "profanity_instances": [],
                "force_mentions": [],
                "command_instances": [],
                "uncertainty_markers": [],
                "named_entities": [],
                "summary": {
                    "num_profanity": 0,
                    "num_force_mentions": 0,
                    "num_commands": 0,
                    "num_uncertainty": 0,
                    "num_named_entities": 0,
                },
            }
        )

        occlusion_events = self.occlusion_detector.detect(uploaded.stored_path)
        notable_moments = [
            NotableMoment(
                label="camera_occlusion",
                start_time=event.start_time,
                end_time=event.end_time,
                confidence=event.confidence,
                metadata={"duration": event.duration},
            )
            for event in occlusion_events
        ]

        return VideoAnalysisResult(
            uploaded_video=uploaded,
            transcript=transcript,
            transcript_segments=segments,
            transcript_events=transcript_events,
            video_events={"camera_occlusion": notable_moments},
        )

    def save_result(self, result: VideoAnalysisResult, output_dir: Path | str) -> Path:
        """Persist the pipeline result to ``output_dir`` as JSON."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"{result.uploaded_video.video_id}_analysis.json"
        file_path.write_text(json.dumps(result.to_dict(), indent=2))
        return file_path


__all__ = [
    "TranscriptSegment",
    "NotableMoment",
    "VideoAnalysisResult",
    "VideoAnalysisPipeline",
]
