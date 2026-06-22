"""Tests for the pure (non-ffmpeg) helpers in video_chunking."""
from services.video_chunking import (
    seconds_to_timestamp,
    timestamp_to_seconds,
    make_segment_path,
    shift_timestamps_in_json,
    _calc_target_bitrate_kbps,
)


class TestTimestampConversion:
    def test_seconds_to_timestamp(self):
        assert seconds_to_timestamp(0) == "00:00"
        assert seconds_to_timestamp(75) == "01:15"
        assert seconds_to_timestamp(5) == "00:05"

    def test_timestamp_to_seconds_mm_ss(self):
        assert timestamp_to_seconds("01:15") == 75
        assert timestamp_to_seconds("2:30") == 150

    def test_timestamp_to_seconds_hh_mm_ss(self):
        assert timestamp_to_seconds("1:00:00") == 3600

    def test_timestamp_to_seconds_invalid(self):
        assert timestamp_to_seconds("garbage") == 0

    def test_round_trip(self):
        for sec in (0, 5, 59, 60, 125, 3599):
            assert timestamp_to_seconds(seconds_to_timestamp(sec)) == sec


class TestMakeSegmentPath:
    def test_colons_become_dashes_and_mp4_suffix(self):
        path = make_segment_path("/segments", "/uploads/abc.webm", "00:00", "05:00")
        assert path.endswith(".mp4")
        assert ":" not in path.rsplit("/", 1)[-1]
        assert "abc" in path


class TestShiftTimestamps:
    def test_shifts_numeric_sec_keys(self):
        obj = {"start_sec": 10.0, "end_sec": 20.0, "label": "x"}
        shifted = shift_timestamps_in_json(obj, 100.0)
        assert shifted["start_sec"] == 110.0
        assert shifted["end_sec"] == 120.0
        assert shifted["label"] == "x"

    def test_shifts_nested(self):
        obj = {"events": [{"time_sec": 5.0}]}
        shifted = shift_timestamps_in_json(obj, 50.0)
        assert shifted["events"][0]["time_sec"] == 55.0

    def test_shifts_string_timestamps(self):
        obj = {"summary": "gunshot at 0:10"}
        shifted = shift_timestamps_in_json(obj, 60.0)
        assert "1:10" in shifted["summary"]


class TestBitrateCalc:
    def test_positive(self):
        assert _calc_target_bitrate_kbps(25.0, 300.0) > 0

    def test_handles_zero_duration(self):
        # Should not raise ZeroDivisionError.
        assert _calc_target_bitrate_kbps(25.0, 0.0) > 0
