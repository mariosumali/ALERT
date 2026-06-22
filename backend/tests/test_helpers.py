"""Tests for the pure helper utilities."""
from utils.helpers import format_duration, get_media_duration


class TestFormatDuration:
    def test_zero(self):
        assert format_duration(0) == "00:00:00"

    def test_minutes_seconds(self):
        assert format_duration(150) == "00:02:30"

    def test_hours(self):
        assert format_duration(3661) == "01:01:01"

    def test_pads_all_fields(self):
        assert format_duration(5) == "00:00:05"


class TestGetMediaDuration:
    def test_missing_file_returns_zero(self):
        assert get_media_duration("/nonexistent/path/to/file.mp4") == 0.0
