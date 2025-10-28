"""
Enhanced Video Browser and Download Manager

GUI application that combines data from:
1. Transcripts spreadsheet 
2. Videos with links spreadsheet

Cross-references both datasets to provide complete video information.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pandas as pd
from pathlib import Path
import webbrowser
import subprocess
import os
import re


class VideoBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("SJPD Video Browser - Enhanced")
        self.root.geometry("1200x800")
        
        # Load data
        self.load_data()
        
        # Current video index
        self.current_idx = 0
        
        # Create GUI
        self.create_widgets()
        self.display_video(0)
    
    def load_data(self):
        """Load and merge data from both spreadsheets"""
        print("Loading spreadsheets...")
        
        try:
            # Load transcripts spreadsheet (primary source - has more videos)
            transcripts_path = "src/spreadsheets/[CS224V copy] SJPD Logging Videos - transcripts.csv"
            self.transcripts_df = pd.read_csv(transcripts_path, encoding='utf-8', on_bad_lines='skip')
            print(f"  Loaded {len(self.transcripts_df)} rows from transcripts")
            
            # Load videos with links spreadsheet (secondary source - has metadata)
            videos_path = "src/spreadsheets/[CS224V copy] SJPD Logging Videos - videos w_ links.csv"
            self.videos_df = pd.read_csv(videos_path, encoding='utf-8', on_bad_lines='skip')
            print(f"  Loaded {len(self.videos_df)} rows from videos")
            
            # Create lookup for videos metadata by gdrive_id
            self.videos_lookup = {}
            for idx, row in self.videos_df.iterrows():
                asset_url = row.get('asset_url', '')
                file_id = self.extract_file_id(asset_url)
                if file_id:
                    self.videos_lookup[file_id] = {
                        'index': idx,
                        'row': row
                    }
            
            # Build combined video list from transcripts
            self.videos = []
            for idx, row in self.transcripts_df.iterrows():
                gdrive_id = row.get('gdrive_id', '')
                if pd.notna(gdrive_id) and gdrive_id:
                    # Get metadata from videos spreadsheet if available
                    video_metadata = self.videos_lookup.get(gdrive_id, {})
                    
                    video_info = {
                        'index': idx,
                        'file_id': gdrive_id,
                        'transcript_row': row,
                        'metadata_row': video_metadata.get('row', None),
                        'has_metadata': gdrive_id in self.videos_lookup,
                    }
                    
                    self.videos.append(video_info)
            
            print(f"\n✓ Loaded {len(self.videos)} videos")
            print(f"  Videos with full metadata: {sum(1 for v in self.videos if v['has_metadata'])}")
            print(f"  Videos only in transcripts: {sum(1 for v in self.videos if not v['has_metadata'])}")
            
            self.status = f"Loaded {len(self.videos)} videos ({sum(1 for v in self.videos if v['has_metadata'])} with metadata)"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.videos = []
            self.status = f"Error loading data: {e}"
    
    def extract_file_id(self, asset_url):
        """Extract Google Drive file ID from URL"""
        if pd.isna(asset_url):
            return None
        
        pattern = r'(?:/d/|id=)([a-zA-Z0-9_-]+)'
        match = re.search(pattern, str(asset_url))
        return match.group(1) if match else None
    
    def create_widgets(self):
        """Create GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Top info bar
        info_bar = ttk.Frame(main_frame)
        info_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(info_bar, text=self.status, font=('Arial', 10))
        self.status_label.pack(side=tk.LEFT)
        
        ttk.Label(info_bar, text="Search:", font=('Arial', 10)).pack(side=tk.LEFT, padx=(20, 5))
        self.search_entry = ttk.Entry(info_bar, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', self.search_videos)
        
        ttk.Button(info_bar, text="Go", command=self.search_videos).pack(side=tk.LEFT, padx=5)
        
        # Navigation frame
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.prev_btn = ttk.Button(nav_frame, text="← Previous", command=self.prev_video)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.current_label = ttk.Label(nav_frame, text="")
        self.current_label.pack(side=tk.LEFT, padx=20)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self.next_video)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        # Filter buttons
        filter_frame = ttk.Frame(nav_frame)
        filter_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Button(filter_frame, text="Has Transcript", 
                   command=self.filter_transcripts).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="Has Metadata", 
                   command=self.filter_metadata).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="All Videos", 
                   command=self.filter_all).pack(side=tk.LEFT, padx=2)
        
        # Video info frame
        info_frame = ttk.LabelFrame(main_frame, text="Video Information", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.info_text = scrolledtext.ScrolledText(info_frame, width=60, height=25, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        actions_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N))
        
        ttk.Button(actions_frame, text="Open in Google Drive", 
                   command=self.open_drive, width=35).grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(actions_frame, text="Copy Download Link", 
                   command=self.copy_link, width=35).grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(actions_frame, text="Download with gdown", 
                   command=self.download_gdown, width=35).grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Separator(actions_frame, orient='horizontal').grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(actions_frame, text="Show Transcript", 
                   command=self.show_transcript, width=35).grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(actions_frame, text="Open Metadata", 
                   command=self.show_metadata, width=35).grid(row=5, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Grid weights
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Store original video list for filtering
        self.all_videos = self.videos[:]
    
    def display_video(self, idx):
        """Display video at index"""
        if not self.videos or idx < 0 or idx >= len(self.videos):
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, "No videos available")
            return
        
        self.current_idx = idx
        video = self.videos[idx]
        
        # Update navigation label
        self.current_label.config(text=f"Video {idx + 1} of {len(self.videos)}")
        
        # Build info text
        info = []
        info.append(f"📹 VIDEO {idx + 1} of {len(self.videos)}")
        info.append("=" * 70)
        info.append("")
        
        # Get data sources
        transcript_row = video['transcript_row']
        metadata_row = video.get('metadata_row')
        
        # File information (always available from transcripts)
        info.append("FILE INFORMATION:")
        info.append(f"  Google Drive ID: {video['file_id']}")
        
        # Get values with proper handling of NaN
        video_name = transcript_row.get('gdrive_name', 'N/A')
        if pd.notna(video_name):
            info.append(f"  Video Name: {video_name}")
        else:
            info.append(f"  Video Name: N/A")
        
        mime_type = transcript_row.get('mimeType', 'N/A')
        if pd.notna(mime_type):
            info.append(f"  MIME Type: {mime_type}")
        else:
            info.append(f"  MIME Type: N/A")
        
        sha1 = transcript_row.get('sha1', 'N/A')
        if pd.notna(sha1) and isinstance(sha1, str):
            info.append(f"  SHA1: {sha1[:20]}...")
        else:
            info.append(f"  SHA1: N/A")
        
        info.append(f"  Has Metadata: {'✓ Yes' if video['has_metadata'] else '✗ No'}")
        info.append("")
        
        # Show metadata if available
        if metadata_row:
            info.append("METADATA FROM VIDEOS SPREADSHEET:")
            info.append("")
            
            fields_to_show = [
                ('Case ID', 'SJPD Case ID'),
                ('Case', 'Case'),
                ('Video', 'Video'),
                ('Length', 'Length'),
                ('Duration (min)', 'Video length minutes'),
                ('Description', 'Description'),
            ]
            
            for label, key in fields_to_show:
                value = metadata_row.get(key, '')
                if pd.notna(value) and value:
                    info.append(f"{label}:")
                    info.append(f"  {value}")
                    info.append("")
        else:
            info.append("METADATA:")
            info.append("  Only basic info available (not in videos spreadsheet)")
            info.append("")
        
        # Transcript information
        transcript = transcript_row.get('first_look_summary', '')
        has_transcript = (pd.notna(transcript) and transcript and 
                         transcript != 'No transcription available')
        
        info.append("TRANSCRIPT:")
        if has_transcript:
            info.append(f"  ✓ Available ({len(str(transcript))} characters)")
            preview = str(transcript)[:200] + "..." if len(transcript) > 200 else str(transcript)
            info.append(f"  Preview: {preview}")
        else:
            info.append("  ✗ No transcript available")
        info.append("")
        
        # Additional info from transcripts
        case_name = transcript_row.get('provisional_case_name', '')
        incident_date = transcript_row.get('incident_date', '')
        
        if pd.notna(case_name) and case_name and str(case_name) != '✗':
            info.append(f"Case Name: {case_name}")
        if pd.notna(incident_date) and incident_date and str(incident_date) != '✗':
            info.append(f"Incident Date: {incident_date}")
        
        # Display
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, "\n".join(info))
    
    def search_videos(self, event=None):
        """Search videos by name or case"""
        query = self.search_entry.get().lower()
        
        if not query:
            self.videos = self.all_videos[:]
        else:
            filtered = []
            for video in self.all_videos:
                name = str(video['transcript_row'].get('gdrive_name', '')).lower()
                if query in name:
                    filtered.append(video)
            
            self.videos = filtered
        
        if self.videos:
            self.display_video(0)
        else:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, "No videos found")
    
    def filter_transcripts(self):
        """Filter to videos with transcripts"""
        self.videos = [v for v in self.all_videos 
                      if pd.notna(v['transcript_row'].get('first_look_summary', '')) 
                      and v['transcript_row'].get('first_look_summary', '')]
        if self.videos:
            self.display_video(0)
    
    def filter_metadata(self):
        """Filter to videos with full metadata"""
        self.videos = [v for v in self.all_videos if v['has_metadata']]
        if self.videos:
            self.display_video(0)
    
    def filter_all(self):
        """Show all videos"""
        self.videos = self.all_videos[:]
        if self.videos:
            self.display_video(0)
    
    def prev_video(self):
        """Show previous video"""
        if self.current_idx > 0:
            self.display_video(self.current_idx - 1)
        else:
            messagebox.showinfo("Info", "Already at first video")
    
    def next_video(self):
        """Show next video"""
        if self.current_idx < len(self.videos) - 1:
            self.display_video(self.current_idx + 1)
        else:
            messagebox.showinfo("Info", "Already at last video")
    
    def open_drive(self):
        """Open video in Google Drive"""
        if not self.videos:
            return
        
        video = self.videos[self.current_idx]
        url = f"https://drive.google.com/file/d/{video['file_id']}/view"
        webbrowser.open(url)
    
    def copy_link(self):
        """Copy download link to clipboard"""
        if not self.videos:
            return
        
        video = self.videos[self.current_idx]
        link = f"https://drive.google.com/uc?export=download&id={video['file_id']}"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        messagebox.showinfo("Copied", "Download link copied to clipboard!")
    
    def download_gdown(self):
        """Download video using gdown command"""
        if not self.videos:
            return
        
        video = self.videos[self.current_idx]
        
        # Check if gdown is installed
        try:
            result = subprocess.run(['which', 'gdown'], capture_output=True, text=True)
            if result.returncode != 0:
                messagebox.showerror("Error", 
                    "gdown not found. Install with: pip install gdown")
                return
        except:
            messagebox.showerror("Error", "Unable to check for gdown")
            return
        
        # Get video name
        video_name = video['transcript_row'].get('gdrive_name', 'video')
        safe_name = "".join(c for c in video_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        file_id = video['file_id']
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{safe_name}.mp4"
        
        # Download
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        cmd = ['gdown', url, '-O', str(output_file)]
        
        messagebox.showinfo("Downloading", f"Starting download to {output_file}")
        
        try:
            subprocess.run(cmd, check=True)
            messagebox.showinfo("Success", f"Downloaded to {output_file}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Download failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Download error: {e}")
    
    def show_transcript(self):
        """Show transcript in a new window"""
        if not self.videos:
            return
        
        video = self.videos[self.current_idx]
        transcript = video['transcript_row'].get('first_look_summary', '')
        
        if not transcript or pd.isna(transcript) or transcript == 'No transcription available':
            messagebox.showinfo("No Transcript", "No transcript available for this video")
            return
        
        # Create transcript window
        transcript_window = tk.Toplevel(self.root)
        transcript_window.title(f"Transcript - {video['transcript_row'].get('gdrive_name', 'Video')}")
        transcript_window.geometry("900x700")
        
        text_widget = scrolledtext.ScrolledText(transcript_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, transcript)
        text_widget.config(state=tk.DISABLED)
    
    def show_metadata(self):
        """Show full metadata in a new window"""
        if not self.videos:
            return
        
        video = self.videos[self.current_idx]
        
        metadata_window = tk.Toplevel(self.root)
        metadata_window.title("Full Metadata")
        metadata_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(metadata_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Show all metadata
        lines = []
        lines.append("=== TRANSCRIPT ROW DATA ===")
        for key, value in video['transcript_row'].items():
            if pd.notna(value) and value:
                lines.append(f"{key}: {value}")
        
        if video['has_metadata']:
            lines.append("\n=== METADATA ROW DATA ===")
            for key, value in video['metadata_row'].items():
                if pd.notna(value) and value:
                    lines.append(f"{key}: {value}")
        
        text_widget.insert(1.0, "\n".join(lines))
        text_widget.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = VideoBrowser(root)
    root.mainloop()


if __name__ == "__main__":
    main()
