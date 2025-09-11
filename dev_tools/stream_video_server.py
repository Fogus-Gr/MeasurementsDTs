"""
Development-only script for simulating an IP video stream using Flask.
Used for local testing of IP-stream-based HPE input.

Do NOT deploy in production.
"""

from flask import Flask, Response
import cv2
import os
import time
import numpy as np
import argparse

# Get script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Default to a relative path from the script directory
#video_path = os.path.join(SCRIPT_DIR, "videos/ultimatum/hd_00_00.mp4")

video_path = os.path.join(SCRIPT_DIR, "../video_squat.mp4")



# Add these global variables at the top (after video_path)
video_info = {
    "resolution": "N/A",
    "fps": "N/A",
    "frame_count": "N/A"
}

def initialize_video_info():
    """Initialize video information at server startup"""
    global video_path, video_info

    print(f"[INFO] Initializing video info for: {video_path}")

    # Check if file exists
    if not os.path.exists(video_path):
        print(f"[WARNING] Video file not found: {video_path}")
        return

    # Try to open video and get properties
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"[WARNING] Failed to open video file: {video_path}")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Validate and set defaults if needed
    if width <= 0 or height <= 0:
        print("[WARNING] Invalid video dimensions, using defaults")
        width, height = 640, 480

    if fps <= 0:
        print("[WARNING] FPS not found or invalid, defaulting to 30 FPS")
        fps = 30

    if frame_count <= 0:
        print("[WARNING] Frame count not found or invalid")
        frame_count = "Unknown"

    # Update video_info
    video_info["resolution"] = f"{width}x{height}"
    video_info["fps"] = f"{fps:.2f}"
    video_info["frame_count"] = str(frame_count)

    print(f"[INFO] Video info initialized: {video_info}")

    # Clean up
    cap.release()

def generate_test_pattern():
    """Generate a test pattern when no video is available"""
    # Create a 640x480 test pattern
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add colored rectangles
    img[50:150, 50:250] = [0, 0, 255]  # Red
    img[50:150, 280:480] = [0, 255, 0]  # Green
    img[200:300, 50:250] = [255, 0, 0]  # Blue
    img[200:300, 280:480] = [255, 255, 0]  # Yellow
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'Test Pattern', (180, 400), font, 1.5, (255, 255, 255), 2)
    cv2.putText(img, f'Video file not found at:', (120, 430), font, 0.6, (255, 255, 255), 1)
    cv2.putText(img, f'{video_path}', (50, 460), font, 0.5, (255, 255, 255), 1)
    
    return img

def generate_frames():
    global video_path, video_info
    
    # Print debug info
    print(f"[DEBUG] Script directory: {SCRIPT_DIR}")
    print(f"[DEBUG] Current working directory: {os.getcwd()}")
    print(f"[DEBUG] Looking for video at: {video_path}")
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found: {video_path}")
        # Generate test pattern frames
        while True:
            test_frame = generate_test_pattern()
            ret, buffer = cv2.imencode('.jpg', test_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.5)  # Update twice per second
    else:
        print(f"[INFO] Opening video from: {video_path}")
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("[ERROR] Failed to open video file")
            # Generate test pattern frames
            while True:
                test_frame = generate_test_pattern()
                ret, buffer = cv2.imencode('.jpg', test_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.5)  # Update twice per second
        else:
            # Video properties are already initialized at startup
            # Get FPS for frame timing (fallback to 30 if not available)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                print("[WARNING] FPS not found or invalid. Defaulting to 30 FPS.")
                fps = 30

            first_time = True
            frame_counter = 0
            
            while True:
                success, frame = cap.read()
                
                if not success:
                    print(f"[INFO] Video ended after {frame_counter} frames. Reopening file...")
                    cap.release()
                    time.sleep(0.1)  # Small delay to ensure file is properly released
                    cap = cv2.VideoCapture(video_path)
                    frame_counter = 0
                    if not cap.isOpened():
                        print("[ERROR] Failed to reopen video file")
                        break
                    continue
                    
                frame_counter += 1
                
                if first_time:
                    print("[INFO] Starting video stream...")
                    first_time = False
        
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
        
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                
                # Add a small delay to control frame rate
                time.sleep(1 / fps)

@app.route('/')
def index():
    """Serve a simple page with the video stream embedded"""
    return f'''
    <!DOCTYPE html>
    <html>
      <head>
        <title>Video Stream</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 20px; }}
          .container {{ max-width: 800px; margin: 0 auto; }}
          .debug {{ background: #f0f0f0; padding: 10px; margin-top: 20px; }}
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Video Stream</h1>
          <img src="/video_feed" width="640" height="480" />
          
          <div class="debug">
            <h3>Debug Information</h3>
            <p><strong>Video path:</strong> {video_path}</p>
            <p><strong>Resolution:</strong> {video_info["resolution"]}</p>
            <p><strong>FPS:</strong> {video_info["fps"]}</p>
            <p><strong>Total frames:</strong> {video_info["frame_count"]}</p>
            <p><strong>Working directory:</strong> {os.getcwd()}</p>
            <p><strong>Script directory:</strong> {SCRIPT_DIR}</p>
          </div>
        </div>
      </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Video streaming server')
    parser.add_argument('--video', type=str, help='Path to video file')
    args = parser.parse_args()
    
    # Update video path if provided via command line
    if args.video:
        video_path = args.video
        print(f"[INFO] Using video path from command line: {video_path}")

    # Initialize video information at startup
    initialize_video_info()

    print(f"[INFO] Starting server with video: {video_path}")
    print(cv2.getBuildInformation())
    app.run(host="0.0.0.0", port=8089, threaded=True)
