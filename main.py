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
import logging
from tqdm import tqdm
from utils.video_detection import detect_video_properties

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('hpe_processing.log')  # File output
    ]
)

# Create logger
logger = logging.getLogger(__name__)

class _HideAspectWarn(logging.Filter):
    def filter(self, rec):
        msg = rec.getMessage()
        return "Chosen model aspect ratio doesn't match image aspect ratio" not in msg

logging.getLogger().addFilter(_HideAspectWarn())


def main():
    parser = parse_arguments()
    args = parser.parse_args()

    hpe = get_hpe_method(args)
    hpe.load_model()
    
    # Auto-detect video properties for HTTP streams
    if args.input.startswith('http'):
        logging.info(f"HTTP stream detected: {args.input}")
        
        # Check if user provided override values
        if args.video_duration > 0 or args.video_fps > 0:
            logging.info("Using user-provided video properties...")
            fps = args.video_fps if args.video_fps > 0 else 25.0
            duration = args.video_duration if args.video_duration > 0 else 300.0
            total_frames = int(duration * fps)
            logging.info(f"User-provided video properties:")
            logging.info(f"  FPS: {fps:.2f}")
            logging.info(f"  Duration: {duration:.1f}s")
            logging.info(f"  Total frames: {total_frames}")
        else:
            logging.info("Auto-detecting video properties...")
            # Detect video properties
            fps, duration, total_frames = detect_video_properties(args.input)
        
        # Auto-set timeout and max_frames if not provided
        if args.timeout == 0:  # Default timeout
            # Calculate timeout based on processing speed (assume 2-3 FPS for HRNet)
            estimated_processing_time = total_frames / 2.5  # Conservative estimate
            args.timeout = int(estimated_processing_time) + 60  # Add 60s buffer
            logging.info(f"Auto-set timeout: {args.timeout}s (estimated processing time: {estimated_processing_time:.1f}s)")
        
        if args.max_frames == 0:  # Default max_frames
            args.max_frames = total_frames
            logging.info(f"Auto-set max_frames: {args.max_frames}")
        
        logging.info("Adding real-time processing with auto-detection...")
        hpe.main_loop_realtime(args.timeout, args.max_frames, fps, duration, total_frames)
    elif args.input.isdigit() or args.input == '0':
        logging.info(f"Webcam detected: {args.input}")
        logging.info("Processing webcam feed (press Ctrl+C to stop)...")
        hpe.main_loop()
    else:
        logging.info(f"Video file detected: {args.input}")
        logging.info("Processing complete video without timeout...")
        hpe.main_loop()

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
        parser.add_argument('--timeout', type=int, default=0, help="Timeout in seconds for HTTP streams (default=%(default)s, auto-detected if HTTP)")
        parser.add_argument('--max_frames', type=int, default=0, help="Maximum number of frames to process (default=%(default)s, auto-detected if HTTP)")
        parser.add_argument('--video_duration', type=float, default=0, help="Video duration in seconds (overrides auto-detection)")
        parser.add_argument('--video_fps', type=float, default=0, help="Video FPS (overrides auto-detection)")
        
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
