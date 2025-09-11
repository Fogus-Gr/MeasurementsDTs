import os
import subprocess
import logging
from flask import Flask, Response, request

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)

# Get video path from environment variable with fallback
video_path = os.environ.get("VIDEO_PATH", "hd_00_00_8M_trimmed_25fps.mp4")
logging.info(f"Using video path: {video_path}")

def log_video_details(video_path_arg):
    """Logs FPS, total frames, and duration of the video using ffprobe."""
    try:
        # Ensure we have an absolute path for ffprobe
        abs_video_path = os.path.abspath(video_path_arg)
        logging.info(f"Probing video file at: {abs_video_path}")

        # Get FPS
        fps_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=avg_frame_rate', '-of', 'default=noprint_wrappers=1:nokey=1', abs_video_path]
        fps_process = subprocess.run(fps_cmd, capture_output=True, text=True, check=True)
        fps_str = fps_process.stdout.strip()
        
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            fps = num / den
        else:
            fps = float(fps_str)

        # Get total frames
        frames_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames', '-of', 'default=noprint_wrappers=1:nokey=1', abs_video_path]
        frames_process = subprocess.run(frames_cmd, capture_output=True, text=True, check=True)
        total_frames = int(frames_process.stdout.strip())

        if fps > 0:
            duration = total_frames / fps
            logging.info(f"Video details: {total_frames} frames, {fps:.2f} FPS, duration: {duration:.2f} seconds")
        else:
            logging.warning("Could not determine video FPS or total frames.")

    except FileNotFoundError:
        logging.error("ffprobe command not found. Cannot log video details.")
    except subprocess.CalledProcessError as e:
        logging.error(f"ffprobe command failed to execute: {e}")
    except ValueError:
        logging.error(f"Could not parse video details from ffprobe output: FPS='{fps_str}', Frames='{total_frames}'")
    except Exception as e:
        logging.error(f"An unexpected error occurred while logging video details: {e}")

# Check if ffmpeg is available
try:
    # Use DEVNULL for stderr to suppress version output
    subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    logging.info("ffmpeg is available.")
    # Log video details if ffmpeg is available
    log_video_details(video_path)
except FileNotFoundError:
    logging.error("ffmpeg command not found. Please install ffmpeg and ensure it's in your PATH.")
    # In a real application, you might want to exit or raise an exception here
except subprocess.CalledProcessError:
    logging.error("ffmpeg command failed to execute.")
    # In a real application, you might want to exit or raise an exception here


def generate_frames():
    """Generate video frames using ffmpeg for streaming, reading complete JPEG frames."""
    ffmpeg_cmd = [
        'ffmpeg',
        # '-stream_loop', '-1',           # Loop video indefinitely
        '-re',                          # Real-time playback
        '-i', video_path,
        '-f', 'mjpeg',                  # MJPEG format
        '-r', '25',                     # Target input video FPS
        '-vf', 'scale=1280:720',        # Simulate 720p webcam resolution
        '-q:v', '3',                    # Video quality (0-5, lower is better quality)
        '-'                             # Output to stdout
    ]
    pipe = None
    buffer = b''
    try:
        pipe = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        while True:
            # Read data from the pipe.
            # We need to read data and buffer it until a complete JPEG frame is formed.
            # A JPEG image starts with FF D8 and ends with FF D9.
            
            # Read a chunk of data.
            data_chunk = pipe.stdout.read(4096)
            if not data_chunk and not buffer: # If no data and buffer is empty, process has ended
                logging.warning("ffmpeg process ended or produced no output.")
                break
            
            buffer += data_chunk

            # Process the buffer to find complete JPEG frames.
            while True:
                # Look for the start of a JPEG image (SOI marker: FF D8)
                soi_marker_pos = buffer.find(b'\xFF\xD8')
                if soi_marker_pos == -1:
                    # No start marker found. Need more data.
                    # If no more data is coming and we have no start marker, break.
                    if not data_chunk:
                        break # Exit inner loop, will break outer loop if buffer is empty
                    else:
                        # Read more data to complete the buffer.
                        data_chunk = pipe.stdout.read(4096)
                        if not data_chunk:
                            break # No more data, exit inner loop
                        buffer += data_chunk
                        continue # Try finding SOI again with more data

                # Found a start marker. Now look for the end of the JPEG image (EOI marker: FF D9).
                eoi_marker_pos = buffer.find(b'\xFF\xD9', soi_marker_pos + 2) # Search after the SOI marker

                if eoi_marker_pos != -1:
                    # Found both SOI and EOI markers. This is a complete JPEG frame.
                    # The frame data is from the SOI marker up to and including the EOI marker.
                    frame_data = buffer[soi_marker_pos : eoi_marker_pos + 2]
                    
                    # Yield the complete frame data with multipart boundaries
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                    
                    # Remove the processed frame data from the buffer
                    buffer = buffer[eoi_marker_pos + 2:]
                    # Continue inner loop to process the rest of the buffer
                else:
                    # Found SOI but no EOI. This means the current frame is incomplete.
                    # We need more data.
                    # If no more data is coming, this might be an incomplete frame at the end.
                    if not data_chunk:
                        # No more data, and frame is incomplete. Log a warning and break.
                        logging.warning("Incomplete JPEG frame at end of stream.")
                        break # Exit inner loop
                    else:
                        # More data is expected, so break inner loop and read more data.
                        break # Exit inner loop, read more data in outer loop

    except Exception as e:
        logging.error(f"Error during ffmpeg streaming: {e}")
    finally:
        # Ensure the ffmpeg process is terminated if it's still running
        if pipe and pipe.poll() is None:
            pipe.terminate()
            pipe.wait()
            logging.info("ffmpeg process terminated.")


@app.route('/video_feed')
def video_feed():
    """Route for video stream using ffmpeg"""
    logging.info(f"Client connected to video feed (ffmpeg)")

    # Handle HEAD requests: return headers only, no content
    if request.method == 'HEAD':
        # Return 204 No Content status, which is appropriate for HEAD requests
        # where the resource doesn't have a body to return.
        # We also need to return the correct Content-Type header.
        return Response(status=204, mimetype='multipart/x-mixed-replace; boundary=frame')

    # Note: FFmpeg handles looping and frame rate control, so no explicit re-initialization needed here
    # unless ffmpeg process itself fails.
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    # Simplified index page for the ffmpeg stream
    return '''
    <html>
      <head>
        <title>Video Stream Player (FFmpeg)</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
          .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
          h2 { color: #333; text-align: center; }
          .status { background: #e8f5e8; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
          img { display: block; margin: 0 auto; border: 2px solid #ddd; border-radius: 5px; }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>▶️ Video Stream Player (FFmpeg)</h2>
          <div class="status">
            <strong>Status:</strong> Ready to stream<br>
            <strong>Source:</strong> Video file playback via FFmpeg<br>
            <strong>Protocol:</strong> MJPEG over HTTP
          </div>
          <img src="/video_feed" width="640" alt="Video stream" />
        </div>
      </body>
    </html>
    '''

if __name__ == '__main__':
    logging.info("Starting Flask server with FFmpeg streaming...")
    # Use threaded=True for concurrent requests if needed, though ffmpeg might be a bottleneck
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8089)), threaded=True)
