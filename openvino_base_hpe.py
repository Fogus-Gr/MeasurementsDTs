from pathlib import Path
import os
import numpy as np

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

    def _configure_core(self, core: ov.Core):
        # Map to OV performance hints
        perf_mode = ov.hint.PerformanceMode.THROUGHPUT if self.ov_mode == "throughput" else ov.hint.PerformanceMode.LATENCY
        cpu_props = {
            ov.hint.performance_mode: perf_mode,
            ov.inference_num_threads: self.ov_threads,
            ov.hint.enable_cpu_pinning: True,
            ov.hint.enable_hyper_threading: False,  # helps on small VPS
        }
        if self.ov_streams is not None:
            cpu_props[ov.num_streams] = int(self.ov_streams)
        core.set_property("CPU", cpu_props)

    def load_model(self):
        print(f"Loading {self.model_type} model...")

        xml_path = self.model_cfg["path"]

        plugin_config = get_user_config(self.device, '', None)

        # Configure CPU once
        core = create_core()  # returns ov.Core from model_api
        self._configure_core(core)

        # Build adapter; let OV infer layouts unless you need to force them
        model_adapter = OpenvinoAdapter(
            core, xml_path,
            device=self.device,
            plugin_config=plugin_config,
            max_num_requests=0,
            # model_parameters={"input_layouts": {"data": "NCHW"}}
        )

        # Default to 1.0 aspect ratio if dimensions aren't known at load time
        aspect_ratio = (self.img_w / self.img_h) if (self.img_w and self.img_h) else 1.0

        config = {
            "target_size": None,
            "aspect_ratio": aspect_ratio,
            "confidence_threshold": self.score_thresh,
            # the 'higherhrnet' and 'ae' specific
            "padding_mode": "center" if self.model_type == "higherhrnet" else None,
            "delta": 0.5 if self.model_type == "higherhrnet" else None,
        }
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
        if results:
            poses, _scores = results

        return poses

    def postprocess(self, poses):
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
