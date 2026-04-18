# AGENTS.md — MeasurementsDTs (evaluation branch)

Agent guidance for working in this repository.

## Project Overview

2D Human Pose Estimation (HPE) benchmark suite with an accuracy evaluation
framework. Runs multiple HPE backends (AlphaPose, MoveNet, OpenPose,
HigherHRNet, EfficientHRNet) against image, video, directory, webcam, and
IP-stream inputs. Outputs annotated frames and keypoint data in COCO-format
JSON/CSV. The `evaluation` branch adds offline accuracy measurement (PCK, AUC,
OKS, AP/AR) against Panoptic Studio ground-truth data.

**Stack:** Python 3.8.10 · OpenVINO 2024.2.0 · PyTorch 2.4.1+cu121 · OpenCV

---

## Repository Layout

```
main.py                        # HPE CLI entry point
evaluate.py                    # Evaluation CLI entry point
base_hpe.py                    # Abstract HPE base class
openvino_base_hpe.py           # OpenVINO backend (OpenPose, HigherHRNet, EfficientHRNet)
movenet_hpe.py                 # MoveNet backend (OpenVINO runtime, CPU only)
alphapose_hpe.py               # AlphaPose backend (PyTorch + YOLO detector)
utils/
  body.py                      # Body dataclass (moved here from base_hpe.py)
  constants.py                 # COCO visibility flags + CATEGORY_PERSON
  export_pose_results.py       # COCO JSON/CSV serialisation + Tx bandwidth measurement
  visualizer.py                # OpenCV skeleton/keypoint rendering
  accuracyEvaluation/
    base_evaluator.py          # Abstract evaluator: loading, frame loop, matching, rendering
    auc_evaluator.py           # AUC-PCK evaluator
    apar_evaluator.py          # AP/AR evaluator (COCO-style)
    matching.py                # IoU and keypoint-distance matching strategies
    keypointsDataset.py        # JSON loader + frame-indexed lookup
    metrics/
      pck.py                   # PCK metric + draw_curve()
      oks.py                   # OKS metric
    2DprojectionPanopticRecordings.py  # Offline tool: project Panoptic 3D GT → COCO 2D
models/
  AlphaPose/                   # AlphaPose source + Cython extensions
  MoveNet/                     # OpenVINO IR model files (not committed)
  OpenVINO/                    # OpenVINO model_api + IR model files (not committed)
dev_tools/
  stream_video_server.py       # Flask MJPEG server for local IP-stream testing
unit_tests/
  images/                      # Sample images for manual smoke tests
  video/                       # Sample GIF for video/stream tests
  video2sec/                   # 2-second clip + GT + pre-computed predictions for eval tests
  test_pck.py                  # PCK unit tests (pytest)
  test_oks.py                  # OKS unit tests + golden tests
  test_matching.py             # Matcher unit tests
  test_auc_integration.py      # AUC integration tests (golden)
  test_apar_integration.py     # AP/AR integration tests (golden)
```

---

## Architecture

### HPE Pipeline

`BaseHPE` (abstract) handles input routing, the main loop, padding/resize,
frame dispatch, and output saving. Concrete subclasses implement:

| Method | Responsibility |
|---|---|
| `load_model()` | Load weights and compile inference graph |
| `run_model(padded)` | Run inference, return raw predictions |
| `postprocess(predictions)` | Convert raw output to `List[Body]` |

`AlphaPoseHPE` overrides `set_padding` and `pad_and_resize` — AlphaPose
handles its own preprocessing internally.

### Evaluation Pipeline

`BaseEvaluator` (abstract) handles JSON loading (`KeypointsDataset`), video
frame iteration, GT/prediction alignment, body format conversion, matching, and
rendering. Concrete subclasses implement:

| Method | Responsibility |
|---|---|
| `evaluate_frame(bodies)` | Compute per-frame metric, return `{method: value}` |
| `print_results(frame_number, results)` | Verbose per-frame logging |

The two concrete evaluators:

| Class | Metric | Entry point |
|---|---|---|
| `AUCEvaluator` | PCK swept over thresholds → AUC | `evaluator.AUC()` |
| `APAREvaluator` | OKS-based AP/AR (COCO-style) | `evaluator.APAR()` |

### Body dataclass (`utils/body.py`)

`Body` carries both HPE output fields and evaluation state fields:

```
score, xmin/ymin/xmax/ymax, keypoints, keypoints_norm, keypoints_score
# evaluation fields (set during eval, None otherwise):
correctness, included_in_denominator   # PCK
oks, matched                           # OKS/AP
thresh_radius                          # PCK visualisation
```

Do not add HPE-specific logic to `Body`. Keep it a plain data container.

### Ground-Truth Format

GT JSON files follow COCO annotation structure with extra fields:
- `frame_number` — Panoptic frame index (not video frame index)
- `fpsType` — `"hd_29_97"` (only supported value currently)
- `keypoints` — flat `[x, y, v, ...]` array, 17 joints, COCO order

`KeypointsDataset` indexes entries by `frame_number` for O(1) lookup.
`BaseEvaluator.adjust_frame_number` converts video frame numbers to GT frame
numbers using `gt_fps / video_fps * frame + frame_offset`.

---

## Development Conventions

### Code Style
- Python 3.8 compatible — no walrus operator, no `match` statements.
- No type annotations currently in use; do not add them unless the whole file
  is being refactored.
- 4-space indentation. Match the surrounding file's style exactly.
- Module-level globals in `export_pose_results.py` are intentional (accumulator
  pattern); do not refactor to a class without discussing first.

### Adding a New HPE Backend
1. Subclass `BaseHPE` in a new file `<name>_hpe.py`.
2. Implement `load_model`, `run_model`, `postprocess`, and define `LINES_BODY`.
3. Register the method name in `main.py` → `method_map` and `argparse choices`.
4. Document required model files in `README.md`.

### Adding a New Metric
1. Create `utils/accuracyEvaluation/metrics/<name>.py` with an `<Name>Evaluator`
   class exposing an `evaluate(gt_body, pred_body)` method.
2. Create or extend an evaluator in `utils/accuracyEvaluation/` that subclasses
   `BaseEvaluator` and implements `evaluate_frame` and `print_results`.
3. Register the method in `evaluate.py` → `get_accuracy_method` and `argparse choices`.
4. Add unit tests in `unit_tests/test_<name>.py`.

### Matching
Two strategies are available in `Matcher` (`matching.py`):
- `iou` — bounding-box IoU ≥ threshold (default 0.3). Requires ≥ 4 common
  visible keypoints.
- `keypoint` — mean normalised Euclidean distance < threshold (default 0.05).

Each GT body is matched to at most one prediction (greedy, GT-first). COCO
sorts predictions by confidence before matching; this implementation does not —
see known issues below.

### Model Files
Model weights are **not committed**. Listed in `.gitignore`. Never commit
`.bin`, `.pth`, or `.weights` files.

### Output Files
All HPE output goes to `out/` by default (gitignored). Evaluation output
(images, CSVs) should also target `out/`.

### Known Issues / TODOs
- `matching.py`: predictions are not sorted by confidence before matching
  (diverges from COCO spec — noted in module docstring).
- `apar_evaluator.py → evaluate_frame`: returns `oks_score` from the last
  iteration of the inner loop, not a meaningful per-frame aggregate.
- `base_evaluator.py → run_evaluation`: returns `mean_dict` (mean per method
  over all frames) but `APAREvaluator` ignores this return value — `APAR()`
  calls `run_evaluation()` only for its side-effects on `self.all_detections`.
- `keypointsDataset.py`: only `"hd_29_97"` FPS type is handled; others call
  `exit(1)` instead of raising an exception.
- `2DprojectionPanopticRecordings.py`: hardcodes `data_path` and `selected_cam`
  — not usable without manual edits.
- `openvino_base_hpe.py → run_model`: `results` may be unbound if `raw_result`
  is falsy (inherited from `main` branch).
- `export_pose_results.py`: global accumulator never reset between runs
  (inherited from `main` branch).

---

## Running the Project

### HPE inference
```bash
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image
python3 main.py --method alphapose --input unit_tests/images/ --json
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video
```

### Evaluation
```bash
# AUC-PCK
python3 evaluate.py \
  --method auc \
  --gt_file unit_tests/video2sec/all_body2DScenes_499_540.json \
  --pd_files unit_tests/video2sec/pd_movenet.json \
  --input_video unit_tests/video2sec/160422_ultimatum_hd_00_00_2s.mp4 \
  --start_threshold 0.0 --stop_threshold 0.5 --step_threshold 0.05

# AP/AR
python3 evaluate.py \
  --method apar \
  --gt_file unit_tests/video2sec/all_body2DScenes_499_540.json \
  --pd_files unit_tests/video2sec/pd_movenet.json unit_tests/video2sec/pd_alphapose.json \
  --input_video unit_tests/video2sec/160422_ultimatum_hd_00_00_2s.mp4

# Debug mode (no arguments — runs a hardcoded AUC test case)
python3 evaluate.py
```

### Tests
```bash
python3 -m pytest unit_tests/ -v
```

### IP stream dev tool
```bash
python3 dev_tools/stream_video_server.py
python3 main.py --method movenet --input http://<your-ip>:8080/video_feed --save_video
```

---

## Environment Setup

Requires a Conda environment — the devcontainer does **not** install
dependencies automatically.

```bash
conda create -n hpe python=3.8.10 -y
conda activate hpe
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch
conda install --file requirements.txt
bash models/AlphaPose/build_extensions.sh
```

GPU inference requires CUDA 12.x and an NVIDIA driver. MoveNet and HigherHRNet
fall back to CPU automatically.

---

## Commit Style

Imperative subject line; body explains *what* and *why*. Examples from history:

```
Implement AP-AR and relevant integration tests
Fix visibility and FP logic
Refactor: Move body structure to a separate file
```

Keep commits focused on one logical change.
