# 2D Human Pose Estimation

Benchmark suite for 2D Human Pose Estimation methods used in Digital Twin
measurement experiments. The CLI can run AlphaPose, MoveNet, OpenPose,
HigherHRNet, and EfficientHRNet on images, directories, videos, webcams, and
HTTP video streams.

## Dependencies

- Ubuntu 20.04
- Python 3.8.10
- OpenVINO 2024.4.0
- PyTorch 2.4.1
- OpenCV 4.10.0

### GPU and Drivers

The known working GPU setup uses an NVIDIA GPU, CUDA 12.x, and PyTorch 2.4.1.
MoveNet and HigherHRNet fall back to CPU automatically.

## Installation

Create and activate the Conda environment:

```bash
conda create -n hpe python=3.8.10 -y
conda activate hpe
```

If `conda activate hpe` fails before Conda is initialized, run:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate hpe
```

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

For CUDA-backed PyTorch, install the PyTorch build that matches your driver
before running the project. The current environment uses PyTorch 2.4.1 with a
CUDA 12.x runtime.

Build the AlphaPose Cython/CUDA extensions:

```bash
bash models/AlphaPose/build_extensions.sh
```

## Required Model Files

Model weights are not committed. Download them after installing `gdown` from
`requirements.txt`.

Create the target directories first:

```bash
mkdir -p models/AlphaPose/pretrained_models
mkdir -p models/AlphaPose/detector/yolo/data
mkdir -p models/MoveNet
mkdir -p models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001
mkdir -p models/OpenVINO/pretrained_models/intel/human-pose-estimation-0005/FP32
mkdir -p models/OpenVINO/pretrained_models/intel/human-pose-estimation-0006/FP32
mkdir -p models/OpenVINO/pretrained_models/intel/human-pose-estimation-0007/FP32
mkdir -p models/OpenVINO/pretrained_models/public/FP32
```

### AlphaPose

AlphaPose requires the ResNet50 pose checkpoint, YOLOv3 detector weights, and
the config file at
`models/AlphaPose/pretrained_models/256x192_res50_lr1e-3_1x.yaml`.

```bash
gdown "https://drive.google.com/uc?id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" \
  -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth

gdown "https://drive.google.com/uc?id=1D47msNOOiJKvPOXlnpyzdKA3k6E97NTC" \
  -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights
```

### MoveNet

The code loads `models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml`.
Keep the matching `.bin` file in the same directory.

```bash
gdown "https://drive.google.com/uc?id=15SZwY2jAh1KqHwT-YO6_UByOsQD70RSr" \
  -O models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin
```

### OpenPose

The code loads
`models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001/human-pose-estimation-0001.xml`.
Keep the matching `.bin` file in the same directory.

```bash
gdown "https://drive.google.com/uc?id=1VNucIyIsdaiw1cYt-JGqBWloVu2TVdsm" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0001/human-pose-estimation-0001.bin
```

### HigherHRNet

The code loads
`models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.xml`.
Keep the matching `.bin` file in the same directory.

```bash
gdown "https://drive.google.com/uc?id=1fko47eVczJZQb9wWA2X7eQ0TuF4PDXzs" \
  -O models/OpenVINO/pretrained_models/public/FP32/higher-hrnet-w32-human-pose-estimation.bin
```

### EfficientHRNet

The `ae1`, `ae2`, and `ae3` methods load the XML files from
`models/OpenVINO/pretrained_models/intel/...`. Place the matching FP32 `.bin`
files next to those XML files:

```bash
gdown "https://drive.google.com/uc?id=1lEUFqQnWHVymQoZvaXuDFcnOyEEKsexP" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0005/FP32/human-pose-estimation-0005.bin

gdown "https://drive.google.com/uc?id=1d8pGQrM9vEfz_oAIey0qRr7Gxp6dS2UE" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0006/FP32/human-pose-estimation-0006.bin

gdown "https://drive.google.com/uc?id=1ZSdsqgD4zUO4gyHMYBfxq3m4UMyQ187j" \
  -O models/OpenVINO/pretrained_models/intel/human-pose-estimation-0007/FP32/human-pose-estimation-0007.bin
```

If you already have the Open Model Zoo public layout, the same `.bin` files may
exist under `models/OpenVINO/pretrained_models/public/human-pose-estimation-*`.
They are compatible with the XML files used by this branch.

## Running

Show all CLI options:

```bash
python3 main.py --help
```

Run MoveNet on one image:

```bash
python3 main.py --method movenet --input unit_tests/images/testImage.jpg --save_image
```

Run AlphaPose on a directory and export COCO JSON:

```bash
python3 main.py --method alphapose --input unit_tests/images/ --json
```

Run EfficientHRNet1 on a video:

```bash
python3 main.py --method ae1 --input unit_tests/video/giphy.gif --save_video
```

Run on a webcam:

```bash
python3 main.py --method movenet --input 0 --save_video
```

Outputs are written to `out/` by default. Use `--output_dir` to choose another
directory.

## Developer Utilities

`dev_tools/stream_video_server.py` starts a local Flask MJPEG stream for testing
HTTP video input.

In one terminal:

```bash
python3 dev_tools/stream_video_server.py
```

In another terminal, replace `<your-ip>` with the output of `hostname -I`:

```bash
python3 main.py --method movenet --input http://<your-ip>:8080/video_feed --save_video
```
