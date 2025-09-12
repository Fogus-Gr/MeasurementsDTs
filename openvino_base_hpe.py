from pathlib import Path
import os
import numpy as np
import cv2

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
    LINES_BODY = [
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    # VPS-friendly knobs: ov_threads / ov_mode / ov_streams
    def __init__(self, model_type, device="CPU", ov_threads=None, ov_mode=None, ov_streams=None, **kwargs):
        if model_type not in MODEL_CONFIGS:  # BUGFIX: check arg, not self.model_type
            raise ValueError(f"Unsupported model type: {model_type}. Choose from: {list(MODEL_CONFIGS.keys())}")

        self.model_type = model_type
        self.model_cfg = MODEL_CONFIGS[self.model_type]
        self.device = device

        # Defaults via ENV (so main.py changes are optional)
        # 4-vCPU VPS: leave ~1 for decode/IO -> 3 for inference
        env_threads = os.getenv("OV_THREADS")
        env_mode = os.getenv("OV_MODE")          # "throughput" or "latency"
        env_streams = os.getenv("OV_STREAMS")    # int or empty

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
        if input_src.isdigit():
            # Webcam input
            self.cap = cv2.VideoCapture(int(input_src))
        else:
            # Video file or HTTP stream
            self.cap = cv2.VideoCapture(input_src)

        if not self.cap.isOpened():
            raise ValueError(f"Failed to open video capture: {input_src}")

        # Get video properties
        self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps == 0:
            self.video_fps = 25  # Default FPS

        print(f"Video capture initialized: {self.img_w}x{self.img_h} @ {self.video_fps} FPS")

    def _configure_core(self, core):
        # 2025.x API: use openvino.properties
        from openvino import properties as props

        perf = (
            props.hint.PerformanceMode.THROUGHPUT
            if self.ov_mode == "throughput"
            else props.hint.PerformanceMode.LATENCY
        )

        cpu_props = {
            props.hint.performance_mode: perf,
            props.inference_num_threads: int(self.ov_threads),   # e.g., 3 on 4-vCPU VPS
            props.hint.enable_cpu_pinning: True,
            props.hint.enable_hyper_threading: False,
        }
        if self.ov_streams is not None:
            cpu_props[props.num_streams] = int(self.ov_streams)

        core.set_property("CPU", cpu_props)

        from openvino import properties as props
        print("[OV] effective:",
            "mode=", core.get_property("CPU", props.hint.performance_mode),
            "threads=", core.get_property("CPU", props.inference_num_threads),
            "streams=", core.get_property("CPU", props.num_streams))

    def load_model(self):
        print(f"Loading {self.model_type} model...")

        xml_path = self.model_cfg["path"]

        # --- plugin config (sanitize legacy keys) ---
        plugin_config = get_user_config(self.device, '', None) or {}
        for k in [
            "PERFORMANCE_HINT", "CPU_THREADS_NUM", "CPU_THROUGHPUT_STREAMS",
            "INFERENCE_NUM_THREADS", "NUM_STREAMS", "ENABLE_CPU_PINNING",
            "ENABLE_HYPER_THREADING"
        ]:
            plugin_config.pop(k, None)

        # --- configure CPU once (your _configure_core uses openvino.properties) ---
        core = create_core()  # ov.Core from model_api
        self._configure_core(core)

        # --- adapter ---
        model_adapter = OpenvinoAdapter(
            core, xml_path,
            device=self.device,
            plugin_config=plugin_config,
            max_num_requests=0,
            # model_parameters={"input_layouts": {"data": "NCHW"}}  # only if you truly need it
        )

        # Print detailed network information like MoveNet
        print("Reading network")
        # Try to get network info from the adapter
        try:
            # Check if we can access the model through the adapter
            if hasattr(model_adapter, '_model'):
                network = model_adapter._model
            elif hasattr(model_adapter, 'model'):
                network = model_adapter.model
            else:
                # Fallback: try to read the model directly
                network = core.read_model(xml_path)

            print(f"Input info: {network.inputs}")
            print(f"Output info: {network.outputs}")

            for input_tensor in network.inputs:
                print(f"Input blob: {input_tensor.get_any_name()} - shape: {input_tensor.shape}")
            for output_tensor in network.outputs:
                print(f"Output blob: {output_tensor.get_any_name()} - shape: {output_tensor.shape}")
        except Exception as e:
            print(f"Could not read detailed network info: {e}")
            print("Model adapter outputs:", list(model_adapter.get_output_layers().keys()))

        print(f"DEBUG: Model adapter outputs before ImageModel.create_model: {model_adapter.get_output_layers().keys()}")

        # compute aspect ratio safely; fallback to 1.0 if unknown
        w = int(self.img_w or 0)
        h = int(self.img_h or 0)
        aspect_ratio = (w / h) if (w > 0 and h > 0) else 1.0

        if self.model_type == "openpose":
            # OPENPOSE (intel/human-pose-estimation-0001) wants a tuple (W,H)
            # human-pose-estimation-0001: target_size = HEIGHT (int)
            height_int = int(self.model_cfg["input_size"][1])  # 256
            config = {
                "target_size": height_int,                # int HEIGHT
                "aspect_ratio": float(aspect_ratio),      # width / height of the SOURCE image
                "confidence_threshold": self.score_thresh,
                "use_pooled_heatmaps": False,             # 0001 has no 'pooled_heatmaps' output
                "upsample_ratio": 4,                      # int (your file expects int)
                # no padding_mode / delta for openpose
            }
        else: # AE/HigherHRNet blocks as-is
            is_ae = (self.model_cfg["architecture"] == "HPE-associative-embedding")
            size_int = int(self.model_cfg["input_size"][0])  # 288 for 0005

            config = {
                "target_size": size_int,
                "aspect_ratio": float(aspect_ratio),          # <-- required, not None
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
        inputs, preprocessing_meta = self.model.preprocess(padded)
        raw_result = self.model.infer_sync(inputs)

        results = None  # safe default
        if raw_result:
            results = self.model.postprocess(raw_result, preprocessing_meta)

        poses = []  # safe default
        scores = []  # safe default
        if results:
            poses, scores = results

        return poses, scores

    def postprocess(self, predictions):
        # predictions is now (poses, scores) from run_model
        poses, scores = predictions if isinstance(predictions, tuple) else (predictions, None)

        bodies = []

        for pose in poses:
            keypoints_xy = pose[:, :2]  # (17,2)
            keypoints_scores = pose[:, 2]  # (17,)

            score = float(np.mean(keypoints_scores))
            if score > self.score_thresh:
                # Depad & rescale keypoints to original image size
                keypoints_xy_orig = keypoints_xy.copy()

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
