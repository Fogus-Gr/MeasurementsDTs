# 2D Human Pose Estimation Evaluation Framework

This project branch provides a comprehensive evaluation framework for 2D Human Pose Estimation (HPE) methods.

The framework evaluates model accuracy using two primary methods:
* **AUC:** Area Under the Curve (PCK - Probability of Correct Keypoints).
* **APAR:** Average Precision and Recall (Standard COCO metrics).

## 🚀 Workflow

To benchmark a model, follow this pipeline:
1.  **Prepare Ground Truth:** Convert CMU Panoptic 3D data to 2D COCO-format JSONs.
2.  **Get Predictions:** Run your HPE model (e.g., MoveNet) on the video to generate prediction JSONs.
3.  **Evaluate:** Compare the Predictions against the Ground Truth using this tool.

---

## 1. Preparing Ground Truth (3D to 2D Projection)

Since datasets like CMU Panoptic provide **3D** annotations, they must be projected into **2D** image coordinates to serve as ground truth for 2D HPE methods.

We provide a panoptic_to_coco utility script (`utils/accuracyEvaluation/2DprojectionPanopticRecordings.py`) that:
1.  Reads the 3D Skeleton data and Camera Calibration files.
2.  Projects points using camera intrinsics/distortion parameters.
3.  Converts the skeleton format to **COCO 17-Keypoint format**.

### Usage
**Note:** Before running, open the script and update the `CONFIG` section with your local paths:
```python
# === CONFIG ===
data_path = "/mnt/data/panoptic-toolbox/scripts/171204_pose1"
calib_file = os.path.join(data_path, "calibration_171204_pose1.json")
input_3d_path = os.path.join(data_path, "hdPose3d_stage1_coco19")
### Executing program
```

**Run the conversion:**
```bash
# Generates a single JSON file containing all frames (recommended for evaluation)
python3 utils/panoptic_to_coco.py

# Generates one JSON file per frame
python3 utils/panoptic_to_coco.py --mode multiple
```
*Output will be saved in `projected_2d/`.*

---

## 2. Running Evaluation

Once you have your Ground Truth JSON (from step 1) and your Prediction JSONs (from your model), you can run the evaluation.

### Basic Command Structure
```bash
python3 evaluate.py --method [auc|apar] --gt_file [PATH] --pd_files [PATH] --input_video [PATH]
```

### Examples

#### 1. APAR Evaluation (mAP / mAR)
Calculates Average Precision and Recall, similar to standard COCO evaluation.
```bash
python3 evaluate.py \
  --method apar \
  --gt_file unit_tests/video2sec/all_body2DScenes_499_540.json \
  --pd_files unit_tests/video2sec/pd_movenet.json \
  --input_video unit_tests/video2sec/160422_ultimatum_hd_00_00_2s.mp4 \
  --frame_offset 499
```

#### 2. AUC Evaluation (PCK) with Rendering
Calculates Probability of Correct Keypoints and renders the result images to an output folder.
```bash
python3 evaluate.py \
  --method auc \
  --gt_file unit_tests/video2sec/all_body2DScenes_499_540.json \
  --pd_files unit_tests/video2sec/pd_movenet.json \
  --input_video unit_tests/video2sec/160422_ultimatum_hd_00_00_2s.mp4 \
  --frame_offset 499 \
  --render
```

#### 3. Comparing Multiple Models
You can pass multiple prediction files to compare them in one run.
```bash
python3 evaluate.py --method apar \
  --gt_file data/ground_truth.json \
  --pd_files results/movenet.json results/alphapose.json results/openpose.json \
  --input_video data/video.mp4
```

---

## ⚙️ Configuration Options

| Argument | Required | Description |
| :--- | :---: | :--- |
| `--method` | ✅ | Evaluation metric: `auc` or `apar`. |
| `--gt_file` | ✅ | Path to the Ground Truth JSON (from Step 1). |
| `--pd_files` | ✅ | List of prediction JSON files to evaluate. |
| `--input_video` | ✅ | Path to the original video file. |
| `--frame_offset` | | Frame synchronization offset (if GT starts at frame 0 but video starts later). |
| `--render` | | If set, renders output images with overlaid keypoints. |
| `--matching` | | Matching strategy: `iou` (default) or `keypoint`. |
| `--confidence_threshold`| | Filter predictions below this confidence (AUC only). |
| `--frame` | | Evaluate a specific single frame index. |
| `--verbose`, `-v` | | Print detailed logs. |

---

### Development
To run the internal debug test case (no arguments):
```bash
python3 evaluate.py
```