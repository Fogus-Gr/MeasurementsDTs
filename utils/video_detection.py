import subprocess
import json
import cv2
import logging

def detect_video_properties(input_url):
    """Auto-detect video properties from HTTP stream or video file"""
    try:
        logging.info(f"Auto-detecting video properties from: {input_url}")
        
        # Use ffprobe to get video properties
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
                fps_str = video_stream.get('r_frame_rate', '29.97/1')
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    fps = num / den
                else:
                    fps = float(fps_str)
                
                # Get duration
                duration = float(data.get('format', {}).get('duration', 0))
                
                # Get frame count
                frame_count = int(video_stream.get('nb_frames', 0))
                if frame_count == 0 and duration > 0:
                    frame_count = int(duration * fps)
                
                # Validate the detected values
                if fps <= 0 or fps > 120:
                    logging.warning(f"Invalid FPS detected: {fps}, using default 25.0")
                    fps = 25.0
                
                if duration <= 0 or duration > 3600:  # Max 1 hour
                    logging.warning(f"Invalid duration detected: {duration}, using default 307s")
                    duration = 307.0
                
                if frame_count <= 0 or frame_count > 1000000:  # Max 1M frames
                    logging.warning(f"Invalid frame count detected: {frame_count}, calculating from duration")
                    frame_count = int(duration * fps)
                
                logging.info(f"Auto-detected video properties:")
                logging.info(f"  FPS: {fps:.2f}")
                logging.info(f"  Duration: {duration:.1f}s")
                logging.info(f"  Total frames: {frame_count}")
                
                return fps, duration, frame_count
        
        # For HTTP streams, try to get basic info from OpenCV
        if input_url.startswith('http'):
            logging.info("HTTP stream detected - attempting OpenCV-based detection...")
            try:
                cap = cv2.VideoCapture(input_url)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    
                    if fps > 0:
                        logging.info(f"OpenCV detected FPS: {fps:.2f}")
                        
                        # Calculate duration from frame count and FPS
                        if frame_count > 0:
                            duration = frame_count / fps
                            logging.info(f"OpenCV detected duration: {duration:.1f}s from {frame_count} frames")
                        else:
                            # Use default duration for HTTP streams
                            duration = 307.0
                            frame_count = int(duration * fps)
                            logging.info(f"Using default duration: {duration:.1f}s")
                        
                        cap.release()
                        return fps, duration, frame_count
                cap.release()
            except Exception as e:
                logging.warning(f"OpenCV detection failed: {e}")
        
        # Fallback to default values
        logging.warning("Could not auto-detect video properties - using defaults")
        return 25.0, 307.0, 7675  # 307s * 25 FPS = 7675 frames
        
    except Exception as e:
        logging.error(f"Error auto-detecting video properties: {e}")
        logging.warning("Using default video properties")
        return 25.0, 307.0, 7675  # 307s * 25 FPS = 7675 frames
