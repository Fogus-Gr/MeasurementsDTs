import cv2
import subprocess
import json
import logging
import os
import requests

def get_streamer_video_info(streamer_url):
    """
    Query the streamer's /video_info endpoint to get converted video properties.
    
    Args:
        streamer_url: Base URL of the streamer (e.g., 'http://127.0.0.1:8089')
        
    Returns:
        dict: Video conversion info or None if failed
    """
    try:
        # Construct the video_info endpoint URL
        video_info_url = f"{streamer_url.rstrip('/')}/video_info"
        logging.info(f"Querying streamer video info from: {video_info_url}")
        
        # Make request with timeout
        response = requests.get(video_info_url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        logging.info("Successfully retrieved video conversion info from streamer:")
        logging.info(f"  Original: {data['original_frames']} frames @ {data['original_fps']:.2f} FPS")
        logging.info(f"  Duration: {data['duration']:.2f}s")
        logging.info(f"  Converted: {data['converted_frames']} frames @ {data['target_fps']} FPS")
        
        return data
        
    except requests.exceptions.RequestException as e:
        logging.info(f"Could not query streamer video info: {e}")
        return None
    except Exception as e:
        logging.info(f"Error parsing streamer video info: {e}")
        return None

def detect_video_properties(input_url):
    """
    Detect video properties (FPS, duration, total frames) from various input sources.
    
    Args:
        input_url: URL or path to video source
        
    Returns:
        tuple: (fps, duration, total_frames)
    """
    logging.info(f"Auto-detecting video properties from: {input_url}")
    
    # For HTTP streams, try to get properties from the streamer's video_info endpoint first
    if input_url.startswith('http'):
        # First, try to get converted properties from the streamer's API
        # This gives us the exact frame count after FPS conversion
        streamer_info = get_streamer_video_info(input_url)
        if streamer_info:
            # Use the converted properties from the streamer
            fps = streamer_info['target_fps']  # Use the target FPS (25)
            duration = streamer_info['duration']  # Duration stays the same
            frame_count = streamer_info['converted_frames']  # Use converted frame count
            
            logging.info("Using video properties from streamer (with FPS conversion):")
            logging.info(f"  Target FPS: {fps:.2f}")
            logging.info(f"  Duration: {duration:.1f}s")
            logging.info(f"  Converted frames: {frame_count}")
            return fps, duration, frame_count
        
        # Fallback: try to get properties from the original video file that the streamer is using
        try:
            # Get the video path from environment
            video_path = os.environ.get("VIDEO_PATH")
            if not video_path:
                logging.info("VIDEO_PATH environment variable not set - skipping source video detection")
                raise FileNotFoundError("VIDEO_PATH not set")
            
            # Use ffprobe on the original video file (same as app_ffmpeg.py does)
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Find video stream
                video_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break
                
                if video_stream:
                    # Get FPS
                    fps_str = video_stream.get('r_frame_rate', '25/1')
                    if '/' in fps_str:
                        num, den = map(int, fps_str.split('/'))
                        original_fps = num / den
                    else:
                        original_fps = float(fps_str)
                    
                    # Get duration
                    duration = float(data.get('format', {}).get('duration', 0))
                    
                    # Get original frame count
                    original_frame_count = int(video_stream.get('nb_frames', 0))
                    
                    if duration > 0 and original_frame_count > 0:
                        # Calculate converted frame count for 25 FPS (streamer target)
                        target_fps = 25
                        converted_frame_count = int(duration * target_fps)
                        
                        logging.info("Auto-detected video properties from streamer's source video:")
                        logging.info(f"  Original: {original_frame_count} frames @ {original_fps:.2f} FPS")
                        logging.info(f"  Duration: {duration:.1f}s")
                        logging.info(f"  Converted: {converted_frame_count} frames @ {target_fps} FPS")
                        return target_fps, duration, converted_frame_count
                    else:
                        logging.info("Could not get complete properties from source video, trying HTTP stream detection")
            
        except Exception as e:
            logging.info(f"Could not detect from source video: {e}")
            logging.info("Trying HTTP stream detection as fallback")
        
        # Fallback: try ffprobe on the HTTP stream itself
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', input_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Find video stream
                video_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break
                
                if video_stream:
                    # Get FPS
                    fps_str = video_stream.get('r_frame_rate', '25/1')
                    if '/' in fps_str:
                        num, den = map(int, fps_str.split('/'))
                        fps = num / den
                    else:
                        fps = float(fps_str)
                    
                    # Get duration (may be 0 for live streams)
                    duration = float(data.get('format', {}).get('duration', 0))
                    
                    # Get frame count (may be 0 for live streams)
                    frame_count = int(video_stream.get('nb_frames', 0))
                    
                    # For HTTP streams, try to get actual properties from OpenCV if ffprobe fails
                    if duration <= 0 or frame_count <= 0:
                        logging.info("HTTP stream detected - trying OpenCV to get actual video properties")
                        # Don't return yet, let OpenCV try to get real values
                    else:
                        logging.info("Auto-detected video properties from HTTP stream:")
                        logging.info(f"  FPS: {fps:.2f}")
                        logging.info(f"  Duration: {duration:.1f}s")
                        logging.info(f"  Total frames: {frame_count}")
                        return fps, duration, frame_count
                    
        except Exception as e:
            logging.info(f"ffprobe failed for HTTP stream: {e}")
            logging.info("Trying OpenCV to get actual video properties")
    
    # Fallback to OpenCV for local files or when ffprobe fails
    try:
        cap = cv2.VideoCapture(input_url)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            # For HTTP streams, if we can't get duration/frame count, it's likely a live stream
            if input_url.startswith('http'):
                if fps <= 0:
                    logging.warning("Could not detect FPS from HTTP stream - this may cause timing issues")
                    fps = 25.0  # Reasonable default for webcam streams
                if duration <= 0:
                    logging.info("HTTP stream appears to be live (no duration detected)")
                    # For live streams, we can't predict duration, so we'll use a large value
                    # The timeout will handle stopping the processing
                    duration = 3600.0  # 1 hour - will be overridden by user timeout
                if frame_count <= 0:
                    logging.info("HTTP stream appears to be live (no frame count detected)")
                    # For live streams, calculate based on duration
                    frame_count = int(duration * fps) if fps > 0 else 90000  # 1 hour at 25fps
            
            logging.info("Auto-detected video properties:")
            logging.info(f"  FPS: {fps:.2f}")
            logging.info(f"  Duration: {duration:.1f}s")
            logging.info(f"  Total frames: {frame_count}")
            
            return fps, duration, frame_count
            
    except Exception as e:
        logging.info(f"OpenCV detection failed: {e}")
    
    # Final fallback - return None to indicate detection failed
    if input_url.startswith('http'):
        logging.warning("Could not detect video properties from HTTP stream")
        logging.warning("Consider using --timeout and --max_frames arguments to control processing")
        logging.warning("Or provide a local video file for automatic property detection")
        return None, None, None  # Let the caller handle this
    else:
        logging.warning("Could not detect video properties from local file")
        logging.warning("Consider using --timeout and --max_frames arguments to control processing")
        return None, None, None  # Let the caller handle this
