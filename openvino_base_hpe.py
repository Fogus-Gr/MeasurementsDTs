# import asyncio
# import concurrent.futures
# from queue import Queue
# import threading
import logging
import time
from pathlib import Path
import os
import numpy as np
import cv2
import torch

from base_hpe import BaseHPE, _is_stream_url
from base_hpe import Body

from models.OpenVINO.model_api.models import ImageModel
from models.OpenVINO.model_api.adapters import create_core, OpenvinoAdapter
from models.OpenVINO.model_api.pipelines import get_user_config

import openvino as ov  # CPU tuning

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_CONFIGS = {
    "openpose": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001/human-pose-estimation-0001.xml",
        "input_size": (456, 256),
        "architecture": "openpose",
        "gpu_supported": True,
    },
    "efficienthrnet1": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/public/human-pose-estimation-0005/FP32/human-pose-estimation-0005.xml",
        "input_size": (288, 288),
        "architecture": "HPE-associative-embedding",
        "gpu_supported": True,
    },
    "efficienthrnet2": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/public/human-pose-estimation-0006/FP32/human-pose-estimation-0006.xml",
        "input_size": (352, 352),
        "architecture": "HPE-associative-embedding",
        "gpu_supported": True,
    },
    "efficienthrnet3": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/public/human-pose-estimation-0007/FP32/human-pose-estimation-0007.xml",
        "input_size": (448, 448),
        "architecture": "HPE-associative-embedding",
        "gpu_supported": True,
    },
    "higherhrnet": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.xml",
        "input_size": (512, 512),
        "architecture": "HPE-associative-embedding",
        "gpu_supported": False,
    }
}

class OpenVINOBaseHPE(BaseHPE):
    """Base OpenVINO Human Pose Estimation class"""
    LINES_BODY = [
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    def __init__(self, model_type, device="CPU", ov_threads=None, ov_mode=None, ov_streams=None, **kwargs):
        if model_type not in MODEL_CONFIGS:
            raise ValueError(f"Unsupported model type: {model_type}. Choose from: {list(MODEL_CONFIGS.keys())}")

        self.model_type = model_type
        self.model_cfg = MODEL_CONFIGS[self.model_type]
        self.device = device

        # Defaults via ENV (so main.py changes are optional)
        env_threads = os.getenv("OV_THREADS")
        env_mode = os.getenv("OV_MODE")
        env_streams = os.getenv("OV_STREAMS")
        env_cpu_pinning = os.getenv("OV_CPU_PINNING")
        env_hyper_threading = os.getenv("OV_HYPER_THREADING")

        self.ov_threads = int(ov_threads if ov_threads is not None else (env_threads or 1))
        self.ov_mode = (ov_mode or env_mode or "latency").lower()
        self.ov_streams = int(env_streams) if (ov_streams is None and env_streams and env_streams.isdigit()) else ov_streams
        
        # CPU pinning and hyper-threading configuration
        self.ov_cpu_pinning = env_cpu_pinning.lower() == "true" if env_cpu_pinning else False
        self.ov_hyper_threading = env_hyper_threading.lower() == "true" if env_hyper_threading else False

        if self.device == "GPU" and not self.model_cfg["gpu_supported"]:
            print(f"[INFO] Model '{self.model_type}' is not supported on GPU. Falling back to CPU.")
            self.device = "CPU"

        self.pd_w, self.pd_h = self.model_cfg["input_size"]
        super().__init__(**kwargs)

    def _init_opencv_video_capture(self, input_src):
        """Initialize OpenCV video capture for fallback when PyNvCodec is not available."""
        print(f"Initializing OpenCV video capture for: {input_src}")
        
        # Handle both string and integer inputs
        if isinstance(input_src, str) and input_src.isdigit():
            self.cap = cv2.VideoCapture(int(input_src))
        elif isinstance(input_src, int):
            self.cap = cv2.VideoCapture(input_src)
        else:
            # Use FFmpeg backend for HTTP/RTSP streams for better reliability
            if isinstance(input_src, str) and _is_stream_url(input_src):
                print(f"Using FFmpeg backend for stream: {input_src}")
                self.cap = cv2.VideoCapture(input_src, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency for real-time streams
            else:
                self.cap = cv2.VideoCapture(input_src)

        if not self.cap.isOpened():
            print(f"[ERROR] Could not open video source: {input_src}")
            # For streaming URLs, set default dimensions and continue
            if isinstance(input_src, str) and _is_stream_url(input_src):
                print("[INFO] Setting default dimensions for streaming URL")
                self.img_w = 640
                self.img_h = 480
                self.video_fps = 25
                self.cap = None  # Will be initialized later when needed
                return
            else:
                raise ValueError(f"Failed to open video capture: {input_src}")

        self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps == 0:
            self.video_fps = 25

        print(f"Video capture initialized: {self.img_w}x{self.img_h} @ {self.video_fps} FPS")

    def _ensure_video_capture(self):
        """Ensure video capture is initialized for streaming URLs"""
        if self.cap is None and hasattr(self, 'input_src') and isinstance(self.input_src, str) and _is_stream_url(self.input_src):
            print(f"Initializing video capture for streaming URL: {self.input_src}")
            print(f"Using FFmpeg backend for stream: {self.input_src}")
            self.cap = cv2.VideoCapture(self.input_src, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency for real-time streams
            if not self.cap.isOpened():
                print(f"[WARNING] Could not open streaming URL: {self.input_src}")
                return False
            # Update dimensions from the actual stream
            self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if self.video_fps == 0:
                self.video_fps = 25
            print(f"Stream dimensions: {self.img_w}x{self.img_h} @ {self.video_fps} FPS")
            return True
        return self.cap is not None

    def _configure_core(self, core):
        """Configure OpenVINO core with performance settings"""
        from openvino import properties as props

        perf = (
            props.hint.PerformanceMode.THROUGHPUT
            if self.ov_mode == "throughput"
            else props.hint.PerformanceMode.LATENCY
        )

        cpu_props = {
            props.hint.performance_mode: perf,
            props.inference_num_threads: int(self.ov_threads),
            props.hint.enable_cpu_pinning: self.ov_cpu_pinning,
            props.hint.enable_hyper_threading: self.ov_hyper_threading,
        }
        if self.ov_streams is not None:
            cpu_props[props.num_streams] = int(self.ov_streams)

        def _safe_get(core, device, prop, fallback):
            try:
                return core.get_property(device, prop)
            except Exception:
                logging.warning("Could not read property %s on device %s; using fallback.", prop, device)
                return fallback

        core.set_property("CPU", cpu_props)

        print("\n[OpenVINO Configuration]")
        print(f"  Requested settings: threads={self.ov_threads}, mode={self.ov_mode}, streams={self.ov_streams}")
        print("  Effective settings:")
        print(f"    Performance mode: {_safe_get(core, 'CPU', props.hint.performance_mode, 'unknown')}")
        print(f"    CPU threads: {_safe_get(core, 'CPU', props.inference_num_threads, self.ov_threads)}")
        print(f"    CPU streams: {_safe_get(core, 'CPU', props.num_streams, self.ov_streams)}")
        print(f"    CPU pinning: {_safe_get(core, 'CPU', props.hint.enable_cpu_pinning, self.ov_cpu_pinning)}")
        print(f"    Hyper-threading: {_safe_get(core, 'CPU', props.hint.enable_hyper_threading, self.ov_hyper_threading)}\n")

    def load_model(self):
        """Load OpenVINO model"""
        print(f"Loading {self.model_type} model...")

        xml_path = self.model_cfg["path"]
        plugin_config = get_user_config(self.device, '', None) or {}

        # Remove legacy keys
        for k in ["PERFORMANCE_HINT", "CPU_THREADS_NUM", "CPU_THROUGHPUT_STREAMS",
                  "INFERENCE_NUM_THREADS", "NUM_STREAMS", "ENABLE_CPU_PINNING",
                  "ENABLE_HYPER_THREADING"]:
            plugin_config.pop(k, None)

        core = create_core()
        self._configure_core(core)

        model_adapter = OpenvinoAdapter(
            core, xml_path,
            device=self.device,
            plugin_config=plugin_config,
            max_num_requests=0,
        )

        print("Reading network")
        try:
            if hasattr(model_adapter, '_model'):
                network = model_adapter._model
            elif hasattr(model_adapter, 'model'):
                network = model_adapter.model
            else:
                network = core.read_model(xml_path)

            print(f"Input info: {network.inputs}")
            print(f"Output info: {network.outputs}")

            for input_tensor in network.inputs:
                print(f"Input blob: {input_tensor.get_any_name()} - shape: {input_tensor.shape}")
            for output_tensor in network.outputs:
                print(f"Output blob: {output_tensor.get_any_name()} - shape: {output_tensor.shape}")
        except Exception as e:
            print(f"Could not read detailed network info: {e}")

        print(f"DEBUG: Model adapter outputs: {list(model_adapter.get_output_layers().keys())}")

        # Default to 1.0 aspect ratio if dimensions aren't known at load time
        aspect_ratio = (self.img_w / self.img_h) if (self.img_w and self.img_h) else 1.0

        if self.model_type == "openpose":
            config = {
                'target_size': None,
                'aspect_ratio': aspect_ratio,
                'confidence_threshold': self.score_thresh,
                # NOTE: do NOT pass use_pooled_heatmaps here — the parameter was
                # removed from open_pose.py in a90d5dd. The NMS pooled_heatmaps
                # layer is always added dynamically; no config flag controls it.
                'upsample_ratio': 4,
            }
        else:
            config = {
                'target_size': None,
                'aspect_ratio': aspect_ratio,
                'confidence_threshold': self.score_thresh,
                'padding_mode': 'center' if self.model_type == 'higherhrnet' else None,
                'delta': 0.5 if self.model_type == 'higherhrnet' else None,
            }

        architecture = self.model_cfg["architecture"]
        self.model = ImageModel.create_model(architecture, model_adapter, config)
        self.model.log_layers_info()
        self.model.load()
        print("Loading completed")

    def run_model(self, padded):
        """Run inference on preprocessed frame"""
        if self.model_type in ("openpose", "higherhrnet") and hasattr(self, "_current_frame"):
            model_input = self._current_frame
        else:
            model_input = padded

        inputs, preprocessing_meta = self.model.preprocess(model_input)
        raw_result = self.model.infer_sync(inputs)

        results = None
        if raw_result:
            results = self.model.postprocess(raw_result, preprocessing_meta)

        poses = []
        scores = []
        if results:
            poses, scores = results

        return poses, scores

    def postprocess(self, predictions):
        """Postprocess model predictions"""
        poses, scores = predictions if isinstance(predictions, tuple) else (predictions, None)

        bodies = []

        for pose in poses:
            keypoints_xy = pose[:, :2]
            keypoints_scores = pose[:, 2]

            score = float(np.mean(keypoints_scores))
            if score > self.score_thresh:
                keypoints_xy_orig = keypoints_xy.copy()

                if self.model_type not in ("openpose", "higherhrnet"):
                    unpadded_w = self.img_w + self.padding.w
                    unpadded_h = self.img_h + self.padding.h
                    keypoints_xy_orig[:, 0] *= (unpadded_w / self.pd_w)
                    keypoints_xy_orig[:, 1] *= (unpadded_h / self.pd_h)

                visible_kps = keypoints_xy_orig[keypoints_scores > 0.1]
                if len(visible_kps) == 0:
                    continue

                xmin = int(np.min(visible_kps[:, 0]))
                xmax = int(np.max(visible_kps[:, 0]))
                ymin = int(np.min(visible_kps[:, 1]))
                ymax = int(np.max(visible_kps[:, 1]))

                body = Body(
                    score=score,
                    xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
                    keypoints_score=keypoints_scores,
                    keypoints=keypoints_xy_orig.astype(float),
                    keypoints_norm=keypoints_xy_orig / np.array([self.img_w, self.img_h], dtype=float)
                )
                bodies.append(body)

        return bodies

    def process_frame(self, frame, frame_number):
        self._current_frame = frame.cpu().numpy() if isinstance(frame, torch.Tensor) else frame
        try:
            return super().process_frame(frame, frame_number)
        finally:
            self._current_frame = None

    def main_loop(self):
        """Override main_loop to handle streaming URLs properly"""
        from utils.evaluator import reset_results
        reset_results()
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
            import glob
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
                    if surface.Empty():
                        break

                    # Convert to PyTorch tensor
                    frame_tensor = self.surface_to_tensor(surface)
                    self.process_frame(frame_tensor, frame_number)
                    frame_number += 1

                except KeyboardInterrupt:
                    print("\nStopping video processing...")
                    break
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    break

        else:   # OpenCV video/webcam/stream fallback
            # Ensure video capture is initialized for streaming URLs
            if not self._ensure_video_capture():
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
            from utils.evaluator import save_COCO_format_json
            save_COCO_format_json(os.path.join(self.output_dir, "COCOformat.json"))
        if self.csv:
            from utils.evaluator import save_COCO_format_csv, save_Tx_csv_data
            save_COCO_format_csv(os.path.join(self.output_dir, f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_JSON.csv"))
            save_Tx_csv_data(os.path.join(self.output_dir, f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_Tx.csv"))
