"""
Transcript Processor

Processes and aligns transcripts with video data for event detection.
"""

import re
from typing import Dict, List, Tuple
from pathlib import Path


class TranscriptProcessor:
    """Processes transcripts for event detection."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        # Keywords for detecting events
        self.profanity_keywords = self._load_profanity_list()
        self.force_keywords = ['force', 'restrain', 'hold down', 'cuff', 'pat down', 'search']
        self.command_keywords = ['stop', 'hands up', 'get down', 'don\'t move', 'freeze']
        self.uncertainty_indicators = ['maybe', 'might', 'could', 'perhaps', 'seems like']
    
    def _load_profanity_list(self) -> List[str]:
        """Load list of profanity/strong language keywords."""
        # You can expand this list or load from a file
        return ['damn', 'crap', 'hell', 'jerk', 'stupid']  # Add more as needed
    
    def extract_temporal_phrases(self, text: str) -> List[Dict]:
        """
        Extract temporal language indicating timing of events.
        
        Args:
            text: Transcript text
            
        Returns:
            List of temporal phrases with context
        """
        temporal_patterns = [
            r'before [a-z\s]+ arrest',
            r'after [a-z\s]+ arrest',
            r'during [a-z\s]+ stop',
            r'while [a-z\s]+ handcuff',
            r'at [0-9]+:[0-9]+',
            r'for [0-9]+\s*(minute|second|hour)',
        ]
        
        phrases = []
        for pattern in temporal_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                phrases.append({
                    'phrase': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'temporal'
                })
        
        return phrases
    
    def detect_profanity(self, text: str) -> List[Dict]:
        """
        Detect profanity or strong emotional language.
        
        Args:
            text: Transcript text
            
        Returns:
            List of detected profanity instances
        """
        instances = []
        text_lower = text.lower()
        
        for keyword in self.profanity_keywords:
            pattern = re.compile(r'\b' + keyword + r'\b', re.IGNORECASE)
            matches = re.finditer(pattern, text)
            for match in matches:
                instances.append({
                    'keyword': keyword,
                    'start': match.start(),
                    'end': match.end(),
                    'context': text[max(0, match.start()-20):match.end()+20]
                })
        
        return instances
    
    def detect_force_mentions(self, text: str) -> List[Dict]:
        """
        Detect mentions of force usage.
        
        Args:
            text: Transcript text
            
        Returns:
            List of force-related mentions
        """
        instances = []
        
        for keyword in self.force_keywords:
            pattern = re.compile(r'\b' + keyword + r'\b', re.IGNORECASE)
            matches = re.finditer(pattern, text)
            for match in matches:
                instances.append({
                    'keyword': keyword,
                    'start': match.start(),
                    'end': match.end(),
                    'context': text[max(0, match.start()-30):match.end()+30]
                })
        
        return instances
    
    def detect_command_speech(self, text: str) -> List[Dict]:
        """
        Detect command-style speech patterns.
        
        Args:
            text: Transcript text
            
        Returns:
            List of command phrases
        """
        instances = []
        
        for keyword in self.command_keywords:
            pattern = re.compile(r'\b' + keyword + r'\b', re.IGNORECASE)
            matches = re.finditer(pattern, text)
            for match in matches:
                instances.append({
                    'keyword': keyword,
                    'start': match.start(),
                    'end': match.end(),
                    'context': text[max(0, match.start()-20):match.end()+30]
                })
        
        return instances
    
    def detect_uncertainty(self, text: str) -> List[Dict]:
        """
        Detect linguistic uncertainty markers.
        
        Args:
            text: Transcript text
            
        Returns:
            List of uncertainty markers
        """
        instances = []
        text_lower = text.lower()
        
        for marker in self.uncertainty_indicators:
            pattern = re.compile(r'\b' + marker + r'\b', re.IGNORECASE)
            matches = re.finditer(pattern, text)
            for match in matches:
                instances.append({
                    'marker': marker,
                    'start': match.start(),
                    'end': match.end(),
                    'context': text[max(0, match.start()-30):match.end()+30]
                })
        
        return instances
    
    def extract_named_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities (officer names, locations, etc.).
        
        Args:
            text: Transcript text
            
        Returns:
            List of named entities
        """
        # Simplified named entity extraction
        # For better results, integrate with spaCy
        entities = []
        
        # Pattern for officer names (Officer [Name], Deputy [Name], etc.)
        officer_pattern = r'\b(?:Officer|Deputy|Lieutenant|Sergeant|Detective)\s+([A-Z][a-z]+)'
        officer_matches = re.finditer(officer_pattern, text)
        for match in officer_matches:
            entities.append({
                'entity': match.group(0),
                'type': 'officer',
                'name': match.group(1),
                'start': match.start(),
                'end': match.end()
            })
        
        return entities
    
    def process_transcript(self, video_id: int, transcript: str) -> Dict:
        """
        Process a complete transcript and extract all event indicators.
        
        Args:
            video_id: Video identifier
            transcript: Full transcript text
            
        Returns:
            Dictionary with all detected events and indicators
        """
        return {
            'video_id': video_id,
            'transcript_length': len(transcript),
            'temporal_phrases': self.extract_temporal_phrases(transcript),
            'profanity_instances': self.detect_profanity(transcript),
            'force_mentions': self.detect_force_mentions(transcript),
            'command_instances': self.detect_command_speech(transcript),
            'uncertainty_markers': self.detect_uncertainty(transcript),
            'named_entities': self.extract_named_entities(transcript),
            'summary': {
                'num_profanity': len(self.detect_profanity(transcript)),
                'num_force_mentions': len(self.detect_force_mentions(transcript)),
                'num_commands': len(self.detect_command_speech(transcript)),
                'num_uncertainty': len(self.detect_uncertainty(transcript)),
                'num_named_entities': len(self.extract_named_entities(transcript)),
            }
        }
    
    def save_processed_transcript(self, video_id: int, results: Dict, output_dir: str):
        """
        Save processed transcript results.
        
        Args:
            video_id: Video identifier
            results: Processed transcript results
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_file = output_path / f"video_{video_id}_transcript_analysis.json"
        
        # TODO: Use proper JSON serialization
        output_file.write_text(str(results))


if __name__ == "__main__":
    # Example usage
    processor = TranscriptProcessor()
    
    transcript = """
    Officer Smith: Stop right there! Hands up!
    Subject: What? Why?
    Officer Smith: Get down on the ground now!
    [Multiple officers arrive]
    Officer Jones: He's resisting!
    Subject: You're hurting me! This is excessive force!
    Officer Smith: Stop resisting! We're going to cuff you.
    """
    
    results = processor.process_transcript(video_id=0, transcript=transcript)
    print(f"Detected {results['summary']['num_commands']} commands")
    print(f"Detected {results['summary']['num_force_mentions']} force mentions")

