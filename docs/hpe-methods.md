# HPE Methods — Deep Dive

> **Newcomer?** Unfamiliar with terms like *HPE*, *keypoint*, *COCO format*, *OpenVINO*, *backend*, or *padding*? Check the [Glossary in ONBOARDING.md](../ONBOARDING.md#appendix-a-glossary) before reading further.

## Overview
Detailed reference for all Human Pose Estimation methods, their architectures, model files, and configuration.

## Class Hierarchy

```
BaseHPE (abc.ABC) — base_hpe.py (546 lines)
│
├── AlphaPoseHPE — alphapose_hpe.py (334 lines)
│   Architecture: Two-stage (YOLO detector + ResNet pose estimator)
│   Device: CPU/GPU (default GPU)
│
├── MoveNetHPE — movenet_hpe.py (111 lines)
│   Architecture: Single-stage bottom-up (OpenVINO)
│   Device: CPU only (GPU flag forces CPU fallback)
│
└── OpenVINOBaseHPE — openvino_base_hpe.py (653 lines)
    Architecture: Configurable OpenVINO models
    ├── openpose (456x256) — GPU/CPU
    ├── efficienthrnet1 (288x288, ae1) — GPU/CPU
    ├── efficienthrnet2 (352x352, ae2) — GPU/CPU
    ├── efficienthrnet3 (448x448, ae3) — GPU/CPU
    └── higherhrnet (512x512, hrnet) — CPU only
```

## BaseHPE Abstract Class

### Core Attributes
- `input_type`: "image" | "directory" | "video" | "webcam"
- `cap`: OpenCV VideoCapture (fallback path)
- `demuxer`, `decoder`: PyNvCodec (GPU-accelerated decode path)
- `is_pynvcodec_enabled`: Boolean — GPU decode available?
- `processing_times`: Deque of last 200 inference times (for FPS calc)
- `measurement_interval_ms`: Data volume measurement granularity (default 100ms)
- `padding`: Named tuple (w, h, padded_w, padded_h)

### Input Type Detection
1. Starts with "http" → video stream (tries PyNvCodec, falls back to OpenCV)
2. Ends with .mp4/.avi/.mov → video file
3. Ends with .jpg/.png → single image
4. isdigit() → webcam index
5. isdir() → directory of images

### Video Processing Paths
**PyNvCodec (GPU decode)**:
- DecodeSingleFrame() → GPU surface (NV12)
- RGB conversion → RGB surface
- Tensor conversion → PyTorch GPU tensor
- Pass to process_frame()

**OpenCV (CPU fallback)**:
- cap.read() → NumPy array (BGR)
- Pass to process_frame()

### Frame Processing Pipeline
1. Convert frame to NumPy if tensor
2. Pad and resize to model input dimensions
3. Run model (timed)
4. Postprocess predictions → Body objects
5. Calculate FPS from last 200 times
6. Draw FPS overlay
7. Append to CSV/JSON if enabled
8. Draw keypoints/skeleton if save_image/save_video

### Padding Calculation
- Compares image aspect ratio to model input ratio
- Adds padding to right/bottom only (simplifies depadding)
- `set_padding()` calculates once, reused per frame

### Abstract Methods (subclasses must implement)
- `load_model()` — Load weights and compile model
- `run_model(padded_frame)` — Single-frame inference
- `postprocess(predictions)` — Convert raw output to Body objects

## AlphaPose (alphapose_hpe.py)

### Architecture
**Two-stage top-down approach**:
1. **Stage 1: Person Detection** (YOLO v3-SPP)
   - Detect bounding boxes around people
   - Batch process detections (configurable batch size)
2. **Stage 2: Pose Estimation** (ResNet-50 backbone, 256x192)
   - Extract person ROI from each detection
   - Estimate 17 COCO keypoints per person
   - Heatmap → coordinate conversion

### Device Selection
- `DEVICE_TO_GPU = {"GPU": "0", "CPU": "-1"}`
- Default: GPU
- Multi-GPU: scales batch sizes by GPU count

### Model Files
- Config: `models/AlphaPose/pretrained_models/256x192_res50_lr1e-3_1x.yaml`
- Checkpoint: `models/AlphaPose/pretrained_models/fast_res50_256x192.pth`
- YOLO weights: `models/AlphaPose/detector/yolo/data/yolov3-spp.weights`

### Model Loading
1. Load YAML config
2. Initialize YOLO detector
3. Build pose model (SPPE architecture from config)
4. Load pretrained checkpoint
5. Set to eval mode
6. Initialize image transform (Normalize: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])

### Inference (run_model)
For video/webcam:
1. Convert frame to GPU tensor
2. Resize to 608x608 (YOLO input)
3. Detect people: `detector_model.images_detection()`
4. Filter human class (idx == 0)
5. For each detection: GPU crop → resize to 256x192 → normalize
6. Stack crops into batch → pose_model inference
7. Convert heatmaps to coordinates

### Postprocess
Per detected person:
- Extract normalized keypoints (x, y) ∈ [0, 1]
- Extract confidence scores
- Filter by score threshold
- Create Body object with bbox, keypoints, scores

## MoveNet (movenet_hpe.py)

### Architecture
**Single-stage bottom-up multi-pose** (MoveNet Lightning):
- Input: 256x256 RGB
- Output: Up to 6 people, 17 keypoints each
- Runs on OpenVINO inference engine

### Device Selection
- Forces CPU regardless of --device flag (GPU not supported for this model)

### Model Files
- XML: `models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml`
- BIN: `models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin`

### Model Loading
1. Create OpenVINO Core
2. Read model from XML
3. Get input tensor info (input_blob name, shape)
4. Get output tensor name: "Identity"
5. Compile model for CPU

### Inference (run_model)
1. BGR → RGB conversion
2. Transpose HWC → CHW
3. Cast to float32, add batch dimension
4. OpenVINO infer

### Postprocess
Output shape: 6x56 per image
Per person (up to 6):
- Keypoints: first 51 values → reshape to (17, 3) → x, y, score
- Bbox: values 51-54 (normalized)
- Overall score: value 55
- Swap x/y coordinates, denormalize to pixel coords
- Create Body object if score > threshold

## OpenVINO Models (openvino_base_hpe.py)

### Model Variants

| CLI Name | Model | Input Size | Architecture | GPU Support |
|----------|-------|-----------|--------------|-------------|
| openpose | human-pose-estimation-0001 | 456x256 | OpenPose (PAFs + heatmaps) | Yes |
| ae1 | human-pose-estimation-0005 | 288x288 | Associative embedding | Yes |
| ae2 | human-pose-estimation-0006 | 352x352 | Associative embedding | Yes |
| ae3 | human-pose-estimation-0007 | 448x448 | Associative embedding | Yes |
| hrnet | higher-hrnet-w32 | 512x512 | Associative embedding | No (CPU only) |

### Model File Paths
```
models/OpenVINO/pretrained_models/
├── intel/
│   ├── human-pose-estimation-0001/human-pose-estimation-0001.xml  (openpose)
│   ├── human-pose-estimation-0006/FP32/human-pose-estimation-0006.xml  (ae2)
│   └── human-pose-estimation-0007/FP32/human-pose-estimation-0007.xml  (ae3)
└── public/
    ├── human-pose-estimation-0005/FP32/human-pose-estimation-0005.xml  (ae1)
    └── FP32/higher-hrnet-w32-human-pose-estimation.xml  (hrnet)
```

### Performance Tuning (Environment Variables)
| Variable | Default | Description |
|----------|---------|-------------|
| OV_THREADS | 1 | Inference thread count |
| OV_MODE | latency | latency or throughput |
| OV_STREAMS | (auto) | Number of inference streams |
| OV_CPU_PINNING | false | Bind threads to CPU cores |
| OV_HYPER_THREADING | false | Enable hyper-threading |

### Core Configuration
The `_configure_core()` method sets OpenVINO performance hints:
- Performance mode hint (latency/throughput)
- CPU thread count
- CPU pinning (bind threads to specific cores)
- Hyper-threading toggle
- Stream count for parallelism

## Body Class (Output Format)

```python
class Body:
    score: float                  # Global body confidence (0-1)
    xmin, ymin, xmax, ymax: int  # Bounding box in pixels
    keypoints_score: ndarray      # Per-keypoint confidence (17,)
    keypoints: ndarray            # Per-keypoint pixel coords (17, 2)
    keypoints_norm: ndarray       # Per-keypoint normalized coords (17, 2) ∈ [0,1]
```

### 17 COCO Keypoints
```
0: nose          1: left_eye      2: right_eye
3: left_ear      4: right_ear     5: left_shoulder
6: right_shoulder 7: left_elbow   8: right_elbow
9: left_wrist    10: right_wrist  11: left_hip
12: right_hip    13: left_knee    14: right_knee
15: left_ankle   16: right_ankle
```

## CSV Output Formats

### Keypoint CSV (`{timestamp}_{method}_{input}_JSON.csv`)
| Column | Type | Description |
|--------|------|-------------|
| frame_number | int | Sequential frame ID |
| timestamp | float | Unix timestamp (seconds.ms) |
| json_output | string | COCO format JSON (serialized) |

### COCO JSON Format (within each row)
```json
[{
    "image_id": 42,
    "category_id": 1,
    "keypoints": [x1, y1, v1, x2, y2, v2, ...],  // 51 values (17*3)
    "score": 0.85
}]
```
Visibility: 0=not labeled, 1=labeled not visible, 2=labeled visible

### Data Volume CSV (`{timestamp}_{method}_{input}_Tx.csv`)
| Column | Type | Description |
|--------|------|-------------|
| msecond | float | Time interval (seconds) |
| json_bytes | int | Total JSON output bytes in interval |

## Method Selection Guide

| Use Case | Method | Why |
|----------|--------|-----|
| Fastest inference | movenet | Single-stage, lightweight |
| Best accuracy (GPU) | alphapose | Two-stage, ResNet backbone |
| Good CPU performance | ae1/ae2/ae3 | OpenVINO optimized |
| Multi-person (no GPU) | hrnet | HigherHRNet, CPU only |
| Balanced GPU | openpose | OpenVINO with GPU support |

## CLI Reference

```bash
python3 main.py --method <METHOD> --input <SOURCE> [OPTIONS]

Required:
  --method    openpose|alphapose|movenet|hrnet|ae1|ae2|ae3

Input:
  --input     Path/URL/webcam index (default: 0)

Output:
  --output_dir        Output directory
  --json              Export COCO JSON
  --csv               Export COCO CSV
  --save_video        Encode output video
  --save_image        Save annotated frames

Device:
  --device    CPU|GPU (default: GPU for alphapose/openpose, CPU for others)

Tuning:
  --detbatch                Detection batch size (AlphaPose only, default: 5)
  --measurement_interval_ms Data volume interval (default: 100)
  --timeout                 HTTP stream timeout seconds (default: 300)
  --max_frames              Max frames to process (default: 0 = unlimited)
```
