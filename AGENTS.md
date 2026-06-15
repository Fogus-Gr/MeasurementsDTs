# AGENTS.md — MeasurementsDTs

Agent guidance for working in this repository.

## Project Overview

2D Human Pose Estimation (HPE) benchmark suite. Runs multiple HPE backends
(AlphaPose, MoveNet, OpenPose, HigherHRNet, EfficientHRNet) against image,
video, directory, webcam, and IP-stream inputs. Outputs annotated frames and
keypoint data in COCO-format JSON/CSV. Designed for Digital Twin measurement
research.

**Stack:** Python 3.8.10 · OpenVINO 2024.2.0 · PyTorch 2.4.1+cu121 · OpenCV

## Repository Layout

```
main.py                  # CLI entry point — argument parsing + method dispatch
base_hpe.py              # Abstract base class (BaseHPE) + Body/Padding types
openvino_base_hpe.py     # OpenVINO backend (OpenPose, HigherHRNet, EfficientHRNet)
movenet_hpe.py           # MoveNet backend (OpenVINO runtime, CPU only)
alphapose_hpe.py         # AlphaPose backend (PyTorch + YOLO detector)
utils/
  export_pose_results.py # COCO JSON/CSV serialisation + Tx bandwidth measurement
  visualizer.py          # OpenCV skeleton/keypoint rendering
models/
  AlphaPose/             # AlphaPose source + Cython extensions (built via setup.py)
  MoveNet/               # OpenVINO IR model files (not committed — see README)
  OpenVINO/              # OpenVINO model_api + IR model files (not committed)
dev_tools/
  stream_video_server.py # Flask MJPEG server for local IP-stream testing
unit_tests/
  images/                # Sample images for manual smoke tests
  video/                 # Sample GIF for video/stream tests
```

## Architecture

`BaseHPE` (abstract) handles input routing, the main loop, padding/resize,
frame dispatch, and output saving. Concrete subclasses implement three methods:

| Method | Responsibility |
|---|---|
| `load_model()` | Load weights and compile inference graph |
| `run_model(padded)` | Run inference, return raw predictions |
| `postprocess(predictions)` | Convert raw output to `List[Body]` |

`AlphaPoseHPE` overrides `set_padding` and `pad_and_resize` because AlphaPose
handles its own preprocessing internally.

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
4. Document required model files in `README.md` under "Required Pretrained Models".

### Model Files
Model weights are **not committed**. They are listed in `.gitignore` and must
be downloaded manually (see README). Never commit `.bin`, `.pth`, or `.weights`
files.

### Output Files
All output goes to `out/` by default (also gitignored). Do not hardcode other
output paths.

### Current Project Gaps
- `unit_tests/` currently contains sample media only; there are no automated
  tests yet. Prefer small `unittest` smoke tests before adding new test
  dependencies.
- There is no linter / formatter config and no CI workflow. Match local style
  instead of introducing broad formatting churn.
- `.devcontainer/devcontainer.json` exists, but it is not a complete
  dependency setup for this project.
- `requirements.txt` is currently pip-style but README setup uses
  `conda install --file requirements.txt`; verify installer changes carefully
  and keep README, requirements files, and AGENTS.md aligned.

### Known Issues and TODOs
- `movenet_hpe.py`: keypoint-level score filtering not yet applied to body
  score (marked `# TODO`).
- `alphapose_hpe.py`: batch parallelism for directory input not implemented;
  bounding box is derived from keypoints, not from the detector.
- `visualizer.py`: keypoint colouring logic is only verified correct for
  MoveNet (marked `# TODO`).
- `openvino_base_hpe.py → run_model`: `results` variable may be unbound if
  `raw_result` is falsy — needs a guard.
- `utils/export_pose_results.py`: `reset_results()` exists but is not called
  before each run, so module-level accumulators can leak state across multiple
  runs in one process.
- `alphapose_hpe.py → postprocess`: `Body` keypoint arrays should preserve all
  17 COCO joints so downstream rendering/export can index consistently.

## Running the Project

```bash
# Single image
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image

# Directory of images
python3 main.py --method alphapose --input unit_tests/images/ --json

# Video file
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video

# IP stream (start server first in another terminal)
python3 dev_tools/stream_video_server.py
python3 main.py --method movenet --input http://<your-ip>:8080/video_feed --save_video
```

## Environment Setup

Requires a Conda environment for the documented GPU-capable setup. The
devcontainer does **not** install all dependencies automatically.

```bash
conda create -n hpe python=3.8.10 -y
conda activate hpe
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch
conda install --file requirements.txt
bash models/AlphaPose/build_extensions.sh   # builds Cython NMS extension
```

GPU inference requires CUDA 12.x and an NVIDIA driver. MoveNet and HigherHRNet
fall back to CPU automatically.

## Commit Style

Follow the existing log pattern: imperative subject line, body explains *what*
and *why* (not *how*). Examples from history:

```
Add option to measure the produced data volume per time period
Resize/Pad input images based on the base model used
```

Keep commits focused on one logical change.
