#!/usr/bin/env python3
"""
Direct H.264 Streaming Server
=============================

A simple and reliable HTTP-based video streaming server that serves H264 video
to clients like VLC Media Player and FFplay.

USAGE:
1. Run: python direct_stream_server.py --video "path/to/video.mp4"
2. Open VLC: http://localhost:8089  /stream.h264
3. Or use FFplay: ffplay http://localhost:8089/stream.h264

EXAMPLES:
  # Windows
  python direct_stream_server.py --video "C:\\Users\\theo\\Downloads\\video.mp4"
  
  # Linux/macOS
  python direct_stream_server.py --video "/home/user/video.mp4"
  
  # Custom port
  python direct_stream_server.py --video "video.mp4" --port 9090

This solution was created after discovering that emulating and IP camera from a video 
file using opencv implementing RTSP from scratch has too many complexities and 
cpu usage utilization for a simple streaming use case.
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
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class H264StreamHandler(BaseHTTPRequestHandler):
    """HTTP handler for H264 streaming"""
    
    def __init__(self, *args, video_path=None, **kwargs):
        self.video_path = video_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for H264 stream"""
        logger.info(f"New connection from {self.client_address[0]}:{self.client_address[1]}")
        logger.info(f"Request path: {self.path}")
        logger.info(f"User agent: {self.headers.get('User-Agent', 'Unknown')}")
        if self.path == '/stream.h264':
            logger.info(f"Client requesting H264 stream from {self.client_address}")
            
            if not self.video_path or not os.path.exists(self.video_path):
                logger.error(f"Video file not found: {self.video_path}")
                self.send_error(404, "Video file not found")
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')  # Use 'video/MP2T' for MPEG_TS format
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close')
            self.end_headers()
            
            logger.info(f"Streaming video: {self.video_path}")
            
            try:
                # Use FFmpeg to convert and stream
                # Old command (no re-encoding, high bitrate):
                cmd = [
                    'ffmpeg',
                    '-re',
                    '-i', self.video_path,
                    '-c:v', 'copy',  # or libx264 if re-encoding is needed
                    '-f', 'mpegts',
                    '-'
                ]
                # New command: re-encode to H.264 at 4 Mbps for realistic IP camera emulation
                # cmd = [
                #     'ffmpeg',
                #     '-re',
                #     '-i', self.video_path,
                #     '-c:v', 'libx264',
                #     '-b:v', '4M',  # 4 Mbps bitrate
                #     '-preset', 'veryfast',
                #     '-tune', 'zerolatency',
                #     '-f', 'mpegts',
                #     '-'
                # ]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ffmpeg_stderr = []
                while True:
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    try:
                        self.wfile.write(data)
                        self.wfile.flush()
                    except BrokenPipeError:
                        break
                        
                process.terminate()
                process.wait()
                # Log FFmpeg stderr output for debugging
                ffmpeg_stderr = process.stderr.read().decode(errors='replace')
                if process.returncode != 0:
                    logger.error(f"FFmpeg exited with code {process.returncode}. Stderr: {ffmpeg_stderr}")
                else:
                    logger.info("FFmpeg finished streaming successfully.")
                
            except Exception as e:
                logger.error(f"Error streaming H264: {e}")
        else:
            self.send_error(404)
    
    def do_HEAD(self):
        """Handle HEAD requests for H264 stream (for OpenCV/FFmpeg probing)"""
        logger.info(f"HEAD request from {self.client_address[0]}:{self.client_address[1]}")
        logger.info(f"Request path: {self.path}")
        if self.path == '/stream.h264':
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close')
            self.end_headers()
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.client_address[0]} - {format % args}")

class DirectStreamServer:
    def __init__(self, port=8089, video_path=None):
        self.port = port
        self.video_path = video_path
        self.server = None
        
    def create_handler(self):
        """Create handler class with video path"""
        video_path = self.video_path
        
        class Handler(H264StreamHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, video_path=video_path, **kwargs)
        
        return Handler
        
    def start(self):
        """Start the HTTP streaming server"""
        try:
            # Validate video file
            if not self.video_path:
                logger.error("No video file specified. Use --video argument.")
                return
                
            if not os.path.exists(self.video_path):
                logger.error(f"Video file not found: {self.video_path}")
                return
            
            handler_class = self.create_handler()
            self.server = HTTPServer(('0.0.0.0', self.port), handler_class)
            
            logger.info(f"Direct H.264 streaming server started on port {self.port}")
            logger.info(f"Video file: {self.video_path}")
            logger.info(f"Test with VLC: http://localhost:{self.port}/stream.h264")
            logger.info(f"Test with FFplay: ffplay http://localhost:{self.port}/stream.h264")
            logger.info("Press Ctrl+C to stop")
            
            self.server.serve_forever()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        if self.server:
            self.server.shutdown()
            logger.info("Direct streaming server stopped")

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Direct H.264 Streaming Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows
  python direct_stream_server.py --video "C:\\path\\to\\video.mp4"
  
  # Linux/macOS  
  python direct_stream_server.py --video "/path/to/video.mp4"
  
  # With custom port
  python direct_stream_server.py --video "video.mp4" --port 9090
        """
    )
    
    parser.add_argument(
        '--video', '-v',
        type=str,
        required=True,
        help='Path to the video file to stream (required)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8089,
        help='Port number for the HTTP server (default: 8089)'
    )
    
    return parser.parse_args()

def validate_video_path(video_path):
    """Validate and normalize video path for cross-platform compatibility"""
    try:
        # Convert to Path object for cross-platform handling
        path = Path(video_path)
        
        # Resolve to absolute path
        abs_path = path.resolve()
        
        # Check if file exists
        if not abs_path.exists():
            logger.error(f"Video file not found: {abs_path}")
            return None
            
        # Check if it's a file (not directory)
        if not abs_path.is_file():
            logger.error(f"Path is not a file: {abs_path}")
            return None
            
        logger.info(f"Video file validated: {abs_path}")
        return str(abs_path)
        
    except Exception as e:
        logger.error(f"Error validating video path: {e}")
        return None

def main():
    """Main function"""
    print("=" * 60)
    print("Direct H.264 Streaming Server")
    print("=" * 60)
    print()
    # Parse command-line arguments
    try:
        args = parse_arguments()
    except SystemExit:
        return
    # Validate video path
    video_path = validate_video_path(args.video)
    if not video_path:
        logger.error("Invalid video file. Exiting.")
        sys.exit(1)
    print(f"Video file: {video_path}")
    print(f"Server port: {args.port}")
    print("This server streams your video directly via HTTP")
    print()
    # Start server
    server = DirectStreamServer(port=args.port, video_path=video_path)
    def stop_server(signum, frame):
        logger.info("Received SIGTERM, stopping server...")
        server.stop()
    signal.signal(signal.SIGTERM, stop_server)
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
