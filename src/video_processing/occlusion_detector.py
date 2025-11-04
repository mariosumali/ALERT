"""Video occlusion detection utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2


@dataclass
class OcclusionEvent:
    """Information about an occlusion event detected in a video."""

    start_time: float
    end_time: float
    confidence: float

    @property
    def duration(self) -> float:
        """Return the duration (seconds) of the occlusion event."""

        return max(0.0, self.end_time - self.start_time)


class OcclusionDetector:
    """Detects periods of low visibility/occlusion in a video file.

    The detector analyses the average brightness of frames in a video. Long stretches
    of very dark or very bright frames (depending on the threshold) can indicate the
    camera being covered or pointed at an obstruction. The algorithm keeps the
    implementation intentionally lightweight so that it can run inside the GUI/web UI
    pipeline without external services.
    """

    def __init__(
        self,
        *,
        frame_skip: int = 5,
        occlusion_threshold: float = 20.0,
        min_event_duration: float = 1.0,
    ) -> None:
        """Create a new detector.

        Args:
            frame_skip: Number of frames to skip between brightness checks. A value
                of 5 means every 5th frame is examined, reducing computation time on
                long recordings.
            occlusion_threshold: Average grayscale intensity threshold (0-255). Frames
                with mean intensity lower than this value are treated as occluded.
            min_event_duration: Minimum duration (seconds) before marking an occlusion
                event. Helps filter out very short occlusion blips that are usually
                noise.
        """

        if frame_skip < 1:
            raise ValueError("frame_skip must be >= 1")

        self.frame_skip = frame_skip
        self.occlusion_threshold = occlusion_threshold
        self.min_event_duration = min_event_duration

    def detect(self, video_path: Path | str) -> List[OcclusionEvent]:
        """Detect occlusion events in a video.

        Args:
            video_path: Path to the video file.

        Returns:
            A list of :class:`OcclusionEvent` objects representing the detected
            occlusion periods.
        """

        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video: {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_index = 0
        occlusion_start = None
        events: List[OcclusionEvent] = []

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                if frame_index % self.frame_skip != 0:
                    frame_index += 1
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = float(gray.mean())
                timestamp = frame_index / fps

                if brightness <= self.occlusion_threshold:
                    if occlusion_start is None:
                        occlusion_start = timestamp
                else:
                    if occlusion_start is not None:
                        self._finalize_event(
                            events,
                            occlusion_start,
                            timestamp,
                            fps,
                        )
                        occlusion_start = None

                frame_index += 1

            # Finalise event if video ended during occlusion
            if occlusion_start is not None:
                video_duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps
                self._finalize_event(events, occlusion_start, video_duration, fps)
        finally:
            capture.release()

        return events

    def _finalize_event(
        self,
        events: List[OcclusionEvent],
        start: float,
        end: float,
        fps: float,
    ) -> None:
        """Append an occlusion event if it meets the minimum duration."""

        duration = max(0.0, end - start)
        if duration < self.min_event_duration:
            return

        # Confidence is inversely proportional to duration variability; here we use a
        # simple heuristic based on duration relative to the minimum threshold.
        confidence = min(1.0, duration / max(self.min_event_duration, 1e-6))
        events.append(OcclusionEvent(start_time=start, end_time=end, confidence=confidence))


__all__ = ["OcclusionDetector", "OcclusionEvent"]
