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

    def test_openpose_and_hrnet_use_original_frame_for_model_api_preprocess(self):
        source = (ROOT / "openvino_base_hpe.py").read_text()

        self.assertIn(
            'if self.model_type in ("openpose", "higherhrnet") and hasattr(self, "_current_frame"):',
            source,
        )
        self.assertIn("model_input = self._current_frame", source)
        self.assertIn("model_input = padded", source)
        self.assertIn("self.model.preprocess(model_input)", source)
        self.assertIn("def process_frame(self, frame, frame_number):", source)
        self.assertIn(
            "self._current_frame = frame.cpu().numpy() if isinstance(frame, torch.Tensor) else frame",
            source,
        )
        self.assertIn("self._current_frame = None", source)

    def test_openpose_and_hrnet_skip_extra_padded_coordinate_rescale(self):
        source = (ROOT / "openvino_base_hpe.py").read_text()
        postprocess = source[source.index("def postprocess(self, predictions):"):source.index("def main_loop(self):")]

        self.assertIn('if self.model_type not in ("openpose", "higherhrnet"):', postprocess)
        self.assertIn("keypoints_xy_orig[:, 0] *= (unpadded_w / self.pd_w)", postprocess)
        self.assertIn("keypoints_xy_orig[:, 1] *= (unpadded_h / self.pd_h)", postprocess)

    def test_timeout_loop_uses_opencv_capture_before_http_fallback(self):
        source = (ROOT / "base_hpe.py").read_text()
        timeout_loop = source[source.index("def main_loop_with_timeout"):source.index("def process_frame")]

        self.assertIn("elif self.cap is not None:", timeout_loop)
        self.assertIn("self.cap.read()", timeout_loop)
        self.assertLess(timeout_loop.index("self.cap.read()"), timeout_loop.index("requests.get"))

    def test_timeout_zero_is_unlimited_in_timeout_loop(self):
        source = (ROOT / "base_hpe.py").read_text()
        timeout_loop = source[source.index("def main_loop_with_timeout"):source.index("def process_frame")]

        self.assertIn(
            "if timeout_seconds > 0 and time.time() - start_time > timeout_seconds:",
            timeout_loop,
        )
        self.assertNotIn(
            "if time.time() - start_time > timeout_seconds:",
            timeout_loop,
        )

    def test_main_routes_local_video_max_frames_to_timeout_loop(self):
        source = (ROOT / "main.py").read_text()

        self.assertIn("if args.timeout > 0 or args.max_frames > 0:", source)
        self.assertIn("hpe.main_loop_with_timeout(args.timeout, args.max_frames)", source)


if __name__ == "__main__":
    unittest.main()
