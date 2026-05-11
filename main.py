import os
import sys
import cv2
import time

cv2.setNumThreads(1)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from movenet_hpe import MoveNetHPE
from openvino_base_hpe import OpenVINOBaseHPE
from alphapose_hpe import AlphaPoseHPE
from utils.video_detection import detect_video_properties
import logging

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hpe_processing.log'),
        logging.StreamHandler()  # Also log to console
    ]
)

# Create structured logger for machine-readable data
import json
import csv
from datetime import datetime

def log_structured_data(event_type, data, log_file='hpe_structured.log'):
    """Log structured data for easy parsing"""
    timestamp = datetime.now().isoformat()
    entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'data': data
    }
    
    # Write to JSONL file (one JSON object per line)
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')

class _HideAspectWarn(logging.Filter):
    def filter(self, rec):
        msg = rec.getMessage()
        return "Chosen model aspect ratio doesn't match image aspect ratio" not in msg

logging.getLogger().addFilter(_HideAspectWarn())

def main():
    parser = parse_arguments()
    args = parser.parse_args()
    
    # Log session start
    log_structured_data('session_start', {
        'method': args.method,
        'input': args.input,
        'device': args.device,
        'timeout': args.timeout,
        'max_frames': args.max_frames
    })

    hpe = get_hpe_method(args)
    
    hpe.load_model()

    is_url_stream = args.input.startswith('http') or args.input.startswith('rtsp://')

    # Add timeout and frame count detection for HTTP/RTSP streams and video files
    if is_url_stream:
        logging.info(f"URL stream detected: {args.input}")
        logging.info("Auto-detecting video properties...")
        
        # Auto-detect video properties (includes FPS conversion for HTTP streams)
        fps, duration, total_frames = detect_video_properties(args.input)
        
        # Handle detection failure
        if fps is None or duration is None or total_frames is None:
            logging.warning("Video property detection failed - using user-provided timeout and max_frames")
            logging.warning("Processing will be controlled by --timeout and --max_frames arguments")
            
            # Log that detection failed
            log_structured_data('video_properties_detection_failed', {
                'input_url': args.input,
                'reason': 'Could not detect video properties',
                'fallback': 'Using user-provided timeout and max_frames'
            })
        else:
            # Log video properties (may include converted frame count for HTTP streams)
            logging.info(f"Detected video properties: {fps:.2f} FPS, {duration:.1f}s duration, {total_frames} frames")
            if args.input.startswith('http'):
                logging.info("Note: Frame count may be converted from original video FPS to streamer target FPS (25)")
            
            log_structured_data('video_properties_detected', {
                'fps': fps,
                'duration': duration,
                'total_frames': total_frames,
                'input_url': args.input,
                'is_http_stream': args.input.startswith('http')
            })
        
        # Auto-set timeout and max_frames based on detected properties (only if detection succeeded)
        logging.info(f"Current timeout: {args.timeout}, max_frames: {args.max_frames}")
        
        original_timeout = args.timeout
        original_max_frames = args.max_frames
        
        if fps is not None and duration is not None and total_frames is not None:
            # We have valid detected properties, can do auto-setting
            if args.timeout == 0:  # Default timeout (unset) - keep unlimited
                logging.info(f"Timeout set to unlimited (0) - processing will continue until max_frames or manual stop")
            else:
                logging.info(f"Using provided timeout: {args.timeout}s")
            
            if args.max_frames == 0:  # No limit set
                args.max_frames = total_frames
                if args.input.startswith('http'):
                    logging.info(f"Auto-set max_frames: {args.max_frames} (converted for streamer FPS)")
                else:
                    logging.info(f"Auto-set max_frames: {args.max_frames}")
            else:
                logging.info(f"Using provided max_frames: {args.max_frames}")
            
            # Log configuration changes
            log_structured_data('configuration_applied', {
                'original_timeout': original_timeout,
                'final_timeout': args.timeout,
                'original_max_frames': original_max_frames,
                'final_max_frames': args.max_frames,
                'auto_set_timeout': False,  # Timeout stays unlimited (0)
                'auto_set_max_frames': original_max_frames == 0,
                'detection_successful': True,
                'is_http_stream': args.input.startswith('http'),
                'fps_conversion_applied': args.input.startswith('http') and original_max_frames == 0
            })
        else:
            # Detection failed, use user-provided values
            logging.info(f"Using provided timeout: {args.timeout}s")
            logging.info(f"Using provided max_frames: {args.max_frames}")
            
            # Log that no auto-setting was done
            log_structured_data('configuration_applied', {
                'original_timeout': original_timeout,
                'final_timeout': args.timeout,
                'original_max_frames': original_max_frames,
                'final_max_frames': args.max_frames,
                'auto_set_timeout': False,
                'auto_set_max_frames': False,
                'detection_successful': False
            })
        
        hpe.main_loop_with_timeout(args.timeout, args.max_frames)
    elif args.input.isdigit() or args.input == '0':
        logging.info(f"Webcam detected: {args.input}")
        logging.info("Processing webcam feed (press Ctrl+C to stop)...")
        log_structured_data('processing_start', {
            'input_type': 'webcam',
            'input_source': args.input,
            'timeout': None,
            'max_frames': None
        })
        hpe.main_loop()
    else:
        logging.info(f"Video file detected: {args.input}")
        if args.timeout > 0:
            logging.info(f"Processing video with timeout: {args.timeout}s")
            log_structured_data('processing_start', {
                'input_type': 'video_file',
                'input_source': args.input,
                'timeout': args.timeout,
                'max_frames': args.max_frames
            })
            hpe.main_loop_with_timeout(args.timeout, args.max_frames)
        else:
            logging.info("Processing complete video without timeout...")
            log_structured_data('processing_start', {
                'input_type': 'video_file',
                'input_source': args.input,
                'timeout': None,
                'max_frames': None
            })
            hpe.main_loop()
    
    # Log session end
    log_structured_data('session_end', {
        'method': args.method,
        'input': args.input,
        'device': args.device
    })

def parse_arguments():
        parser = argparse.ArgumentParser()
        parser.add_argument('--method', type=str, required=True, choices=['openpose', 'alphapose', 'movenet', 'hrnet', 'ae1', 'ae2', 'ae3'])
        parser.add_argument('--input', type=str, default='0', help="Path to video or image file to use as input (default=%(default)s)")
        parser.add_argument("--output_dir", type=str, help="Path to directory where output files will be saved")          
        parser.add_argument("--json", action="store_true", help="Enable export keypoints to a single json file")
        parser.add_argument("--csv", action="store_true", help="Enable export keypoints to a single csv file")
        parser.add_argument("--measurement_interval_ms", type=int, default=100, help="Interval in ms for measuring transmitted data volume per interval")
        parser.add_argument("--save_video", action="store_true", help="Save resutls into a video file")
        parser.add_argument("--save_image", action="store_true", help="Save image with keypoints")
        parser.add_argument('--device', type=str, default="GPU", choices=['GPU', 'CPU'], help="Device to run inference on. Options: CPU, GPU")
        parser.add_argument('--detbatch', type=int, default=5, help="Detection batch size (default=%(default)s)")
        parser.add_argument('--timeout', type=int, default=0, help="Timeout in seconds for processing (0=unlimited, default=%(default)s)")
        parser.add_argument('--max_frames', type=int, default=0, help="Maximum number of frames to process (0=unlimited)")
        
        return parser

def get_hpe_method(args):
    method_map = {
        'movenet': lambda args: MoveNetHPE(device=args.device, **base_args(args)),
        'alphapose': lambda args: AlphaPoseHPE(device=args.device, detbatch=args.detbatch, **base_args(args)),
        'openpose': lambda args: OpenVINOBaseHPE(model_type='openpose', device=args.device, **base_args(args)),
        'hrnet': lambda args: OpenVINOBaseHPE(model_type='higherhrnet', device=args.device, **base_args(args)),
        'ae1': lambda args: OpenVINOBaseHPE(model_type='efficienthrnet1', device=args.device, **base_args(args)),
        'ae2': lambda args: OpenVINOBaseHPE(model_type='efficienthrnet2', device=args.device, **base_args(args)),
        'ae3': lambda args: OpenVINOBaseHPE(model_type='efficienthrnet3', device=args.device, **base_args(args)),
    }

    name = args.method.lower()

    if name not in method_map:
        raise ValueError(f"Unknown method: {name}")

    if callable(method_map[name]):
        return method_map[name](args)
    else:
        return method_map[name](**base_args(args))

def base_args(args):
    return {
        "input_src": args.input,
        "output_dir": args.output_dir,
        "enable_json": args.json,
        "enable_csv": args.csv,
        "measurement_interval_ms": args.measurement_interval_ms,
        "save_image": args.save_image,
        "save_video": args.save_video
    }


if __name__ == "__main__":
    main()
