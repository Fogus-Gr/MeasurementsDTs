from abc import ABC, abstractmethod
import cv2
import os
from collections import namedtuple, deque # Added deque import
import glob
import time
import torch
import numpy as np
import logging
import requests
import re
import json

try:
    import PyNvCodec as nvc
except ImportError:
    nvc = None
    print("[WARNING] PyNvCodec not found. Hardware accelerated video decoding will not be available.")

from utils.visualizer import render
from utils.evaluator import append_COCO_format_json, append_COCO_format_csv, save_COCO_format_json, save_COCO_format_csv, save_Tx_csv_data
import json
from datetime import datetime

class Body:
    def __init__(self, score, xmin, ymin, xmax, ymax, keypoints_score, keypoints, keypoints_norm):
        self.score = score # global/mean score 
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.keypoints_score = keypoints_score # individual scores of the keypoints
        self.keypoints_norm = keypoints_norm # keypoints normalized ([0,1]) coordinates (x,y) in the input image
        self.keypoints = keypoints # keypoints coordinates (x,y) in pixels in the input image

# Padding (all values are in pixel) :
# w (resp. h): horizontal (resp. vertical) padding on the source image to make its ratio same as Movenet model input. 
#               The padding is done on one side (bottom or right) of the image.
# padded_w (resp. padded_h): width (resp. height) of the image after padding
Padding = namedtuple('Padding', ['w', 'h', 'padded_w',  'padded_h'])

def extract_x_metadata(header_region):
    match = re.search(b'X-Metadata: (.+?)\r\n', header_region)

    if match:
        metadata_json = match.group(1)
        metadata = json.loads(metadata_json.decode())
        frame_number = metadata.get('frame_number')
        server_timestamp = metadata.get("server_timestamp")
        elapsed_time = metadata.get("elapsed_time")
    else:
        frame_number = None
        server_timestamp = None
        elapsed_time = None

    return frame_number

class BaseHPE(ABC):
    input_type = None
    output_dir = ""

    def __init__(self, input_src=None,
                output_dir=None,
                enable_json=False,
                enable_csv=False,
                measurement_interval_ms=100,
                save_image=False,
                save_video=False,
                score_thresh=0.2,
                show_scores = True,
                show_bounding_box = True,
                pd_w = 256,
                pd_h = 256,
                gpu_id = 0): # Added gpu_id parameter
        super().__init__()

        self.gpu_id = gpu_id
        self.demuxer = None
        self.decoder = None
        self.to_rgb_converter = None
        self.to_tensor_converter = None
        self.cap = None # Keep for non-PyNvCodec paths or fallback
        self.is_pynvcodec_enabled = False

        self.json = enable_json
        self.csv = enable_csv
        self.measurement_interval_ms = measurement_interval_ms
        self.save_image = save_image
        self.save_video = save_video
        self.score_thresh = score_thresh
        self.show_scores = show_scores
        self.show_bounding_box = show_bounding_box
        
        self.img_w = 0
        self.img_h = 0
        self.pd_w = pd_w
        self.pd_h = pd_h
        self.current_image_file = ""

        self.start_time_of_experiment = time.time()
        self.input_file = os.path.basename(os.path.normpath(input_src))

        if self.json or self.csv or self.save_image or self.save_video:
            if output_dir is not None:
                self.output_dir = output_dir
            else:
                self.output_dir = "out/"

            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

        if os.path.isdir(input_src):
            self.input_type = "directory"
            self.img_dir = input_src
            self.video_fps = 25
        elif input_src:
            if input_src.startswith("http"): # Check for HTTP first
                self.input_type = "video" # Treat HTTP as video stream
                if nvc is None:
                    print("[ERROR] PyNvCodec not available. Falling back to OpenCV for video decoding.")
                    if hasattr(self, '_init_opencv_video_capture'):
                        self._init_opencv_video_capture(input_src)
                    else:
                        raise NotImplementedError(f"Video input ({input_src}) is not supported by this HPE implementation.")
                else:
                    if hasattr(self, '_init_pynvcodec_video_capture'):
                        self._init_pynvcodec_video_capture(input_src)
                    else:
                        raise NotImplementedError(f"Video input ({input_src}) is not supported by this HPE implementation.")
            elif input_src.endswith('.mp4') or input_src.endswith('.avi') or input_src.endswith('.mov'): # Check for video files
                self.input_type = "video"
                if nvc is None:
                    print("[ERROR] PyNvCodec not available. Falling back to OpenCV for video decoding.")
                    if hasattr(self, '_init_opencv_video_capture'):
                        self._init_opencv_video_capture(input_src)
                    else:
                        raise NotImplementedError(f"Video input ({input_src}) is not supported by this HPE implementation.")
                else:
                    if hasattr(self, '_init_pynvcodec_video_capture'):
                        self._init_pynvcodec_video_capture(input_src)
                    else:
                        raise NotImplementedError(f"Video input ({input_src}) is not supported by this HPE implementation.")
            elif input_src.endswith('.jpg') or input_src.endswith('.png'):
                self.input_type = "image"
                self.img = cv2.imread(input_src)
                self.img_h, self.img_w = self.img.shape[:2]
                self.current_image_file = os.path.basename(input_src)
            elif input_src.isdigit(): # Check for webcam last
                self.input_type = "webcam"
                if hasattr(self, '_init_opencv_video_capture'):
                    self._init_opencv_video_capture(int(input_src))
                else:
                    print(f"[WARNING] Webcam input ({input_src}) is not supported by this HPE implementation.")
            else:
                raise ValueError("No valid input source provided or unsupported file type for PyNvCodec.")
                
            self.set_padding()
        else:
            raise ValueError("No valid input source provided")
            
        self.input_src = input_src  

        # Initialize processing time tracking
        self.processing_times = deque()
        self.max_processing_times_len = 200
        
        # Placeholder keys for model outputs (should be defined in subclasses)
        self.pafs_output_key = "pafs" 
        self.heatmaps_output_key = "heatmaps"

        if (self.input_type == "directory" or self.input_type == "image") and self.save_video:
            raise ValueError("Image input - video output not supported!")

        if self.save_video:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            filename = os.path.join(self.output_dir, "video.avi")
            self.output = cv2.VideoWriter(filename, fourcc, self.video_fps, (self.img_w, self.img_h))


    @abstractmethod
    def load_model(self):
        pass
    
    def _init_opencv_video_capture(self, input_src):
        """Initialize OpenCV video capture for video files and streams"""
        print(f"Initializing OpenCV video capture for: {input_src}")
        
        # Use FFmpeg backend for HTTP streams for better reliability
        if isinstance(input_src, str) and input_src.startswith("http"):
            print(f"Using FFmpeg backend for HTTP stream: {input_src}")
            self.cap = cv2.VideoCapture(input_src, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency for real-time streams
        else:
            self.cap = cv2.VideoCapture(input_src)
        
        if not self.cap.isOpened():
            print(f"[ERROR] Could not open video source: {input_src}")
            self.cap = None
            return False
        
        # Get video properties
        self.video_fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 25
        self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"Video properties: {self.img_w}x{self.img_h} @ {self.video_fps}fps, {total_frames} frames")
        return True
    
    def main_loop(self):
        # Load model if not already loaded
        if not hasattr(self, 'model') or self.model is None:
            print("Loading model...")
            self.load_model()
            print("Model loaded successfully!")

        frame_number = 0

        if self.input_type == "image":
            self.process_frame(self.img, frame_number)

        elif self.input_type == "directory":
            # Get all image files from the directory
            image_files = glob.glob(os.path.join(self.img_dir, '*.[pjg][np][ge]*'))
            print(f"Found {len(image_files)} images in {self.img_dir}")

            # Sort files to ensure they are in alphanumeric order
            image_files = sorted(image_files)
            
            total_frames = len(image_files)
            for image_file in image_files:
                print(f"Processing {frame_number+1}/{total_frames}")
                self.img = cv2.imread(image_file)
                if self.img is None:
                    print(f"Failed to load image: {image_file}")
                    continue

                self.img_h, self.img_w = self.img.shape[:2]
                self.set_padding()
                self.process_frame(self.img, frame_number)

                frame_number += 1
        
        elif self.is_pynvcodec_enabled: # PyNvCodec path
            print(f"Starting processing video/stream data with PyNvCodec on GPU {self.gpu_id}. Press CTR+C to exit")
            while True:
                try:
                    # Decode a frame
                    surface = self.decoder.DecodeSingleFrame(self.demuxer)
                    if not surface:
                        break # End of video

                    # Convert NV12 surface to RGB surface
                    rgb_surface = self.to_rgb_converter.Execute(surface)
                    
                    # Convert RGB surface to PyTorch tensor on GPU
                    frame_tensor = self.to_tensor_converter.Execute(rgb_surface)
                    
                    self.process_frame(frame_tensor, frame_number)

                    frame_number += 1
                except Exception as e:
                    print(f"[ERROR] PyNvCodec decoding error: {e}")
                    break # Exit loop on error

        else:   # OpenCV video/webcam/stream fallback
            if self.cap is None:
                print(f"[ERROR] Video capture not initialized for {self.__class__.__name__}. This HPE implementation may not support video inputs.")
                return
            print("Starting processing video/webcam data with OpenCV. Press CTR+C to exit")
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break

                self.process_frame(frame, frame_number)

                frame_number += 1


        if self.json:
            save_COCO_format_json(os.path.join(self.output_dir, "COCOformat.json"))
        if self.csv:
            save_COCO_format_csv(os.path.join(self.output_dir, f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_JSON.csv"))
            save_Tx_csv_data(os.path.join(self.output_dir, f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_Tx.csv"))

    def main_loop_with_timeout(self, timeout_seconds=0, max_frames=0):
        """Enhanced main loop with timeout and frame count detection for HTTP streams"""
        # Load model if not already loaded
        if not hasattr(self, 'model') or self.model is None:
            print("Loading model...")
            self.load_model()
            print("Model loaded successfully!")

        try: 
            frame_idx = 0
            start_time = time.time()
            
            print(f"Starting processing with timeout: {timeout_seconds}s, max_frames: {max_frames if max_frames > 0 else 'unlimited'}")

            if self.input_type == "image":
                self.process_frame(self.img, frame_idx)

            elif self.input_type == "directory":
                # Get all image files from the directory
                image_files = glob.glob(os.path.join(self.img_dir, '*.[pjg][np][ge]*'))
                print(f"Found {len(image_files)} images in {self.img_dir}")

                # Sort files to ensure they are in alphanumeric order
                image_files = sorted(image_files)

                for image_file in image_files:
                    self.img = cv2.imread(image_file)
                    if self.img is None:
                        print(f"Could not load image: {image_file}")
                        continue

                    self.process_frame(self.img, frame_idx)
                    frame_idx += 1

            elif self.is_pynvcodec_enabled: # PyNvCodec path
                print(f"Starting processing video/stream data with PyNvCodec on GPU {self.gpu_id}. Press CTR+C to exit")
                while True:
                    try:
                        # Check timeout
                        if time.time() - start_time > timeout_seconds:
                            print(f"Timeout reached ({timeout_seconds}s) - stopping processing")
                            break
                        
                        # Check max frames
                        if max_frames > 0 and frame_idx >= max_frames:
                            print(f"Max frames reached ({max_frames}) - stopping processing")
                            break
                        
                        # Decode a frame
                        surface = self.decoder.DecodeSingleFrame(self.demuxer)
                        if not surface:
                            print("End of video stream")
                            break # End of video

                        # Convert NV12 surface to RGB surface
                        rgb_surface = self.to_rgb_converter.Execute(surface)
                        
                        # Convert RGB surface to PyTorch tensor on GPU
                        frame_tensor = self.to_tensor_converter.Execute(rgb_surface)
                        
                        self.process_frame(frame_tensor, frame_idx)
                        frame_idx += 1
                        
                        # Progress update every 100 frames
                        if frame_idx % 100 == 0:
                            elapsed = time.time() - start_time
                            print(f"Processed {frame_idx} frames in {elapsed:.1f}s")
                            
                    except Exception as e:
                        print(f"[ERROR] PyNvCodec decoding error: {e}")
                        break # Exit loop on error

            else:   # video/webcam/stream fallback   
                url = self.input_src
                r = requests.get(url, stream=True)
                buffer = b""

                print("Starting processing video/webcam data from HTTP stream. Press CTRL+C to exit")

                consecutive_failures = 0
                max_consecutive_failures = 10

                for chunk in r.iter_content(chunk_size=1024):
                    buffer += chunk
                    while True:
                        # Check timeout
                        if time.time() - start_time > timeout_seconds:
                            print(f"Timeout reached ({timeout_seconds}s) - stopping processing")
                            break

                        # Check max frames
                        if max_frames > 0 and frame_idx >= max_frames:
                            print(f"Max frames reached ({max_frames}) - stopping processing")
                            break

                        soi = buffer.find(b'\xFF\xD8')
                        eoi = buffer.find(b'\xFF\xD9', soi + 2)

                        if soi != -1 and eoi != -1:
                            header_region = buffer[max(0, soi-200):soi]  # look back 200 bytes
                            frame_number = extract_x_metadata(header_region)
                            
                            frame_data = buffer[soi:eoi+2]
                            buffer = buffer[eoi+2:]

                            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                            if frame is None:
                                consecutive_failures += 1
                                print(f"Frame decode failed ({consecutive_failures}/{max_consecutive_failures})")
                                if consecutive_failures >= max_consecutive_failures:
                                    print("Too many decode failures, stopping.")
                                    break
                                else:
                                    print(f"Frame read failed ({consecutive_failures}/{max_consecutive_failures}), retrying...")
                                    time.sleep(0.1)
                                continue
                            else:
                                consecutive_failures = 0  # Reset on successful read

                            self.process_frame(frame, frame_number)
                            frame_idx += 1
                    
                            # Progress update every 100 frames
                            if frame_idx % 100 == 0:
                                elapsed = time.time() - start_time
                                fps = frame_idx / elapsed if elapsed > 0 else 0
                                print(f"Processed {frame_idx} frames in {elapsed:.1f}s (avg {fps:.1f} FPS)")
                        else:
                            break

            print(f"Processing completed. Total frames processed: {frame_idx}")
            print(f"Total time: {time.time() - start_time:.1f}s")

        except Exception as e:
            print(f"[ERROR] Processing failed: {e}")
        finally:    # always save results
            if self.json:
                save_COCO_format_json(os.path.join(self.output_dir, "COCOformat.json"))
            if self.csv:
                save_COCO_format_csv(os.path.join(self.output_dir, f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_JSON.csv"))
                save_Tx_csv_data(os.path.join(self.output_dir, f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_Tx.csv"))

    def process_frame(self, frame, frame_number):
        # Start timing
        start_time = time.time()

        # If frame is a PyTorch tensor, it's on GPU. Convert to CPU NumPy for OpenCV operations.
        if isinstance(frame, torch.Tensor):
            # Ensure it's RGB (PyNvCodec outputs RGB) and convert to BGR for OpenCV
            frame_np = frame.cpu().numpy()
            frame_np = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
        else:
            frame_np = frame # Already a NumPy array from OpenCV

        padded = self.pad_and_resize(frame_np) # pad_and_resize expects numpy array
        
        # --- Inference and Timing ---
        inference_start = time.time()
        predictions = self.run_model(padded)
        inference_stop = time.time()
        stop_time = time.time()

        # Handle different model output formats
        poses, scores = None, None
        
        if hasattr(self, 'process_results') and hasattr(self, 'draw_poses'):
            # For models that return pafs/heatmaps (like some OpenVINO models)
            if isinstance(predictions, dict):
                try:
                    pafs = predictions.get(self.pafs_output_key)
                    heatmaps = predictions.get(self.heatmaps_output_key)
                    if pafs is not None and heatmaps is not None:
                        poses, scores = self.process_results(frame_np, pafs, heatmaps)
                        frame_np = self.draw_poses(frame_np, poses, 0.1)
                except (KeyError, AttributeError, TypeError) as e:
                    print(f"[WARNING] Could not process pafs/heatmaps: {e}")
            # For models that return poses directly (like OpenVINO base models)
            elif isinstance(predictions, (list, tuple)) and len(predictions) > 0:
                # Check if predictions is already poses/scores
                if len(predictions) == 2 and isinstance(predictions[0], (list, np.ndarray)):
                    poses, scores = predictions
                    frame_np = self.draw_poses(frame_np, poses, 0.1)
                else:
                    # Assume predictions is a list of poses
                    poses = predictions
                    frame_np = self.draw_poses(frame_np, poses, 0.1)
        else:
            # For models that handle pose processing internally
            # The predictions are processed in postprocess method
            pass

        # --- Timing Calculation and Console Output ---
        processing_time_ms = (stop_time - start_time) * 1000
        self.processing_times.append(processing_time_ms)
        
        # Use processing times from last 200 frames.
        if len(self.processing_times) > self.max_processing_times_len:
            self.processing_times.popleft()

        # Calculate FPS
        if self.processing_times: # Avoid division by zero if deque is empty
            mean_processing_time = np.mean(self.processing_times)
            fps = 1000 / mean_processing_time if mean_processing_time > 0 else 0
        else:
            fps = 0

        # Print inference time and FPS to console (single line that updates)
        print(f"Inference time: {processing_time_ms:.1f}ms ({fps:.1f} FPS)", end='\r', flush=True)

        # Draw FPS on the frame
        if frame_np is not None and fps > 0:
            try:
                f_width, _ = frame_np.shape[:2]
                cv2.putText(
                    frame_np,
                    f"Inference time: {processing_time_ms:.1f}ms ({fps:.1f} FPS)",
                    (20, 40), # Position of the text
                    cv2.FONT_HERSHEY_COMPLEX,
                    f_width / 1000, # Font scale
                    (0, 0, 255), # Text color (BGR format, red)
                    1, # Thickness
                    cv2.LINE_AA, # Line type
                )
            except Exception as e:
                print(f"[WARNING] Could not draw FPS on frame: {e}")

        # --- Postprocessing and Saving ---
        # The original postprocess call might need to be adjusted if it uses the 'predictions' directly
        # or if it needs the 'bodies' derived from poses.
        # For now, I'll assume 'bodies' are derived from 'poses' and 'scores'
        # If 'predictions' is not directly used by postprocess, this might need adjustment.
        # Let's assume postprocess uses the output of run_model, which is 'predictions'
        bodies = self.postprocess(predictions) # Keep original postprocess call

        if self.json:
            append_COCO_format_json(bodies, self.score_thresh, frame_number)
        if self.csv:
            # The original code used 'timestamp' here, which was defined at the start of the function.
            # Now, we have start_time and stop_time. Let's use the end of inference for timestamp.
            append_COCO_format_csv(bodies, self.score_thresh, frame_number, stop_time, self.measurement_interval_ms)


        if self.save_image or self.save_video:
            # Ensure that LINES_BODY is defined in the child class
            if not hasattr(self, 'LINES_BODY'):
                print("[WARNING] LINES_BODY is not defined in the child class. Cannot render.")
            else:
                # The render function might need to be adjusted if it expects poses directly
                # or if it uses the 'bodies' variable.
                # For now, I'll keep the original render call, assuming it works with 'bodies'.
                render(frame_np, bodies, self.LINES_BODY, self.score_thresh, self.show_scores, self.show_bounding_box)

            if self.save_video:
                if not self.output.isOpened():
                    raise ValueError("Failed to open the video writer")
                self.output.write(frame_np)

            elif self.save_image:
                filename = os.path.join(self.output_dir, f"frame_{frame_number:04d}.jpg")
                cv2.imwrite(filename, frame_np)
    
    
    
    
    @abstractmethod
    def run_model(self, padded):
        pass

    @abstractmethod
    def postprocess(self, predictions):
        pass

    # Define the padding
    # Note we don't center the source image. The padding is applied
    # on the bottom or right side. That simplifies a bit the calculation
    # when depadding
    def set_padding(self):
        if self.img_w / self.img_h > self.pd_w / self.pd_h:
            pad_h = int(self.img_w * self.pd_h / self.pd_w - self.img_h)
            self.padding = Padding(0, pad_h, self.img_w, self.img_h + pad_h)
        else:
            pad_w = int(self.img_h * self.pd_w / self.pd_h - self.img_w)
            self.padding = Padding(pad_w, 0, self.img_w + pad_w, self.img_h)

    # Pad and resize the image to prepare for the model input.
    def pad_and_resize(self, frame):
        padded = cv2.copyMakeBorder(frame, 0, self.padding.h, 0, self.padding.w, cv2.BORDER_CONSTANT)
        padded = cv2.resize(padded, (self.pd_w, self.pd_h), interpolation=cv2.INTER_AREA)

        return padded
