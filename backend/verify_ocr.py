import sys
import os

# Add current directory to path so we can import services
sys.path.append(os.getcwd())

from services.ocr_extraction import extract_metadata_from_video

def verify_ocr():
    # Path to the video file (mounted in the container)
    # The container mounts ./backend to /app
    # The video is in the root, so it's at /app/../19-124-0413 BWC_Redacted-2.mp4
    # But wait, the docker-compose says:
    # - ./backend:/app
    # - ./uploads:/app/uploads
    # The video is in the root of the repo. It is NOT mounted into the backend container by default!
    # I need to check if I can access it.
    
    # Let's check if the video is available.
    # If not, I might need to copy it or use a mock.
    # But wait, the user said "Verify that all features work".
    # If the video isn't in the container, the app can't process it anyway unless it's uploaded.
    # But I want to verify the *logic* on a sample.
    
    # I'll try to find a video file.
    video_path = "/app/../19-124-0413 BWC_Redacted-2.mp4" # This won't work if not mounted.
    
    # Let's assume I can't access the root video from the container easily without changing docker-compose.
    # I'll check if there are any files in uploads.
    
    uploads_dir = "/app/uploads"
    video_files = [f for f in os.listdir(uploads_dir) if f.endswith('.mp4')]
    
    if not video_files:
        print("No video files found in uploads directory to test.")
        # I can try to test with a dummy image if I had one, but I don't.
        # I'll just check if the function runs without crashing on a non-existent file (it should return None/empty).
        print("Testing with non-existent file to verify error handling...")
        result = extract_metadata_from_video("non_existent.mp4")
        print(f"Result for non-existent file: {result}")
        return

    test_video = os.path.join(uploads_dir, video_files[0])
    print(f"Testing OCR on {test_video}...")
    
    try:
        metadata = extract_metadata_from_video(test_video)
        print("\nOCR Extraction Results:")
        print("-" * 30)
        for k, v in metadata.items():
            if k == "raw_text":
                print(f"{k}: {v[:100]}..." if v else f"{k}: None")
            else:
                print(f"{k}: {v}")
        print("-" * 30)
        
        if any(v for k, v in metadata.items() if k != "raw_text" and v):
            print("SUCCESS: Extracted some metadata!")
        else:
            print("WARNING: No specific metadata fields extracted (only raw text maybe).")
            
    except Exception as e:
        print(f"ERROR: OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_ocr()
