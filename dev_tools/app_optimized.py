import os
import cv2
import logging
import time
from flask import Flask, Response, render_template, request

# --- Configuration and Initialization ---
# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# Get video path from environment variable with fallback
video_path = os.environ.get("VIDEO_PATH", "hd_00_00_8M_trimmed_25fps.mp4")
logging.info(f"Using video path: {video_path}")

# --- Flask Routes and Generator ---
def generate_frames():
    """
    Generator to stream video frames.
    
    This function is now responsible for initializing the video capture,
    streaming the video from start to finish, and controlling the frame rate.
    Each call to this generator will start a new playback.
    """
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        logging.error(f"Error: Could not open video file at {video_path}")
        return

    # Get video FPS for timing
    fps = video.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        logging.warning("Video FPS is 0, defaulting to 25 FPS for timing.")
        fps = 25
    desired_time_per_frame = 1.0 / fps

    logging.info(f"New client connected. Streaming video at {fps} FPS.")

    while True:
        start_time = time.perf_counter()
        
        success, frame = video.read()
        if not success:
            # The video has ended. Release the video capture object and break the loop.
            logging.info("Video stream ended. Releasing video capture.")
            video.release()
            break
        
        # Encode the frame as a JPEG image
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Yield the frame in multipart format for the stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Control the frame rate to match the video's FPS
        elapsed_time = time.perf_counter() - start_time
        if elapsed_time < desired_time_per_frame:
            time.sleep(desired_time_per_frame - elapsed_time)


@app.route('/video_feed', methods=['GET', 'HEAD'])
def video_feed():
    """Route for video stream"""
    if request.method == 'HEAD':
        resp = Response('')
        resp.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    
    # Return a streaming response using the generator
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    # A basic template for viewing the stream
    return '''
    <html>
      <head>
        <title>Video Streamer</title>
      </head>
      <body>
        <h1>Live Video Feed</h1>
        <img src="/video_feed" alt="Video Stream">
      </body>
    </html>
    '''

if __name__ == '__main__':
    logging.info("Starting Flask server...")
    # The `threaded=True` option allows the server to handle multiple clients
    # at the same time, with each client getting their own stream.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8089)), threaded=True)