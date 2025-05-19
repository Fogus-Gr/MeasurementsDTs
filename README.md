# 2D Human Pose Estimation

This project provides baseline implementations for three 2D Human Pose Estimation methods: **AlphaPose**, **OpenPose** and **MoveNet**.

## Dependencies

- Ubuntu 20.04
- Python 3.8.10
- OpenVINO 2024.2.0

### Additional Packages
opencv-python==4.10.0.84
numpy==1.24.4
torch==2.4.1
torchvision==0.19.1
scipy==1.10.1
matplotlib==3.7.5
tqdm==4.67.0
PyYAML==6.0.2
Cython==3.0.11

##  Getting Started

Clone the repository and make sure to download the required pre-trained models below.

### Required Pretrained Models

Download these required model files and place them in the specified locations:

1. **AlphaPose Models**:
   - fast_res50_256x192.pth (ResNet50 weights):
     ```bash
     wget "https://drive.google.com/uc?export=download&id=1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI" -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth
     ```
   - yolov3-spp.weights (YOLOv3 detector):
     ```bash
     wget "https://drive.google.com/uc?export=download&id=1k-9cUGcdH5ZFN1NcMvZrO0ApW241tboD" -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights
     ```

2. **MoveNet Model**:
   - movenet_multipose_lightning_256x256_FP32.bin (OpenVINO binaries):
     ```bash
     wget "https://drive.google.com/uc?export=download&id=15SZwY2jAh1KqHwT-YO6_UByOsQD70RSr" -O models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin
     ```

### Executing program

* Example usage with the sample image
```
# For MoveNet
python3 main.py --method movenet --input images/testImage.jpg --save_image

# For AlphaPose
python3 main.py --method alphapose --input images/testImage.jpg --save_image
```
