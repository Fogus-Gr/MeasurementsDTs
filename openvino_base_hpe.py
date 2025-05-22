from pathlib import Path
from base_hpe import BaseHPE
from abc import abstractmethod

from models.OpenVINO.model_api.models import ImageModel
from models.OpenVINO.model_api.adapters import create_core, OpenvinoAdapter
from models.OpenVINO.model_api.pipelines import get_user_config


SCRIPT_DIR = Path(__file__).resolve().parent
model_map = {
            "openpose": SCRIPT_DIR / "models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001.xml",
            'higherhrnet': SCRIPT_DIR / "models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.xml"
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

        # Default to 1.0 aspect ratio if dimensions aren't known at load time
        aspect_ratio = (self.img_w / self.img_h) if (self.img_w and self.img_h) else 1.0

        config = {
            'target_size': None,
            'aspect_ratio': aspect_ratio,
            'confidence_threshold': 0.2,
            'padding_mode': 'center' if model_type == 'higherhrnet' else None, # the 'higherhrnet' and 'ae' specific
            'delta': 0.5 if model_type == 'higherhrnet' else None, # the 'higherhrnet' and 'ae' specific
        }
        self.model = ImageModel.create_model(ARCHITECTURES[model_type], model_adapter, config)
        self.model.log_layers_info()
        self.model.load()

    def run_model(self, padded):
        inputs, preprocessing_meta = self.model.preprocess(padded)
        raw_result = self.model.infer_sync(inputs)

        if raw_result:
            results = self.model.postprocess(raw_result, preprocessing_meta)

        if results:
            (poses, scores) = results

        return poses
    
    @abstractmethod
    def postprocess(self, predictions):
        pass