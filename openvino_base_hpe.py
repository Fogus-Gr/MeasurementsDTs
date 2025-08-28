from pathlib import Path
from base_hpe import BaseHPE
import numpy as np
from base_hpe import Body

from models.OpenVINO.model_api.models import ImageModel
from models.OpenVINO.model_api.adapters import create_core, OpenvinoAdapter
from models.OpenVINO.model_api.pipelines import get_user_config

import openvino as ov  # NEW

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

    # NEW: threads / mode / streams knobs with VPS-friendly defaults
    def __init__(self, model_type, device="CPU", ov_threads=3, ov_mode="throughput", ov_streams=None, **kwargs):
        if model_type not in MODEL_CONFIGS:  # BUGFIX: use local arg, not self.model_type
            raise ValueError(f"Unsupported model type: {model_type}. Choose from: {list(MODEL_CONFIGS.keys())}")

        self.model_type = model_type
        self.model_cfg = MODEL_CONFIGS[self.model_type]
        self.device = device

        # OpenVINO CPU knobs (4 vCPU VPS: 3 for infer, 1 for decode/IO)
        self.ov_threads = int(ov_threads)            # e.g., 3
        self.ov_mode = ov_mode.lower()               # "throughput" or "latency"
        self.ov_streams = ov_streams                 # None = let hint decide

        if self.device == "GPU" and not self.model_cfg["gpu_supported"]:
            print(f"[INFO] Model '{self.model_type}' is not supported on GPU. Falling back to CPU.")
            self.device = "CPU"

        self.pd_w, self.pd_h = self.model_cfg["input_size"]

        super().__init__(**kwargs)

    def _configure_core(self, core: ov.Core):
        # Map string to OV enum
        perf_mode = ov.hint.PerformanceMode.THROUGHPUT if self.ov_mode == "throughput" else ov.hint.PerformanceMode.LATENCY

        cpu_props = {
            ov.hint.performance_mode: perf_mode,
            ov.inference_num_threads: self.ov_threads,
            ov.hint.enable_cpu_pinning: True,
            ov.hint.enable_hyper_threading: False,  # tiny VPS: avoid SMT thrash
        }
        if self.ov_streams is not None:
            # You can set a fixed number of streams if you want explicit control
            cpu_props[ov.num_streams] = int(self.ov_streams)

        core.set_property("CPU", cpu_props)

    def load_model(self):
        print(f"Loading {self.model_type} model...")

        xml_path = self.model_cfg["path"]

        # Get default plugin config from your pipeline helper (kept for compatibility)
        plugin_config = get_user_config(self.device, '', None)

        # Create/OpenVINO core and apply CPU performance hints
        core = create_core()  # returns ov.Core
        self._configure_core(core)

        # Build adapter. Let OV infer layouts; set explicitly only if needed.
        model_adapter = OpenvinoAdapter(
            core, xml_path, device=self.device,
            plugin_config=plugin_config,
            max_num_requests=0,
            # model_parameters={"input_layouts": {"data": "NCHW"}}  # uncomment if your model requires it
        )

        # Aspect ratio (used by model_api preproc)
        aspect_ratio = (self.img_w / self.img_h) if (self.img_w and self.img_h) else 1.0

        config = {
            "target_size": None,
            "aspect_ratio": aspect_ratio,
            "confidence_threshold": self.score_thresh,
            # specific for 'higherhrnet' / AE models
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

        results = None  # SAFE default
        if raw_result:
            results = self.model.postprocess(raw_result, preprocessing_meta)

        poses = []  # SAFE default
        if results:
            poses, scores = results

        return poses

    def postprocess(self, poses):
        bodies = []
        for pose in poses:
            keypoints_xy = pose[:, :2]
            keypoints_scores = pose[:, 2]
            score = float(np.mean(keypoints_scores))

            if score > self.score_thresh:
                keypoints_xy_orig = keypoints_xy.copy()

                # Undo resize/pad
                unpadded_w = self.img_w + self.padding.w
                unpadded_h = self.img_h + self.padding.h
                keypoints_xy_orig[:, 0] *= (unpadded_w / self.pd_w)
                keypoints_xy_orig[:, 1] *= (unpadded_h / self.pd_h)

                visible_kps = keypoints_xy_orig[keypoints_scores > 0.1]
                if len(visible_kps) == 0:
                    continue

                xmin = int(np.min(visible_kps[:, 0])); xmax = int(np.max(visible_kps[:, 0]))
                ymin = int(np.min(visible_kps[:, 1])); ymax = int(np.max(visible_kps[:, 1]))

                body = Body(
                    score=score,
                    xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
                    keypoints_score=keypoints_scores,
                    keypoints=keypoints_xy_orig.astype(float),
                    keypoints_norm=keypoints_xy_orig / np.array([self.img_w, self.img_h], dtype=float)
                )
                bodies.append(body)
        return bodies
