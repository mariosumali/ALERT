"""
Data Ingestion Module

Handles loading videos from spreadsheets, downloading from Google Drive,
and processing transcripts.
"""

from .transcript_processor import TranscriptProcessor
from .sjpd_loader import SJPDLoader

__all__ = ['TranscriptProcessor', 'SJPDLoader']

