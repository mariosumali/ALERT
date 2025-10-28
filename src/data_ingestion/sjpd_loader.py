"""
Customized SJPD Spreadsheet Loader

Handles the specific structure of SJPD spreadsheets with:
- Video metadata spreadsheet
- Separate transcripts spreadsheet
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re


class SJPDLoader:
    """Loads and manages SJPD video metadata and transcripts."""
    
    def __init__(self, 
                 videos_path: str = "src/spreadsheets/[CS224V copy] SJPD Logging Videos - videos w_ links.csv",
                 transcripts_path: str = "src/spreadsheets/[CS224V copy] SJPD Logging Videos - transcripts.csv"):
        """
        Initialize the SJPD loader.
        
        Args:
            videos_path: Path to CSV file with video links and metadata
            transcripts_path: Path to CSV file with transcripts
        """
        self.videos_path = videos_path
        self.transcripts_path = transcripts_path
        
        # Load spreadsheets
        self.videos_df = self._load_csv(videos_path)
        self.transcripts_df = self._load_csv(transcripts_path)
        
        # Create lookup dictionaries
        self._create_lookups()
        
    def _load_csv(self, path: str) -> pd.DataFrame:
        """Load CSV file with proper encoding handling."""
        try:
            return pd.read_csv(path, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding='latin-1')
    
    def _create_lookups(self):
        """Create lookup dictionaries for fast access."""
        # Index transcripts by gdrive_id
        self.transcript_lookup = {}
        for _, row in self.transcripts_df.iterrows():
            gdrive_id = row.get('gdrive_id', '')
            if pd.notna(gdrive_id) and gdrive_id:
                transcript_text = row.get('first_look_summary', '')
                self.transcript_lookup[gdrive_id] = transcript_text if pd.notna(transcript_text) else ''
    
    def extract_file_id(self, asset_url: str) -> Optional[str]:
        """
        Extract Google Drive file ID from URL.
        
        Args:
            asset_url: Google Drive URL
            
        Returns:
            File ID or None
        """
        if pd.isna(asset_url):
            return None
        
        # Extract from /d/FILE_ID/ or ?id=FILE_ID
        pattern = r'(?:/d/|id=)([a-zA-Z0-9_-]+)'
        match = re.search(pattern, str(asset_url))
        return match.group(1) if match else None
    
    def get_videos(self) -> List[Dict]:
        """
        Get all videos with metadata and transcripts.
        
        Returns:
            List of dictionaries containing video information
        """
        videos = []
        
        for idx, row in self.videos_df.iterrows():
            # Extract Google Drive file ID
            asset_url = row.get('asset_url', '')
            file_id = self.extract_file_id(asset_url)
            
            if not file_id:
                continue
            
            # Get transcript if available
            transcript = self.transcript_lookup.get(file_id, '')
            
            # Extract video information
            video_info = {
                'row_id': idx,
                'file_id': file_id,
                'google_drive_link': asset_url,
                'transcript': transcript,
                'case_id': row.get('Case', ''),
                'sjpd_case_id': row.get('SJPD Case ID', ''),
                'video_name': row.get('Video', ''),
                'length': row.get('Length', ''),
                'hours': row.get('Hours', ''),
                'minutes': row.get('Minutes', ''),
                'seconds': row.get('Seconds', ''),
                'duration_minutes': row.get('Video length minutes', ''),
                'description': row.get('Description', ''),
                'case_internal_description': row.get('case_internal_description', ''),
                'case_summary_publication': row.get('case_summary_publication', ''),
                'has_redaction': row.get('has redaction', ''),
                'notes': row.get('Extra Notes', ''),
                'mime_type': row.get('mimeType', 'video/mp4'),
                'sha1': row.get('sha1', ''),
            }
            
            videos.append(video_info)
        
        return videos
    
    def get_videos_with_transcripts(self) -> List[Dict]:
        """Get only videos that have transcripts available."""
        all_videos = self.get_videos()
        return [v for v in all_videos if v.get('transcript', '').strip()]
    
    def get_transcript(self, file_id: str) -> str:
        """
        Get transcript for a specific video by file ID.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Transcript text or empty string
        """
        return self.transcript_lookup.get(file_id, '')
    
    def get_dataset_summary(self) -> Dict:
        """
        Get summary statistics about the dataset.
        
        Returns:
            Dictionary with dataset statistics
        """
        all_videos = self.get_videos()
        videos_with_transcripts = self.get_videos_with_transcripts()
        
        # Calculate total duration
        total_duration = self.videos_df['Video length minutes'].sum()
        
        # Count by type
        video_types = self.videos_df['mimeType'].value_counts().to_dict()
        
        # Count by case
        unique_cases = self.videos_df['Case'].nunique()
        
        return {
            'total_videos': len(all_videos),
            'videos_with_transcripts': len(videos_with_transcripts),
            'total_duration_minutes': total_duration,
            'total_duration_hours': total_duration / 60,
            'unique_cases': unique_cases,
            'video_types': video_types,
            'average_video_length_minutes': self.videos_df['Video length minutes'].mean(),
        }
    
    def get_case_videos(self, case_id: str) -> List[Dict]:
        """
        Get all videos for a specific case.
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of video dictionaries for the case
        """
        all_videos = self.get_videos()
        return [v for v in all_videos if v.get('sjpd_case_id') == case_id]


def main():
    """Example usage of SJPDLoader."""
    loader = SJPDLoader()
    
    print(f"Loaded {len(loader.videos_df)} videos from spreadsheet")
    print(f"Loaded {len(loader.transcripts_df)} transcript entries")
    
    # Get summary
    summary = loader.get_dataset_summary()
    print("\nDataset Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Get videos with transcripts
    videos_with_transcripts = loader.get_videos_with_transcripts()
    print(f"\nVideos with transcripts: {len(videos_with_transcripts)}")
    
    # Example: Get first video
    if videos_with_transcripts:
        example = videos_with_transcripts[0]
        print(f"\nExample video:")
        print(f"  File ID: {example['file_id']}")
        print(f"  Case ID: {example['case_id']}")
        print(f"  Description: {example['description'][:100] if example['description'] else 'N/A'}...")
        print(f"  Transcript length: {len(example['transcript'])} chars")


if __name__ == "__main__":
    main()

