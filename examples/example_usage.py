"""Example usage of SJPD loader and transcript processor"""

from src.data_ingestion import SJPDLoader, TranscriptProcessor

# Load dataset
loader = SJPDLoader()

# Get summary
summary = loader.get_dataset_summary()
print(f"Total videos: {summary['total_videos']}")
print(f"Duration: {summary['total_duration_hours']:.1f} hours")
print(f"Videos with transcripts: {summary['videos_with_transcripts']}")

# Get videos with transcripts
videos = loader.get_videos_with_transcripts()

# Process transcripts
processor = TranscriptProcessor()
for video in videos[:3]:  # Process first 3
    results = processor.process_transcript(video['file_id'], video['transcript'])
    print(f"\n{video['file_id']}: {results['summary']}")

