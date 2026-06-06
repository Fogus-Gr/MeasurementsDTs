import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class HPERegressionTests(unittest.TestCase):
    def test_movenet_filters_people_by_instance_score(self):
        source = (ROOT / "movenet_hpe.py").read_text()

        self.assertIn("if score > self.score_thresh:", source)
        self.assertNotIn("mean_kp_score", source)

    def test_main_delegates_model_loading_to_processing_loop(self):
        source = (ROOT / "main.py").read_text()
        main_body = source[source.index("def main():"):source.index("def parse_arguments():")]

        self.assertNotIn("hpe.load_model()", main_body)

    def test_openpose_route_uses_openvino_model_adapter(self):
        source = (ROOT / "main.py").read_text()

        self.assertIn(
            "'openpose': lambda args: OpenVINOBaseHPE(model_type='openpose'",
            source,
        )

    def test_alphapose_route_uses_alphapose_adapter_with_detection_batch(self):
        source = (ROOT / "main.py").read_text()

        self.assertIn(
            "'alphapose': lambda args: AlphaPoseHPE(device=args.device, detbatch=args.detbatch",
            source,
        )

    def test_openpose_config_keeps_openvino_architecture(self):
        source = (ROOT / "openvino_base_hpe.py").read_text()

        self.assertIn('"openpose": {', source)
        self.assertIn('"architecture": "openpose"', source)

    def test_alphapose_identifies_its_model_type(self):
        source = (ROOT / "alphapose_hpe.py").read_text()

        self.assertIn('self.model_type = "alphapose"', source)


if __name__ == "__main__":
    unittest.main()
