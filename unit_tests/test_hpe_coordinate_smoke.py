import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import cv2


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_IMAGE = REPO_ROOT / "unit_tests" / "images" / "testImage.jpg"
OUTPUT_ROOT = REPO_ROOT / "out" / "coordinate_smoke"

METHODS = ("openpose", "hrnet", "ae1", "ae2", "ae3", "alphapose", "movenet")

# Baseline from testImage.jpg on perf-tuning-base. These are intentionally
# minimums so small model-confidence drift does not fail the test unless a model
# stops detecting the expected people for this smoke image.
MIN_DETECTIONS = {
    "openpose": 5,
    "hrnet": 5,
    "ae1": 3,
    "ae2": 4,
    "ae3": 5,
    "alphapose": 5,
    "movenet": 5,
}

# A single person should not cover most of this image. This catches giant boxes
# caused by coordinate projection regressions without depending on exact boxes.
MAX_VISIBLE_BBOX_AREA_RATIO = 0.40


def _selected_methods():
    selected = os.environ.get("HPE_SMOKE_METHODS")
    if not selected:
        return METHODS

    methods = tuple(method.strip().lower() for method in selected.split(",") if method.strip())
    unknown = sorted(set(methods) - set(METHODS))
    if unknown:
        raise ValueError("Unknown HPE_SMOKE_METHODS entries: %s" % ", ".join(unknown))
    return methods


def _visible_points(keypoints):
    points = []
    for index in range(0, len(keypoints), 3):
        x = float(keypoints[index])
        y = float(keypoints[index + 1])
        visibility = float(keypoints[index + 2])
        if visibility > 1:
            points.append((x, y))
    return points


class HPECoordinateSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image = cv2.imread(str(INPUT_IMAGE))
        if image is None:
            raise RuntimeError("Could not read smoke input image: %s" % INPUT_IMAGE)
        cls.image_h, cls.image_w = image.shape[:2]
        cls.image_area = cls.image_w * cls.image_h

    def test_model_outputs_stay_in_image_coordinates(self):
        timeout = int(os.environ.get("HPE_SMOKE_TIMEOUT", "180"))

        for method in _selected_methods():
            with self.subTest(method=method):
                output_dir = OUTPUT_ROOT / method
                if output_dir.exists():
                    shutil.rmtree(str(output_dir))
                output_dir.mkdir(parents=True)

                command = [
                    sys.executable,
                    "main.py",
                    "--method", method,
                    "--input", str(INPUT_IMAGE),
                    "--device", "CPU",
                    "--save_image",
                    "--json",
                    "--output_dir", str(output_dir),
                ]
                result = subprocess.run(
                    command,
                    cwd=str(REPO_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=timeout,
                )

                self.assertEqual(
                    result.returncode,
                    0,
                    "Command failed for %s:\n%s" % (method, result.stdout),
                )

                json_path = output_dir / "COCOformat.json"
                image_path = output_dir / "frame_0000.jpg"
                self.assertTrue(json_path.exists(), "Missing JSON output for %s" % method)
                self.assertTrue(image_path.exists(), "Missing rendered image for %s" % method)

                with json_path.open("r") as json_file:
                    detections = json.load(json_file)

                self.assertGreaterEqual(
                    len(detections),
                    MIN_DETECTIONS[method],
                    "%s produced too few detections. Output:\n%s" % (method, result.stdout),
                )

                out_of_bounds = []
                max_visible_bbox_area = 0.0
                for det_index, detection in enumerate(detections):
                    keypoints = detection.get("keypoints", [])
                    self.assertEqual(
                        len(keypoints) % 3,
                        0,
                        "%s detection %d has malformed keypoints" % (method, det_index),
                    )

                    visible = _visible_points(keypoints)
                    if not visible:
                        continue

                    xs = [point[0] for point in visible]
                    ys = [point[1] for point in visible]
                    max_visible_bbox_area = max(
                        max_visible_bbox_area,
                        (max(xs) - min(xs)) * (max(ys) - min(ys)),
                    )

                    for point_index, (x, y) in enumerate(visible):
                        if x < 0 or x > self.image_w or y < 0 or y > self.image_h:
                            out_of_bounds.append((det_index, point_index, x, y))

                self.assertFalse(
                    out_of_bounds,
                    "%s produced out-of-bounds visible keypoints: %s" % (method, out_of_bounds),
                )
                self.assertLessEqual(
                    max_visible_bbox_area,
                    self.image_area * MAX_VISIBLE_BBOX_AREA_RATIO,
                    "%s produced a suspiciously large visible-keypoint bbox: %.1f" % (
                        method,
                        max_visible_bbox_area,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
