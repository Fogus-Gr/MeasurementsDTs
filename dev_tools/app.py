import os
import cv2
import logging
from flask import Flask, Response, render_template

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# Get video path from environment variable with fallback
video_path = os.environ.get("VIDEO_PATH", "hd_00_00_8M_trimmed_25fps.mp4")
logging.info(f"Using video path: {video_path}")

# Log path information for debugging
cwd = os.getcwd()
logging.info(f"Current working directory: {cwd}")
abs_path = os.path.abspath(video_path)
logging.info(f"Absolute video path: {abs_path}")
logging.info(f"File exists: {os.path.exists(abs_path)}")

# Initialize video capture at module level (key improvement #1)
cap = None
try:
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        logging.info(f"Video details: {total_frames} frames, {fps} FPS, duration: {total_frames/fps:.2f} seconds")
    else:
        logging.error(f"Error: Could not open video at {video_path}")
except Exception as e:
    logging.error(f"Error initializing video: {e}")

def generate_frames():
    """Generate video frames for streaming (plays video once, no looping)"""
    frame_count = 0
    first_frame = True

    while True:
        if not cap or not cap.isOpened():
            logging.error("Video capture not available")
            break

        success, frame = cap.read()
        if not success:
            # Video ended, stop streaming
            logging.info("Video playback completed - stream ended")
            break

        frame_count += 1
        if first_frame:
            logging.info("Video stream started")
            first_frame = False

        # Convert frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Route for video stream"""
    logging.info(f"Client connected to video feed")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '''
    <html>
      <head>
        <title>Video Stream Player</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
          .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
          h2 { color: #333; text-align: center; }
          .status { background: #e8f5e8; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
          .note { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
          img { display: block; margin: 0 auto; border: 2px solid #ddd; border-radius: 5px; }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>▶️ Video Stream Player</h2>
          <div class="status">
            <strong>Status:</strong> Ready to stream<br>
            <strong>Source:</strong> Video file playback<br>
            <strong>Protocol:</strong> MJPEG over HTTP
          </div>
          <div class="note">
            <strong>Note:</strong> Video plays once and stops when finished (no looping)
          </div>
          <img src="/video_feed" width="640" alt="Video stream" />
        </div>
      </body>
    </html>
    '''

if __name__ == '__main__':
    logging.info("Starting Flask server...")
    # Add explicit threading (key improvement #3)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8089)), threaded=True)
