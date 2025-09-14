import asyncio
import concurrent.futures
from queue import Queue
import threading
import time
from pathlib import Path
import os
import numpy as np
import cv2
import torch

from base_hpe import BaseHPE
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
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/intel/human-pose-estimation-0005/FP32/human-pose-estimation-0005.xml",
        "input_size": (288, 288),
        "architecture": "HPE-associative-embedding",
        "gpu_supported": True,
    },
    "efficienthrnet2": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/intel/human-pose-estimation-0006/FP32/human-pose-estimation-0006.xml",
        "input_size": (352, 352),
        "architecture": "HPE-associative-embedding",
        "gpu_supported": True,
    },
    "efficienthrnet3": {
        "path": SCRIPT_DIR / "models/OpenVINO/pretrained_models/intel/human-pose-estimation-0007/FP32/human-pose-estimation-0007.xml",
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

        self.ov_threads = int(ov_threads if ov_threads is not None else (env_threads or 3))
        self.ov_mode = (ov_mode or env_mode or "throughput").lower()
        self.ov_streams = int(env_streams) if (ov_streams is None and env_streams and env_streams.isdigit()) else ov_streams

        if self.device == "GPU" and not self.model_cfg["gpu_supported"]:
            print(f"[INFO] Model '{self.model_type}' is not supported on GPU. Falling back to CPU.")
            self.device = "CPU"

        self.pd_w, self.pd_h = self.model_cfg["input_size"]
        super().__init__(**kwargs)

    def _init_opencv_video_capture(self, input_src):
        """Initialize OpenCV video capture for fallback when PyNvCodec is not available."""
        # Handle both string and integer inputs
        if isinstance(input_src, str) and input_src.isdigit():
            self.cap = cv2.VideoCapture(int(input_src))
        elif isinstance(input_src, int):
            self.cap = cv2.VideoCapture(input_src)
        else:
            self.cap = cv2.VideoCapture(input_src)

        if not self.cap.isOpened():
            raise ValueError(f"Failed to open video capture: {input_src}")

        self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps == 0:
            self.video_fps = 25

        print(f"Video capture initialized: {self.img_w}x{self.img_h} @ {self.video_fps} FPS")

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
            props.hint.enable_cpu_pinning: True,
            props.hint.enable_hyper_threading: False,
        }
        if self.ov_streams is not None:
            cpu_props[props.num_streams] = int(self.ov_streams)

        core.set_property("CPU", cpu_props)

        print("[OV] effective:",
            "mode=", core.get_property("CPU", props.hint.performance_mode),
            "threads=", core.get_property("CPU", props.inference_num_threads),
            "streams=", core.get_property("CPU", props.num_streams))

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

        w = int(self.img_w or 0)
        h = int(self.img_h or 0)
        aspect_ratio = (w / h) if (w > 0 and h > 0) else 1.0

        if self.model_type == "openpose":
            height_int = int(self.model_cfg["input_size"][1])
            config = {
                "target_size": height_int,
                "aspect_ratio": float(aspect_ratio),
                "confidence_threshold": self.score_thresh,
                "use_pooled_heatmaps": False,
                "upsample_ratio": 4,
            }
        else:
            is_ae = (self.model_cfg["architecture"] == "HPE-associative-embedding")
            size_int = int(self.model_cfg["input_size"][0])

            config = {
                "target_size": size_int,
                "aspect_ratio": float(aspect_ratio),
                "confidence_threshold": self.score_thresh,
            }

            if is_ae or self.model_type == 'higherhrnet':
                config["padding_mode"] = "center"

            if self.model_type == "higherhrnet":
                config["delta"] = 0.5

        architecture = self.model_cfg["architecture"]
        self.model = ImageModel.create_model(architecture, model_adapter, config)
        self.model.log_layers_info()
        self.model.load()
        print("Loading completed")

    def run_model(self, padded):
        """Run inference on preprocessed frame"""
        inputs, preprocessing_meta = self.model.preprocess(padded)
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
                unpadded_w = self.img_w + self.padding.w
                unpadded_h = self.img_h + self.padding.h
                keypoints_xy_orig = keypoints_xy.copy()
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

class AsyncOpenVINOBaseHPE(OpenVINOBaseHPE):
    """Async version of OpenVINO HPE with frame buffering and parallel processing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Async components
        self.frame_queue = asyncio.Queue(maxsize=5)  # Buffer up to 5 frames
        self.result_queue = asyncio.Queue()
        self.processing_task = None
        self.display_task = None
        self.capture_task = None

        # Thread pool for CPU-bound operations
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)

        # Performance monitoring
        self.frame_drops = 0
        self.last_frame_time = 0

    async def start_async_pipeline(self):
        """Start the async processing pipeline"""
        print("[ASYNC] Starting async processing pipeline...")
        print("[ASYNC] Pipeline started successfully")
        # Tasks will be created in the main async function to avoid event loop issues

    async def stop_async_pipeline(self):
        """Stop the async processing pipeline"""
        print("[ASYNC] Stopping async processing pipeline...")

        # Cancel all tasks
        tasks_to_cancel = [t for t in [self.processing_task, self.display_task, self.capture_task] if t]

        for task in tasks_to_cancel:
            task.cancel()

        # Wait for cancellation
        try:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        print(f"[ASYNC] Pipeline stopped. Frame drops: {self.frame_drops}")

    async def run_webcam_async(self):
        """Async webcam capture with frame dropping"""
        print("[ASYNC] Starting async webcam capture...")

        try:
            while True:
                # Capture frame in thread (non-blocking) - Python 3.9+ recommended approach
                ok, frame = await asyncio.to_thread(self.cap.read)

                if not ok:
                    print("[ASYNC] Webcam capture ended")
                    break

                current_time = time.time()

                # Frame rate limiting (optional)
                if current_time - self.last_frame_time < 1/30:  # Max 30 FPS
                    await asyncio.sleep(0.001)  # Small delay
                    continue

                self.last_frame_time = current_time

                # Try to queue frame
                try:
                    await self.frame_queue.put(frame)
                except asyncio.QueueFull:
                    # Drop frame to prevent latency buildup
                    self.frame_drops += 1
                    if self.frame_drops % 100 == 0:  # Log every 100 drops
                        print(f"[ASYNC] Frame drops: {self.frame_drops}")

        except Exception as e:
            print(f"[ASYNC] Webcam capture error: {e}")
        finally:
            # Signal end of capture
            await self.frame_queue.put(None)  # Sentinel value

    async def _process_frames_async(self):
        """Background frame processing pipeline"""
        frame_number = 0

        try:
            while True:
                # Get frame from queue
                frame = await self.frame_queue.get()

                # Check for sentinel (end of stream)
                if frame is None:
                    break

                # Process frame
                result = await self._process_single_frame_async(frame, frame_number)
                frame_number += 1

                # Queue result for display
                await self.result_queue.put(result)

        except asyncio.CancelledError:
            print("[ASYNC] Frame processing cancelled")
        except Exception as e:
            print(f"[ASYNC] Frame processing error: {e}")

    async def _process_single_frame_async(self, frame, frame_number):
        """Process single frame with OpenVINO inference"""
        start_time = time.time()

        try:
            # Convert to numpy if needed
            if isinstance(frame, torch.Tensor):
                frame_np = frame.cpu().numpy()
                frame_np = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
            else:
                frame_np = frame

            # Preprocessing (pad and resize)
            padded = await asyncio.to_thread(self.pad_and_resize, frame_np)

            # OpenVINO inference (in thread pool to avoid blocking)
            predictions = await asyncio.to_thread(self.run_model, padded)

            # Postprocessing
            bodies = await asyncio.to_thread(self.postprocess, predictions)

            # Calculate timing
            processing_time_ms = (time.time() - start_time) * 1000

            return {
                'frame': frame_np,
                'bodies': bodies,
                'processing_time': processing_time_ms,
                'frame_number': frame_number,
                'timestamp': time.time()
            }

        except Exception as e:
            print(f"[ASYNC] Frame processing error: {e}")
            return None

    async def _display_results_async(self):
        """Background result display and rendering"""
        try:
            while True:
                # Get result from queue
                result = await self.result_queue.get()

                if result is None:
                    break

                # Update performance stats
                self.processing_times.append(result['processing_time'])
                if len(self.processing_times) > self.max_processing_times_len:
                    self.processing_times.popleft()

                # Calculate FPS
                if self.processing_times:
                    mean_time = np.mean(self.processing_times)
                    fps = 1000 / mean_time if mean_time > 0 else 0
                else:
                    fps = 0

                # Render frame with results
                display_frame = result['frame'].copy()

                # Draw poses
                if hasattr(self, 'LINES_BODY') and result['bodies']:
                    from utils.visualizer import render
                    render(display_frame, result['bodies'], self.LINES_BODY,
                          self.score_thresh, self.show_scores, self.show_bounding_box)

                # Draw FPS and timing info
                if fps > 0:
                    cv2.putText(
                        display_frame,
                        f"ASYNC FPS: {fps:.1f} | Time: {result['processing_time']:.1f}ms",
                        (20, 40), cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 255, 0), 2
                    )

                # Display frame (in thread to avoid blocking)
                await asyncio.to_thread(cv2.imshow, 'Async HPE', display_frame)

                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break

        except asyncio.CancelledError:
            print("[ASYNC] Display cancelled")
        except Exception as e:
            print(f"[ASYNC] Display error: {e}")

    def main_loop_async(self):
        """Main async entry point"""
        async def async_main():
            try:
                # Load model (synchronous for now)
                self.load_model()

                print("[ASYNC] Starting async processing pipeline...")

                # Create background tasks in the same event loop context
                self.processing_task = asyncio.create_task(self._process_frames_async())
                self.display_task = asyncio.create_task(self._display_results_async())

                print("[ASYNC] Pipeline started successfully")

                # Run webcam capture
                if self.input_type == "webcam":
                    await self.run_webcam_async()
                else:
                    print(f"[ASYNC] Async processing not implemented for {self.input_type}")

            except KeyboardInterrupt:
                print("[ASYNC] Keyboard interrupt received")
            except Exception as e:
                print(f"[ASYNC] Main loop error: {e}")
            finally:
                # Cleanup
                await self.stop_async_pipeline()
                cv2.destroyAllWindows()

        # Run async main
        asyncio.run(async_main())

# Example usage function
def run_async_openvino_hpe(model_type="efficienthrnet1", device="CPU", input_src="0", **kwargs):
    """Example of how to use AsyncOpenVINOBaseHPE"""
    hpe = AsyncOpenVINOBaseHPE(
        model_type=model_type,
        device=device,
        input_src=input_src,
        ov_threads=kwargs.get('ov_threads', 3),
        ov_mode=kwargs.get('ov_mode', 'throughput'),
        **{k: v for k, v in kwargs.items() if k not in ['ov_threads', 'ov_mode']}
    )

    # Run async processing
    hpe.main_loop_async()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_type', type=str, default='efficienthrnet1', 
                       choices=['openpose', 'efficienthrnet1', 'efficienthrnet2', 'efficienthrnet3', 'higherhrnet'])
    parser.add_argument('--device', type=str, default='CPU', choices=['CPU', 'GPU'])
    parser.add_argument('--input', type=str, default='0', help='Input source (webcam, video file, etc.)')
    parser.add_argument('--ov_threads', type=int, default=3, help='OpenVINO threads')
    parser.add_argument('--ov_mode', type=str, default='throughput', choices=['throughput', 'latency'])
    
    args = parser.parse_args()
    run_async_openvino_hpe(**vars(args))
