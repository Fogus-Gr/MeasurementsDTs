# MoveNet Implementation

<cite>
**Referenced Files in This Document**
- [movenet_hpe.py](file://movenet_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [base_hpe.py](file://base_hpe.py)
- [visualizer.py](file://utils/visualizer.py)
- [movenet_multipose_lightning_256x256_FP32.xml](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml)
- [movenet_multipose_lightning_256x256_FP32.bin](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin)
</cite>

## Update Summary
**Changes Made**
- Updated confidence scoring mechanism section to reflect the improved approach using mean of 17 per-keypoint confidence scores
- Enhanced postprocessing documentation to explain the new filtering methodology
- Added detailed explanation of the TODO A improvement for more reliable pose filtering

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document explains the MoveNet implementation using OpenVINO, focusing on the multipose Lightning model architecture optimized for edge devices and real-time performance. It covers model loading, input preprocessing (256x256 resolution), output postprocessing for multiple persons, configuration options for device selection and performance tuning, and practical examples for initialization, inference, and result interpretation. Limitations such as GPU support restrictions and optimal deployment scenarios for edge computing are also addressed.

**Updated** The confidence scoring mechanism has been improved to use the mean of 17 per-keypoint confidence scores rather than relying solely on the raw model body score, providing more reliable pose filtering and detection quality assessment.

## Project Structure
The MoveNet implementation is organized around a shared base Human Pose Estimation (HPE) framework and a MoveNet-specific adapter that integrates with OpenVINO. Supporting utilities include a visualizer and a base HPE class that standardizes input handling, padding/resizing, and rendering.

```mermaid
graph TB
subgraph "MoveNet OpenVINO Integration"
A["movenet_hpe.py<br/>MoveNetHPE class"]
B["openvino_base_hpe.py<br/>OpenVINOBaseHPE class"]
C["base_hpe.py<br/>BaseHPE class"]
D["visualizer.py<br/>render()"]
end
subgraph "Model Assets"
E["models/MoveNet/<br/>movenet_multipose_lightning_256x256_FP32.xml"]
F["models/MoveNet/<br/>movenet_multipose_lightning_256x256_FP32.bin"]
end
A --> C
B --> C
A --> E
A --> F
C --> D
```

**Diagram sources**
- [movenet_hpe.py:12-113](file://movenet_hpe.py#L12-L113)
- [openvino_base_hpe.py:55-392](file://openvino_base_hpe.py#L55-L392)
- [base_hpe.py:36-628](file://base_hpe.py#L36-L628)
- [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)
- [movenet_multipose_lightning_256x256_FP32.xml:1-200](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml#L1-L200)
- [movenet_multipose_lightning_256x256_FP32.bin:1-100](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin#L1-L100)

**Section sources**
- [movenet_hpe.py:1-113](file://movenet_hpe.py#L1-L113)
- [openvino_base_hpe.py:55-392](file://openvino_base_hpe.py#L55-L392)
- [base_hpe.py:36-628](file://base_hpe.py#L36-L628)
- [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)
- [movenet_multipose_lightning_256x256_FP32.xml:1-200](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml#L1-L200)
- [movenet_multipose_lightning_256x256_FP32.bin:1-100](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin#L1-L100)

## Core Components
- MoveNetHPE: Implements the MoveNet multipose Lightning model with OpenVINO runtime. Handles device selection (CPU fallback for GPU), model loading, preprocessing, inference, and postprocessing for multiple people. **Updated** Features improved confidence scoring using mean of 17 per-keypoint confidence scores.
- BaseHPE: Provides shared infrastructure for input handling, padding/resizing, timing, saving outputs, and rendering. It defines the common interface for all HPE implementations.
- OpenVINOBaseHPE: A more generic OpenVINO-based HPE class supporting multiple architectures and advanced performance tuning (threads, streams, CPU pinning, hyperthreading).
- visualizer: Renders skeletons and bounding boxes for detected bodies.

Key capabilities:
- Lightweight multipose design enabling detection of multiple persons in a single inference.
- Fixed 256x256 input resolution for the MoveNet model.
- **Enhanced** Threshold-based filtering of detections using improved confidence scoring mechanism.
- Optional async processing pipeline for improved responsiveness.

**Section sources**
- [movenet_hpe.py:12-113](file://movenet_hpe.py#L12-L113)
- [base_hpe.py:36-628](file://base_hpe.py#L36-L628)
- [openvino_base_hpe.py:55-392](file://openvino_base_hpe.py#L55-L392)
- [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)

## Architecture Overview
The MoveNet pipeline follows a standard HPE flow: input acquisition → padding and resizing → inference → postprocessing → visualization and output.

```mermaid
sequenceDiagram
participant User as "User Application"
participant HPE as "MoveNetHPE"
participant OV as "OpenVINO Core"
participant Net as "MoveNet Model"
participant VP as "Video/Stream Source"
User->>HPE : Initialize with device and model path
HPE->>VP : Open video/camera/stream
HPE->>HPE : set_padding() and pad_and_resize()
HPE->>OV : read_model(xml_path)
OV-->>HPE : Compiled model
loop For each frame
HPE->>VP : Read frame
HPE->>HPE : pad_and_resize(frame)
HPE->>OV : infer_new_request({input_blob : tensor})
OV-->>HPE : predictions
HPE->>HPE : postprocess(predictions) with improved confidence scoring
HPE->>User : Bodies with keypoints, scores, and bounding boxes
end
```

**Diagram sources**
- [movenet_hpe.py:58-86](file://movenet_hpe.py#L58-L86)
- [movenet_hpe.py:88-113](file://movenet_hpe.py#L88-L113)
- [base_hpe.py:501-628](file://base_hpe.py#L501-L628)

## Detailed Component Analysis

### MoveNetHPE Class
MoveNetHPE extends BaseHPE and encapsulates MoveNet-specific logic:
- Device handling: Forces CPU if GPU is requested because the MoveNet Lightning model is not supported on GPU.
- Model loading: Reads the IR XML and compiles the model for the selected device.
- Preprocessing: Converts BGR to RGB, transposes to CHW, normalizes, and adds batch dimension.
- Inference: Executes a single request using the compiled model.
- **Enhanced** Postprocessing: Squeezes the Identity output, decodes 17 keypoints per person, bounding boxes, and applies improved confidence scoring using mean of 17 per-keypoint confidence scores.

```mermaid
classDiagram
class BaseHPE {
+score_thresh : float
+pd_w : int
+pd_h : int
+set_padding()
+pad_and_resize(frame)
+main_loop()
+process_frame(frame, frame_number)
}
class MoveNetHPE {
+xml_path : Path
+device : str
+load_model()
+run_model(padded)
+postprocess(predictions)
-_init_opencv_video_capture(input_src)
}
BaseHPE <|-- MoveNetHPE
```

**Diagram sources**
- [base_hpe.py:36-628](file://base_hpe.py#L36-L628)
- [movenet_hpe.py:12-113](file://movenet_hpe.py#L12-L113)

**Section sources**
- [movenet_hpe.py:20-31](file://movenet_hpe.py#L20-L31)
- [movenet_hpe.py:58-86](file://movenet_hpe.py#L58-L86)
- [movenet_hpe.py:88-113](file://movenet_hpe.py#L88-L113)

### Input Preprocessing and Padding
The BaseHPE class ensures consistent preprocessing:
- Determines padding to maintain aspect ratio, adding black borders to bottom or right.
- Resizes to the model's fixed input size (256x256 for MoveNet).
- Provides a unified pad_and_resize method used by MoveNetHPE.

```mermaid
flowchart TD
Start(["Frame Received"]) --> Aspect["Compute aspect ratio"]
Aspect --> Decide{"img_w/img_h > pd_w/pd_h ?"}
Decide --> |Yes| PadH["Pad vertically (bottom)"]
Decide --> |No| PadW["Pad horizontally (right)"]
PadH --> Resize["Resize to 256x256"]
PadW --> Resize
Resize --> End(["Padded Tensor"])
```

**Diagram sources**
- [base_hpe.py:615-628](file://base_hpe.py#L615-L628)

**Section sources**
- [base_hpe.py:615-628](file://base_hpe.py#L615-L628)

### Enhanced Output Postprocessing for Multiple Persons
**Updated** MoveNetHPE postprocessing now features improved confidence scoring:
- Squeezes the Identity output to extract per-person data.
- Decodes 17 keypoints (x, y, score), bounding box (ymin, xmin, ymax, xmax), and a person score.
- **Enhanced** Calculates mean of 17 per-keypoint confidence scores for more reliable pose filtering.
- Applies threshold-based filtering using the improved confidence scoring mechanism.
- Converts normalized coordinates to absolute pixel coordinates and normalizes to image dimensions.

```mermaid
flowchart TD
Start(["Predictions from Identity"]) --> Squeeze["Squeeze to (6 x 56)"]
Squeeze --> Loop{"For each of 6 slots"}
Loop --> Decode["Decode 17 keypoints + bbox + score"]
Decode --> Extract["Extract 17 per-keypoint scores"]
Extract --> MeanCalc["Calculate mean of 17 per-keypoint confidence scores"]
MeanCalc --> Thresh{"mean_kp_score > score_thresh?"}
Thresh --> |No| Skip["Skip person"]
Thresh --> |Yes| Denorm["Denormalize to padded size"]
Denorm --> Abs["Convert to absolute pixels"]
Abs --> Body["Create Body with improved confidence scoring"]
Body --> Collect["Collect bodies"]
Loop --> |Done| Collect
Collect --> End(["List of Bodies with enhanced filtering"])
```

**Diagram sources**
- [movenet_hpe.py:88-113](file://movenet_hpe.py#L88-L113)

**Section sources**
- [movenet_hpe.py:88-113](file://movenet_hpe.py#L88-L113)

### Model Loading and Device Selection
- MoveNetHPE reads the IR XML and compiles the model for the specified device.
- If GPU is requested, it automatically falls back to CPU and prints an informational message.
- The compiled model stores the input and output blob names for inference.

```mermaid
sequenceDiagram
participant App as "Application"
participant HPE as "MoveNetHPE"
participant Core as "OpenVINO Core"
participant Model as "Compiled Model"
App->>HPE : load_model()
HPE->>Core : read_model(xml_path)
Core-->>HPE : Network
HPE->>HPE : Detect input/output blobs
HPE->>Core : compile_model(device)
Core-->>HPE : Model
HPE-->>App : Ready for inference
```

**Diagram sources**
- [movenet_hpe.py:58-82](file://movenet_hpe.py#L58-L82)

**Section sources**
- [movenet_hpe.py:28-30](file://movenet_hpe.py#L28-L30)
- [movenet_hpe.py:58-82](file://movenet_hpe.py#L58-L82)

### Practical Examples

- Initialization and device selection:
  - Instantiate MoveNetHPE with an optional model path and device ("CPU" or "GPU"). GPU requests are automatically converted to CPU.
  - Example instantiation path: [movenet_hpe.py:20](file://movenet_hpe.py#L20)

- Model loading:
  - Call load_model to read the IR and compile for the device.
  - Example call path: [movenet_hpe.py:58](file://movenet_hpe.py#L58)

- Inference execution:
  - Prepare a padded frame using BaseHPE.pad_and_resize.
  - Execute run_model to obtain predictions.
  - Example paths: [base_hpe.py:513-514](file://base_hpe.py#L513-L514), [movenet_hpe.py:83-86](file://movenet_hpe.py#L83-L86)

- **Enhanced** Result interpretation:
  - Use postprocess to decode bodies, keypoints, bounding boxes, and apply improved confidence scoring.
  - Example path: [movenet_hpe.py:88-113](file://movenet_hpe.py#L88-L113)

- Rendering:
  - Visualize skeletons and bounding boxes using the provided render utility.
  - Example path: [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)

**Section sources**
- [movenet_hpe.py:20-26](file://movenet_hpe.py#L20-L26)
- [movenet_hpe.py:58-86](file://movenet_hpe.py#L58-L86)
- [movenet_hpe.py:88-113](file://movenet_hpe.py#L88-L113)
- [base_hpe.py:513-514](file://base_hpe.py#L513-L514)
- [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)

## Dependency Analysis
- MoveNetHPE depends on BaseHPE for input handling, padding, and rendering.
- MoveNetHPE uses OpenVINO runtime to load and run the model.
- The model assets include both XML and BIN files with a fixed 256x256 input shape.

```mermaid
graph TB
MoveNet["MoveNetHPE"]
Base["BaseHPE"]
OV["OpenVINO Runtime"]
XML["movenet_multipose_lightning_256x256_FP32.xml"]
BIN["movenet_multipose_lightning_256x256_FP32.bin"]
MoveNet --> Base
MoveNet --> OV
OV --> XML
OV --> BIN
```

**Diagram sources**
- [movenet_hpe.py:12-113](file://movenet_hpe.py#L12-L113)
- [base_hpe.py:36-628](file://base_hpe.py#L36-L628)
- [movenet_multipose_lightning_256x256_FP32.xml:1-200](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml#L1-L200)
- [movenet_multipose_lightning_256x256_FP32.bin:1-100](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin#L1-L100)

**Section sources**
- [movenet_hpe.py:12-113](file://movenet_hpe.py#L12-L113)
- [base_hpe.py:36-628](file://base_hpe.py#L36-L628)
- [movenet_multipose_lightning_256x256_FP32.xml:1-200](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.xml#L1-L200)
- [movenet_multipose_lightning_256x256_FP32.bin:1-100](file://models/MoveNet/movenet_multipose_lightning_256x256_FP32.bin#L1-L100)

## Performance Considerations
- Fixed input size: The model expects 256x256, which reduces overhead and enables predictable throughput on edge devices.
- Single inference per frame: MoveNet Lightning performs multiperson detection in one pass, balancing speed and accuracy.
- Device fallback: GPU is not supported for this model; CPU fallback ensures compatibility.
- **Enhanced** Threshold tuning: Adjust score_thresh to trade off false positives vs. recall. The improved confidence scoring mechanism provides more reliable filtering.
- Asynchronous processing: While MoveNetHPE focuses on a streamlined pipeline, the broader OpenVINOBaseHPE supports async pipelines with frame buffering and thread pools for improved responsiveness in high-throughput scenarios.

## Troubleshooting Guide
Common issues and resolutions:
- GPU not supported: Requests for GPU are automatically redirected to CPU with an informational message. Use CPU for inference.
  - Reference: [movenet_hpe.py:28-30](file://movenet_hpe.py#L28-L30)

- Model path errors: Ensure the IR XML and BIN files exist at the expected path and match the model name.
  - Reference: [movenet_hpe.py:10](file://movenet_hpe.py#L10)

- **Enhanced** Confidence scoring issues: If detections are being filtered too aggressively, consider lowering the score_thresh value. The improved mean-based confidence scoring provides more reliable pose filtering compared to the previous raw model body score approach.
  - Reference: [movenet_hpe.py:96-98](file://movenet_hpe.py#L96-L98)

- Video capture failures: For HTTP streams, the code uses FFmpeg backend and sets a small buffer to reduce latency. Verify stream accessibility and adjust buffering if needed.
  - Reference: [movenet_hpe.py:39-44](file://movenet_hpe.py#L39-L44)

- Rendering artifacts: Confirm that LINES_BODY is defined and score_thresh is set appropriately to filter weak detections.
  - Reference: [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)

**Section sources**
- [movenet_hpe.py:28-30](file://movenet_hpe.py#L28-L30)
- [movenet_hpe.py:10](file://movenet_hpe.py#L10)
- [movenet_hpe.py:96-98](file://movenet_hpe.py#L96-L98)
- [movenet_hpe.py:39-44](file://movenet_hpe.py#L39-L44)
- [visualizer.py:4-53](file://utils/visualizer.py#L4-L53)

## Conclusion
The MoveNet implementation leverages OpenVINO to deliver a lightweight, multiperson pose estimation solution optimized for edge devices. Its fixed 256x256 input, single-inference design, and CPU-centric deployment simplify real-time operation. **Updated** The recent enhancement to the confidence scoring mechanism using the mean of 17 per-keypoint confidence scores provides more reliable pose filtering and detection quality assessment, addressing the TODO A improvement for better pose filtering reliability. By tuning the score threshold and leveraging the provided preprocessing and postprocessing utilities, developers can integrate robust pose detection into resource-constrained environments. For advanced performance tuning and multi-architecture support, the broader OpenVINOBaseHPE class offers additional configuration options.