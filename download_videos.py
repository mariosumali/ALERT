"""
Interactive Video Browser and Download Manager

GUI application for browsing SJPD videos and downloading from Google Drive.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pandas as pd
from pathlib import Path
import webbrowser
import subprocess
import os


class VideoBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("SJPD Video Browser")
        self.root.geometry("1000x700")
        
        # Load data
        self.load_data()
        
        # Current video index
        self.current_idx = 0
        
        # Create GUI
        self.create_widgets()
        self.display_video(0)
    
    def load_data(self):
        """Load SJPD video data from spreadsheets"""
        print("Loading spreadsheets...")
        
        try:
            # Load videos spreadsheet
            videos_path = "src/spreadsheets/[CS224V copy] SJPD Logging Videos - videos w_ links.csv"
            self.videos_df = pd.read_csv(videos_path, encoding='utf-8', on_bad_lines='skip')
            
            # Load transcripts
            transcripts_path = "src/spreadsheets/[CS224V copy] SJPD Logging Videos - transcripts.csv"
            self.transcripts_df = pd.read_csv(transcripts_path, encoding='utf-8', on_bad_lines='skip')
            
            # Create lookup for transcripts
            self.transcript_lookup = {}
            for _, row in self.transcripts_df.iterrows():
                gdrive_id = row.get('gdrive_id', '')
                if pd.notna(gdrive_id) and gdrive_id:
                    transcript = row.get('first_look_summary', '')
                    self.transcript_lookup[gdrive_id] = transcript if pd.notna(transcript) else ''
            
            # Extract file IDs and prepare video list
            self.videos = []
            for idx, row in self.videos_df.iterrows():
                asset_url = row.get('asset_url', '')
                file_id = self.extract_file_id(asset_url)
                
                if file_id:
                    self.videos.append({
                        'index': idx,
                        'file_id': file_id,
                        'row': row,
                        'transcript': self.transcript_lookup.get(file_id, 'No transcript available')
                    })
            
            print(f"Loaded {len(self.videos)} videos")
            self.status = f"Loaded {len(self.videos)} videos"
            
        except Exception as e:
            print(f"Error loading data: {e}")
            self.videos = []
            self.status = f"Error loading data: {e}"
    
    def extract_file_id(self, asset_url):
        """Extract Google Drive file ID from URL"""
        import re
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
        
        # Navigation frame
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.prev_btn = ttk.Button(nav_frame, text="← Previous", command=self.prev_video)
        self.prev_btn.grid(row=0, column=0, padx=5)
        
        self.current_label = ttk.Label(nav_frame, text="")
        self.current_label.grid(row=0, column=1, padx=20)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self.next_video)
        self.next_btn.grid(row=0, column=2, padx=5)
        
        # Video info frame
        info_frame = ttk.LabelFrame(main_frame, text="Video Information", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.info_text = scrolledtext.ScrolledText(info_frame, width=60, height=20, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        actions_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 0))
        
        ttk.Button(actions_frame, text="Open in Google Drive", 
                   command=self.open_drive, width=30).grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(actions_frame, text="Copy Download Link", 
                   command=self.copy_link, width=30).grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(actions_frame, text="Download with gdown", 
                   command=self.download_gdown, width=30).grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Separator(actions_frame, orient='horizontal').grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(actions_frame, text="Show Transcript", 
                   command=self.show_transcript, width=30).grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Grid weights
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def display_video(self, idx):
        """Display video at index"""
        if not self.videos or idx < 0 or idx >= len(self.videos):
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, "No videos available")
            return
        
        self.current_idx = idx
        video = self.videos[idx]
        row = video['row']
        
        # Update navigation label
        self.current_label.config(text=f"Video {idx + 1} of {len(self.videos)}")
        
        # Build info text
        info = []
        info.append(f"📹 VIDEO {idx + 1} of {len(self.videos)}")
        info.append("=" * 60)
        info.append("")
        
        # Extract and display key information
        fields_to_show = [
            ('Case', 'Case'),
            ('SJPD Case ID', 'SJPD Case ID'),
            ('Video Name', 'Video'),
            ('Length', 'Length'),
            ('Duration (mins)', 'Video length minutes'),
            ('Description', 'Description'),
            ('Internal Description', 'case_internal_description'),
            ('Publication Summary', 'case_summary_publication'),
        ]
        
        for label, key in fields_to_show:
            value = row.get(key, '')
            if pd.notna(value) and value:
                info.append(f"{label}:")
                info.append(f"  {value}")
                info.append("")
        
        # File info
        info.append("File Information:")
        info.append(f"  File ID: {video['file_id']}")
        info.append(f"  MIME Type: {row.get('mimeType', 'N/A')}")
        info.append(f"  SHA1: {row.get('sha1', 'N/A')[:20]}...")
        info.append("")
        
        # Has redaction?
        if row.get('has redaction'):
            info.append("⚠️  REDACTED VIDEO")
            info.append("")
        
        # Transcript info
        if video['transcript'] and video['transcript'] != 'No transcript available':
            info.append("Transcript:")
            info.append(f"  {len(video['transcript'])} characters")
            info.append("")
        
        # Display
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, "\n".join(info))
    
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
        # Direct download link
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
        
        # Prepare download
        file_id = video['file_id']
        row = video['row']
        video_name = row.get('Video', 'video')
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean filename
        safe_name = "".join(c for c in video_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
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
        transcript = video['transcript']
        
        if not transcript or transcript == 'No transcript available':
            messagebox.showinfo("No Transcript", "No transcript available for this video")
            return
        
        # Create transcript window
        transcript_window = tk.Toplevel(self.root)
        transcript_window.title(f"Transcript - {video['row'].get('Video', 'Video')}")
        transcript_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(transcript_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, transcript)
        text_widget.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = VideoBrowser(root)
    root.mainloop()


if __name__ == "__main__":
    main()

