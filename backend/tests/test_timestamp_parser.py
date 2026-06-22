"""Tests for natural-language timestamp parsing and formatting."""
from utils.timestamp_parser import parse_timestamps, format_timestamp


class TestParseTimestamps:
    def test_mm_ss(self):
        assert 150.0 in parse_timestamps("look at 2:30 in the video")

    def test_hh_mm_ss(self):
        # 1:23:45 -> 5025 seconds
        assert 5025.0 in parse_timestamps("the event at 1:23:45 is key")

    def test_leading_zero_mm_ss(self):
        assert 45.0 in parse_timestamps("around 0:45")

    def test_x_seconds(self):
        assert 45.0 in parse_timestamps("at 45 seconds something happens")

    def test_x_minutes(self):
        assert 120.0 in parse_timestamps("about 2 minutes in")

    def test_minutes_and_seconds(self):
        assert 150.0 in parse_timestamps("2 minutes 30 seconds")

    def test_results_sorted_and_unique(self):
        result = parse_timestamps("at 0:30 and again at 30 seconds and 1:00")
        assert result == sorted(result)
        assert len(result) == len(set(result))

    def test_no_timestamps(self):
        assert parse_timestamps("what happened in this video?") == []

    def test_empty_string(self):
        assert parse_timestamps("") == []


class TestFormatTimestamp:
    def test_under_an_hour(self):
        assert format_timestamp(150) == "2:30"

    def test_over_an_hour(self):
        assert format_timestamp(5025) == "1:23:45"

    def test_zero(self):
        assert format_timestamp(0) == "0:00"

    def test_pads_seconds(self):
        assert format_timestamp(65) == "1:05"
