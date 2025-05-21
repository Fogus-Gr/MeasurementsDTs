from openvino.runtime import Core
import numpy as np
import cv2
from pathlib import Path
from base_hpe import BaseHPE
from abc import abstractmethod

from models.OpenVINO.model_api.models import ImageModel, OutputTransform
from models.OpenVINO.model_api.adapters import create_core, OpenvinoAdapter
from models.OpenVINO.model_api.pipelines import get_user_config, AsyncPipeline
#from model_api.models import ImageModel, OutputTransform
#from model_api.performance_metrics import PerformanceMetrics
#from model_api.pipelines import get_user_config, AsyncPipeline
#from model_api.adapters import create_core, OpenvinoAdapter

from base_hpe import Body

SCRIPT_DIR = Path(__file__).resolve().parent
model_map = {
            "movenet": SCRIPT_DIR / "models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml",
            "openpose": SCRIPT_DIR / "models/OpenVINO/pretrained_models/human-pose-estimation-0001.xml"
        }

ARCHITECTURES = {
    'ae': 'HPE-assosiative-embedding',
    'higherhrnet': 'HPE-assosiative-embedding',
    'openpose': 'openpose'
}

class OpenVINOBaseHPE(BaseHPE):
    LINES_BODY = [
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    def load_model(self, model_type, device="CPU", **kwargs):
        print(f"Loading {model_type} model...")

        if model_type not in model_map:
            raise ValueError(f"Unsupported model type: {model_type}. Choose from: {list(model_map.keys())}")

        xml_path = model_map[model_type]

        plugin_config = get_user_config(device, '', None)
        model_adapter = OpenvinoAdapter(create_core(), xml_path, device=device, plugin_config=plugin_config,
                                        max_num_requests=0, model_parameters = {'input_layouts': 0})

        config = {
            #'target_size': (self.pd_w, self.pd_h),
            'target_size': None,
            'aspect_ratio': self.img_w / self.img_h,
            'confidence_threshold': 0.2,
            'padding_mode': None, # the 'higherhrnet' and 'ae' specific
            'delta': None, # the 'higherhrnet' and 'ae' specific
        }
        model = ImageModel.create_model(ARCHITECTURES[model_type], model_adapter, config)
        model.log_layers_info()

        self.hpe_pipeline = AsyncPipeline(model)

    def run_model(self, padded):
        self.hpe_pipeline.submit_data(padded, 0, {'frame': padded, 'start_time': 0})
        #output_transform = OutputTransform(padded.shape[:2], args.output_resolution)
        output_resolution = None
        output_transform = OutputTransform(padded.shape[:2], output_resolution)
        if output_resolution:
            output_resolution = output_transform.new_resolution
        else:
            output_resolution = (padded.shape[1], padded.shape[0])

        next_frame_id_to_show = 0
        results = self.hpe_pipeline.get_result(next_frame_id_to_show)

        if results:
            (poses, scores), frame_meta = results

        return poses
    
    @abstractmethod
    def postprocess(self, predictions):
        return predictions