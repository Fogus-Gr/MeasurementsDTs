#!/usr/bin/env python3
"""
Direct H.264 Streaming Server
=============================

A simple and reliable HTTP-based video streaming server that serves H.264 video
to clients like VLC Media Player and FFplay.

WHY THIS APPROACH:
- RTSP is complex (RTP packets, timing, multi-protocol coordination)
- HTTP streaming is simple and reliable
- FFmpeg handles all encoding complexities
- Works with all media players

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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class H264StreamHandler(BaseHTTPRequestHandler):
    """HTTP handler for H.264 streaming"""
    
    def __init__(self, *args, video_path=None, **kwargs):
        self.video_path = video_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for H.264 stream"""
        if self.path == '/stream.h264':
            logger.info(f"Client requesting H.264 stream from {self.client_address}")
            
            if not self.video_path or not os.path.exists(self.video_path):
                logger.error(f"Video file not found: {self.video_path}")
                self.send_error(404, "Video file not found")
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'video/h264')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'close')
            self.end_headers()
            
            logger.info(f"Streaming video: {self.video_path}")
            
            try:
                # Use FFmpeg to convert and stream
                cmd = [
                    'ffmpeg',
                    '-re',
                    '-i', self.video_path,
                    '-c:v', 'copy',
                    '-c:a', 'copy',  # Include audio streams if available
                    # If you want to re-encode, use the following line instead:
                    # '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-tune', 'zerolatency',
                    '-f', 'mpegts',  # CHANGE THIS LINE FROM 'h264' to 'mpegts'
                    '-'
                ]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
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
                
            except Exception as e:
                logger.error(f"Error streaming H.264: {e}")
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
    print("It's simpler than RTSP and should work with VLC/FFplay")
    print()
    
    # Start server
    server = DirectStreamServer(port=args.port, video_path=video_path)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

