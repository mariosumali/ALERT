"""Simple storage helper used by the web/GUI pipeline."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UploadedVideo:
    """Metadata for a stored upload."""

    source_path: Path
    stored_path: Path
    video_id: str


class VideoUploader:
    """Copies uploaded videos to the project storage directories.

    The GUI/WebUI can call this helper with the temporary upload path. The helper
    creates a predictable storage location so that later processing stages can access
    the video without worrying about user provided filenames.
    """

    def __init__(self, storage_dir: Path | str = "data/raw/uploads") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def store(self, video_path: Path | str, *, video_id: Optional[str] = None) -> UploadedVideo:
        """Copy ``video_path`` into the storage directory.

        Args:
            video_path: Path to the uploaded file provided by the user.
            video_id: Optional unique identifier to use for the stored filename. When
                omitted a unique identifier is derived from the input filename.

        Returns:
            :class:`UploadedVideo` describing the stored file.
        """

        source_path = Path(video_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Uploaded video not found: {video_path}")

        if video_id is None:
            video_id = source_path.stem

        # Ensure uniqueness by appending a suffix if necessary.
        target_path = self._unique_path(video_id, source_path.suffix)
        shutil.copy2(source_path, target_path)

        return UploadedVideo(
            source_path=source_path,
            stored_path=target_path,
            video_id=target_path.stem,
        )

    def _unique_path(self, video_id: str, extension: str) -> Path:
        base_path = self.storage_dir / f"{video_id}{extension}"
        if not base_path.exists():
            return base_path

        counter = 1
        while True:
            candidate = self.storage_dir / f"{video_id}_{counter}{extension}"
            if not candidate.exists():
                return candidate
            counter += 1
