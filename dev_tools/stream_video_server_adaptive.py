"""
Adaptive Flask video streaming server for H.264 MP4 files.
Streams at original frame rate and resolution, with JPEG quality based on video.
"""

from flask import Flask, Response
import cv2
import os
import time
import numpy as np
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

video_path = os.path.join(SCRIPT_DIR, "videos/ultimatum/hd_00_00.mp4")
video_info = {
    "resolution": "N/A",
    "fps": "N/A",
    "frame_count": "N/A"
}

def generate_test_pattern():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[50:150, 50:250] = [0, 0, 255]
    img[50:150, 280:480] = [0, 255, 0]
    img[200:300, 50:250] = [255, 0, 0]
    img[200:300, 280:480] = [255, 255, 0]
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'Test Pattern', (180, 400), font, 1.5, (255, 255, 255), 2)
    cv2.putText(img, f'Video file not found at:', (120, 430), font, 0.6, (255, 255, 255), 1)
    cv2.putText(img, f'{video_path}', (50, 460), font, 0.5, (255, 255, 255), 1)
    return img

def get_jpeg_quality(width, height):
    # Use higher JPEG quality for HD, lower for VGA
    if width >= 1280 or height >= 720:
        return 90
    else:
        return 80

def generate_end_frame():
    """Generate an end frame when video finishes"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add gradient background
    for i in range(480):
        img[i, :] = [40, 40, 40 + (i // 3)]
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'End of Video', (180, 200), font, 1.5, (255, 255, 255), 2)
    cv2.putText(img, f'Video has finished playing:', (120, 260), font, 0.7, (255, 255, 255), 1)
    cv2.putText(img, f'{os.path.basename(video_path)}', (120, 300), font, 0.7, (200, 200, 255), 1)
    cv2.putText(img, f'Refresh browser to replay', (160, 400), font, 0.7, (180, 180, 180), 1)
    return img

def generate_frames():
    global video_path, video_info

    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found: {video_path}")
        while True:
            test_frame = generate_test_pattern()
            ret, buffer = cv2.imencode('.jpg', test_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.5)
    else:
        print(f"[INFO] Opening video from: {video_path}")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("[ERROR] Failed to open video file")
            while True:
                test_frame = generate_test_pattern()
                ret, buffer = cv2.imencode('.jpg', test_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.5)
        else:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if width <= 0 or height <= 0:
                width, height = 640, 480
            if fps <= 0:
                print("[WARNING] FPS not found or invalid. Defaulting to 30 FPS.")
                fps = 30
            if frame_count <= 0:
                frame_count = "Unknown"

            video_info["resolution"] = f"{width}x{height}"
            video_info["fps"] = f"{fps:.2f}"
            video_info["frame_count"] = str(frame_count)

            jpeg_quality = get_jpeg_quality(width, height)
            print(f"[INFO] Streaming at {fps} FPS, {width}x{height}, JPEG quality {jpeg_quality}")

            # For HD videos, consider downscaling for better performance
            downscale = width > 1280  # Only downscale HD videos
            target_width = 1280 if downscale else width
            target_height = int(height * (target_width / width)) if downscale else height
            
            print(f"[INFO] Original: {width}x{height}, Streaming: {target_width}x{target_height}")
            
            # Simpler frame delivery with minimal overhead
            first_time = True
            frame_counter = 0
            video_ended = False
            
            while True:
                # Show end frame if video ended
                if video_ended:
                    end_frame = generate_end_frame()
                    ret, buffer = cv2.imencode('.jpg', end_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    time.sleep(1)
                    continue
                
                # Start time measurement for this frame
                start_time = time.time()
                
                # Read frame
                success, frame = cap.read()
                if not success:
                    print(f"[INFO] Video ended after {frame_counter} frames. Not looping.")
                    video_ended = True
                    continue
                
                frame_counter += 1
                if first_time:
                    print("[INFO] Starting video stream...")
                    first_time = False
                
                # Resize if needed (for HD videos)
                if downscale:
                    frame = cv2.resize(frame, (target_width, target_height))
                
                # Encode with moderate quality (balance between speed and quality)
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                
                # Send frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
                # No timing control - run at maximum speed

@app.route('/')
def index():
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
    parser = argparse.ArgumentParser(description='Video streaming server')
    parser.add_argument('--video', type=str, help='Path to video file')
    args = parser.parse_args()
    if args.video:
        video_path = args.video
        print(f"[INFO] Using video path from command line: {video_path}")
    print(f"[INFO] Starting server with video: {video_path}")
    app.run(host="0.0.0.0", port=8089, threaded=True)