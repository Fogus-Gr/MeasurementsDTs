from openvino.runtime import Core
import numpy as np
import cv2
from pathlib import Path
from base_hpe import BaseHPE
from abc import abstractmethod

SCRIPT_DIR = Path(__file__).resolve().parent
model_map = {
            "movenet": SCRIPT_DIR / "models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml",
            "openpose": SCRIPT_DIR / "models/OpenPose/human-pose-estimation-0001.xml"
        }

class OpenVINOBaseHPE(BaseHPE):
    def load_model(self, model_type, device="CPU", **kwargs):
        print(f"Loading {model_type} model...")

        if model_type not in model_map:
            raise ValueError(f"Unsupported model type: {model_type}. Choose from: {list(model_map.keys())}")

        xml_path = model_map[model_type]

        self.ie = Core()
        print("Device info:")
        versions = self.ie.get_versions(device)
        print("{}{}".format(" "*8, device))
        for key, version in versions.items():
            print(f"{key}: version {version.major}.{version.minor}, build {version.build_number}")

        print("Reading network")
        self.pd_net = self.ie.read_model(model=xml_path)
        input_tensor = self.pd_net.inputs[0]
        print(f"Input info: {self.pd_net.inputs}")
        print(f"Output info: {self.pd_net.outputs}")

        self.pd_input_blob = input_tensor.get_any_name()
        print(f"Input blob: {self.pd_input_blob} - shape: {input_tensor.shape}")
        _, _, self.pd_h, self.pd_w = input_tensor.shape
        for output in self.pd_net.outputs:
            print(f"Output blob: {output.get_any_name()} - shape: {output.shape}")

        self.pd_kps = "Identity"
        print("Loading pose detection model into the plugin")
        self.pd_exec_net = self.ie.compile_model(model=self.pd_net, device_name=device)

    def run_model(self, padded):
        self.padded_shape = padded.shape
        frame_nn = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).transpose(2,0,1).astype(np.float32)[None,] 

        return self.pd_exec_net.infer_new_request({self.pd_input_blob: frame_nn})
    
    @abstractmethod
    def postprocess(self, predictions):
        pass