"""
A test version of direct_stream_server.py with the new /status endpoint.
This is a copy for testing purposes.

Original functionality remains the same, but with the addition of a /status endpoint.
"""

import socket
import threading
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import argparse
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class H264StreamHandler(BaseHTTPRequestHandler):
    """HTTP handler for H.264 streaming with status endpoint"""
    
    def __init__(self, *args, video_path=None, **kwargs):
        self.video_path = video_path
        self.streaming = False
        self.start_time = None
        self.stream_thread = None
        self.ffmpeg_process = None
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/status':
            self.handle_status()
        elif self.path == '/stream.h264':
            self.handle_stream()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def handle_status(self):
        """Handle status endpoint"""
        import time
        import os
        
        status = {
            'streaming': self.streaming,
            'video_file': os.path.basename(self.video_path) if self.video_path else None,
            'video_duration': self.get_video_duration() if self.video_path else None,
            'uptime_seconds': time.time() - self.start_time if self.start_time else 0,
            'timestamp': time.time(),
            'status': 'streaming' if self.streaming else 'idle'
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        import json
        self.wfile.write(json.dumps(status, indent=2).encode('utf-8'))
    
    def get_video_duration(self):
        """Get video duration in seconds using ffprobe"""
        try:
            import subprocess
            import json
            
            cmd = [
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                self.video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
        return None
    
    def handle_stream(self):
        """Handle video streaming"""
        if not self.video_path or not os.path.exists(self.video_path):
            self.send_error(404, "Video file not found")
            return
            
        self.streaming = True
        self.start_time = time.time()
        
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'video/H264')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close')
            self.end_headers()
            
            # Start FFmpeg process
            cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-c:v', 'libx264',
                '-f', 'h264',
                'pipe:1'
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            
            # Stream the output
            while True:
                chunk = self.ffmpeg_process.stdout.read(1024 * 16)  # 16KB chunks
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except (ConnectionResetError, BrokenPipeError):
                    logger.info("Client disconnected")
                    break
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}")
        finally:
            self.streaming = False
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
            logger.info("Stream ended")

def run_server(host='0.0.0.0', port=8089, video_path=None):
    """Run the HTTP server with the specified parameters"""
    class Handler(H264StreamHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, video_path=video_path, **kwargs)
    
    server_address = (host, port)
    httpd = HTTPServer(server_address, Handler)
    
    logger.info(f"Starting server on http://{host}:{port}")
    if video_path:
        logger.info(f"Serving video: {video_path}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
    finally:
        httpd.server_close()
        logger.info("Server stopped.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='H.264 HTTP Stream Server')
    parser.add_argument('--video', type=str, help='Path to video file')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8089, help='Port to listen on (default: 8089)')
    
    args = parser.parse_args()
    
    if not args.video:
        parser.print_help()
        sys.exit(1)
    
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        sys.exit(1)
    
    run_server(host=args.host, port=args.port, video_path=str(video_path))
