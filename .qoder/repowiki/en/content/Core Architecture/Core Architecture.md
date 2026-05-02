# Core Architecture

<cite>
**Referenced Files in This Document**
- [base_hpe.py](file://base_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [main.py](file://main.py)
- [utils/visualizer.py](file://utils/visualizer.py)
- [utils/evaluator.py](file://utils/evaluator.py)
- [optimizations/enhanced_openvino_hpe.py](file://optimizations/enhanced_openvino_hpe.py)
- [optimizations/cpu_performance_optimizer.py](file://optimizations/cpu_performance_optimizer.py)
</cite>

## Update Summary
**Changes Made**
- Updated main_loop_with_timeout method documentation to reflect HTTP stream processing improvements
- Added intelligent frame skipping and concurrent failure handling mechanisms
- Enhanced timeout management and progress reporting for HTTP streams
- Updated architecture diagrams to show improved HTTP stream processing flow

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
This document describes the core architecture of the Human Pose Estimation (HPE) framework. It focuses on the abstract BaseHPE class design pattern that enables polymorphic behavior across different HPE implementations, the unified interface that allows switching between AlphaPose, OpenPose, HigherHRNet, EfficientHRNet, and MoveNet methods, and the modular design that separates model-specific logic from common functionality. It also documents the evaluation and visualization utilities and their role in the overall architecture.

**Updated** The framework now features significantly enhanced HTTP stream processing capabilities with intelligent frame skipping, timeout management, and concurrent failure handling mechanisms.

## Project Structure
The HPE framework is organized around a shared base class and multiple specialized implementations. The main entry point selects the desired method and orchestrates the processing loop. Utilities provide visualization and evaluation outputs.

```mermaid
graph TB
subgraph "Entry Point"
MAIN["main.py"]
end
subgraph "Core Abstractions"
BASE["base_hpe.BaseHPE"]
VIS["utils.visualizer.render"]
EVAL["utils.evaluator (JSON/CSV/Tx)"]
end
subgraph "Implementations"
OVB["openvino_base_hpe.OpenVINOBaseHPE"]
MOV["movenet_hpe.MoveNetHPE"]
ALP["alphapose_hpe.AlphaPoseHPE"]
OVB_OPT["optimizations.enhanced_openvino_hpe.OptimizedOpenVINOHPE"]
end
subgraph "Optimizations"
CPU["optimizations.cpu_performance_optimizer.EPICCPUOptimizer"]
end
MAIN --> OVB
MAIN --> MOV
MAIN --> ALP
OVB --> BASE
MOV --> BASE
ALP --> BASE
OVB_OPT --> OVB
OVB_OPT --> CPU
BASE --> VIS
BASE --> EVAL
```

**Diagram sources**
- [main.py:22-99](file://main.py#L22-L99)
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)
- [openvino_base_hpe.py:55-395](file://openvino_base_hpe.py#L55-L395)
- [movenet_hpe.py:12-111](file://movenet_hpe.py#L12-L111)
- [alphapose_hpe.py:33-334](file://alphapose_hpe.py#L33-L334)
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)
- [optimizations/enhanced_openvino_hpe.py:25-333](file://optimizations/enhanced_openvino_hpe.py#L25-L333)
- [optimizations/cpu_performance_optimizer.py:34-539](file://optimizations/cpu_performance_optimizer.py#L34-L539)

**Section sources**
- [main.py:22-99](file://main.py#L22-L99)
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)

## Core Components
- BaseHPE: An abstract base class that defines the unified interface for all HPE implementations. It encapsulates common input handling, preprocessing, inference orchestration, postprocessing, visualization, and evaluation. It also manages hardware acceleration paths (PyNvCodec vs. OpenCV) and timing metrics.
- OpenVINOBaseHPE: A concrete implementation that integrates with OpenVINO's model API and pipelines. It supports multiple architectures (OpenPose, HigherHRNet, EfficientHRNet variants) and exposes configurable performance settings.
- MoveNetHPE: A lightweight implementation leveraging OpenVINO for MoveNet multipose models with a fixed input size.
- AlphaPoseHPE: A PyTorch-based implementation integrating AlphaPose's detector and pose estimation components, with GPU acceleration and optional multiprocessing.
- OptimizedOpenVINOHPE: An extension of OpenVINOBaseHPE that applies CPU-specific optimizations for high-core-count systems, including NUMA-aware configuration and workload-specific tuning.
- EPICCPUOptimizer: A utility that detects CPU capabilities and calculates optimal OpenVINO configurations for throughput or latency modes.
- Utilities:
  - visualizer.render: Draws skeletons and optional bounding boxes and scores onto frames.
  - evaluator: Aggregates pose results into COCO-compatible JSON/CSV and computes transmitted data volume metrics.

**Section sources**
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)
- [openvino_base_hpe.py:55-395](file://openvino_base_hpe.py#L55-L395)
- [movenet_hpe.py:12-111](file://movenet_hpe.py#L12-L111)
- [alphapose_hpe.py:33-334](file://alphapose_hpe.py#L33-L334)
- [optimizations/enhanced_openvino_hpe.py:25-333](file://optimizations/enhanced_openvino_hpe.py#L25-L333)
- [optimizations/cpu_performance_optimizer.py:34-539](file://optimizations/cpu_performance_optimizer.py#L34-L539)
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)

## Architecture Overview
The framework follows a layered design:
- Entry point (main.py) selects the HPE method and constructs the appropriate implementation.
- Each implementation inherits from BaseHPE and overrides model-specific methods (load_model, run_model, postprocess).
- BaseHPE centralizes:
  - Input source detection (image, directory, video, HTTP stream, webcam).
  - Hardware acceleration selection (PyNvCodec GPU decoding or OpenCV CPU decoding).
  - Preprocessing (padding and resizing) and postprocessing (keypoint scaling and bounding box computation).
  - Inference orchestration and timing.
  - Visualization and evaluation outputs.

**Updated** The main_loop_with_timeout method now provides sophisticated HTTP stream processing with intelligent frame skipping, timeout management, and concurrent failure handling.

```mermaid
classDiagram
class BaseHPE {
+input_type
+output_dir
+main_loop()
+main_loop_with_timeout(timeout, max_frames)
+process_frame(frame, frame_number)
+pad_and_resize(frame)
+set_padding()
<<abstract>>
}
class OpenVINOBaseHPE {
+model_type
+load_model()
+run_model(padded)
+postprocess(predictions)
+main_loop()
}
class OptimizedOpenVINOHPE {
+load_model()
+_configure_core(core)
+get_performance_stats()
}
class MoveNetHPE {
+load_model()
+run_model(padded)
+postprocess(predictions)
}
class AlphaPoseHPE {
+load_model()
+run_model(frame_input)
+postprocess(predictions)
+set_padding()
+pad_and_resize(frame)
}
class EPICCPUOptimizer {
+configure_openvino_core(core)
+optimize_system_settings()
+get_recommended_batch_size(model, resolution)
}
class Visualizer {
+render(frame, bodies, LINES_BODY, score_thresh, show_scores, show_bounding_box)
}
class Evaluator {
+append_COCO_format_json(...)
+append_COCO_format_csv(...)
+save_COCO_format_json(...)
+save_COCO_format_csv(...)
+save_Tx_csv_data(...)
}
BaseHPE <|-- OpenVINOBaseHPE
OpenVINOBaseHPE <|-- OptimizedOpenVINOHPE
BaseHPE <|-- MoveNetHPE
BaseHPE <|-- AlphaPoseHPE
OptimizedOpenVINOHPE --> EPICCPUOptimizer : "uses"
BaseHPE --> Visualizer : "uses"
BaseHPE --> Evaluator : "uses"
```

**Diagram sources**
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)
- [openvino_base_hpe.py:55-395](file://openvino_base_hpe.py#L55-L395)
- [movenet_hpe.py:12-111](file://movenet_hpe.py#L12-L111)
- [alphapose_hpe.py:33-334](file://alphapose_hpe.py#L33-L334)
- [optimizations/enhanced_openvino_hpe.py:25-333](file://optimizations/enhanced_openvino_hpe.py#L25-L333)
- [optimizations/cpu_performance_optimizer.py:34-539](file://optimizations/cpu_performance_optimizer.py#L34-L539)
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)

## Detailed Component Analysis

### BaseHPE: Abstract Design Pattern and Polymorphism
BaseHPE defines a common contract for all HPE implementations:
- Unified constructor parameters for input source, output configuration, and visualization toggles.
- Input detection logic supporting images, directories, videos, HTTP streams, and webcams.
- Hardware acceleration paths:
  - PyNvCodec GPU decoding with NV12 to RGB conversion and tensor conversion.
  - OpenCV CPU decoding with configurable backend for HTTP streams.
- Centralized preprocessing and postprocessing:
  - Padding and resizing to a target model input size.
  - Postprocessing that converts normalized keypoints to original image coordinates and computes bounding boxes.
- Inference orchestration:
  - process_frame measures inference time, draws FPS, and renders results.
  - Supports both dictionary outputs (PAFs/heatmaps) and direct pose arrays.
- Evaluation and visualization:
  - Aggregates COCO-format results and writes JSON/CSV.
  - Renders skeletons and optional bounding boxes and scores.

**Updated** The main_loop_with_timeout method now provides comprehensive HTTP stream processing with intelligent frame skipping, timeout management, and concurrent failure handling.

Polymorphism is achieved by requiring subclasses to implement:
- load_model: Model initialization and adapter creation.
- run_model: Preprocess, run inference, and return predictions.
- postprocess: Convert raw outputs to standardized Body objects.

```mermaid
sequenceDiagram
participant Main as "main.py"
participant Impl as "Concrete HPE (OpenVINOBaseHPE/MoveNetHPE/AlphaPoseHPE)"
participant Base as "BaseHPE"
participant Utils as "Visualizer/Evaluator"
Main->>Impl : construct with args
Main->>Impl : load_model()
Impl->>Base : BaseHPE.__init__(...)
Base->>Base : detect input type<br/>initialize capture/decoders
Main->>Base : main_loop()/main_loop_with_timeout()
loop frames
Base->>Base : process_frame(frame, frame_number)
Base->>Impl : run_model(padded)
Impl-->>Base : predictions
Base->>Base : postprocess(predictions)
Base->>Utils : render(frame, bodies, ...)
Base->>Utils : append_COCO_format_*(...)
end
Base->>Utils : save_* outputs
```

**Diagram sources**
- [main.py:22-99](file://main.py#L22-L99)
- [base_hpe.py:240-630](file://base_hpe.py#L240-L630)
- [openvino_base_hpe.py:183-276](file://openvino_base_hpe.py#L183-L276)
- [movenet_hpe.py:58-111](file://movenet_hpe.py#L58-L111)
- [alphapose_hpe.py:69-294](file://alphapose_hpe.py#L69-L294)
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:35-114](file://utils/evaluator.py#L35-L114)

**Section sources**
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)

### Enhanced HTTP Stream Processing in main_loop_with_timeout
**New Section** The main_loop_with_timeout method provides sophisticated HTTP stream processing capabilities:

#### Intelligent Frame Skipping
- **Frame Detection**: Scans the incoming data buffer for complete JPEG frames using SOI (Start of Image) and EOI (End of Image) markers.
- **Multiple Frame Handling**: Identifies and processes only the most recent complete frame when multiple frames are present in the buffer.
- **Skip Reporting**: Logs the number of skipped frames to inform users about stream lag.

#### Concurrent Failure Handling
- **Failure Counting**: Tracks consecutive decode failures with a configurable maximum threshold.
- **Graceful Degradation**: Stops processing gracefully after reaching the failure threshold.
- **Buffer Management**: Removes processed frame data from the buffer to prevent memory accumulation.

#### Timeout and Frame Limit Management
- **Dynamic Termination**: Monitors both timeout duration and maximum frame count simultaneously.
- **Progress Tracking**: Provides periodic progress updates during HTTP stream processing.
- **Resource Cleanup**: Ensures CSV and JSON files are properly saved even on early termination.

```mermaid
flowchart TD
HTTP_Start([HTTP Stream Processing]) --> BufferInit["Initialize Buffer & State"]
BufferInit --> ReadLoop["Read Available Data Loop"]
ReadLoop --> FindFrames["Find Complete Frames in Buffer"]
FindFrames --> HasFrames{"Frames Found?"}
HasFrames --> |Yes| ProcessLast["Process Only Last Frame"]
HasFrames --> |No| CheckTimeout["Check Timeout/Max Frames"]
ProcessLast --> DecodeFrame["Decode JPEG Frame"]
DecodeFrame --> DecodeSuccess{"Decode Success?"}
DecodeSuccess --> |Yes| UpdateState["Update State & Reset Failures"]
DecodeSuccess --> |No| IncFailures["Increment Failure Counter"]
IncFailures --> CheckFailures{"Failures >= Max?"}
CheckFailures --> |Yes| StopProcessing["Stop Processing"]
CheckFailures --> |No| Sleep["Small Sleep"]
UpdateState --> CheckTimeout
Sleep --> ReadLoop
CheckTimeout --> TimeoutReached{"Timeout/Max Frames Reached?"}
TimeoutReached --> |Yes| SaveResults["Save Results & Exit"]
TimeoutReached --> |No| ReadLoop
SaveResults --> HTTP_End([Processing Complete])
```

**Diagram sources**
- [base_hpe.py:317-481](file://base_hpe.py#L317-L481)

**Section sources**
- [base_hpe.py:317-481](file://base_hpe.py#L317-L481)

### OpenVINOBaseHPE: Unified Interface for OpenVINO Models
OpenVINOBaseHPE provides a unified interface for OpenVINO-based models:
- Model registry with input sizes and architecture types for OpenPose, HigherHRNet, and EfficientHRNet variants.
- Device selection with GPU support checks and fallback to CPU.
- OpenVINO core configuration with performance hints, threading, CPU pinning, and hyper-threading controls.
- Preprocess/postprocess integration with ImageModel and adapter APIs.
- Streaming URL handling with dynamic capture initialization and fallbacks.

```mermaid
flowchart TD
Start([OpenVINOBaseHPE.load_model]) --> ReadXML["Read XML/weights"]
ReadXML --> ConfigureCore["Configure OpenVINO core<br/>threads/streams/performance"]
ConfigureCore --> CreateAdapter["Create OpenVINO adapter"]
CreateAdapter --> CreateModel["Create ImageModel with config"]
CreateModel --> LoadModel["Load model"]
LoadModel --> End([Ready for inference])
```

**Diagram sources**
- [openvino_base_hpe.py:183-260](file://openvino_base_hpe.py#L183-L260)

**Section sources**
- [openvino_base_hpe.py:55-395](file://openvino_base_hpe.py#L55-L395)

### MoveNetHPE: Lightweight OpenVINO Implementation
MoveNetHPE targets MoveNet multipose models:
- Fixed input size (256x256) and GPU fallback to CPU.
- Minimal preprocessing pipeline converting to RGB and NHWC layout.
- Postprocess extracts keypoints, bounding boxes, and scores, scaling to original image coordinates.

```mermaid
sequenceDiagram
participant MV as "MoveNetHPE"
participant OV as "OpenVINO Core"
MV->>MV : load_model()
MV->>OV : read_model(xml)
MV->>OV : compile_model(device)
MV->>MV : run_model(padded)
MV->>MV : postprocess(predictions)
MV-->>MV : bodies (Body[])
```

**Diagram sources**
- [movenet_hpe.py:58-111](file://movenet_hpe.py#L58-L111)

**Section sources**
- [movenet_hpe.py:12-111](file://movenet_hpe.py#L12-L111)

### AlphaPoseHPE: PyTorch-Based Implementation
AlphaPoseHPE integrates AlphaPose's detector and pose estimation:
- Loads detector and pose models from the AlphaPose ecosystem.
- Handles image/directory inputs via a dedicated loader and video/webcam inputs via BaseHPE.
- Performs GPU-accelerated detection and pose estimation with optional flipping and heatmap-to-coordinate conversion.
- Overrides padding/resizing to preserve original resolution.

```mermaid
flowchart TD
AP_Start([AlphaPoseHPE.load_model]) --> LoadDet["Load detector model"]
LoadDet --> LoadPose["Load pose model weights"]
LoadPose --> SetupTrans["Setup transforms"]
SetupTrans --> AP_End([Ready for inference])
AP_Run([run_model]) --> DetPath{"Image/dir?"}
DetPath --> |Yes| UseDetLoader["Use DetectionLoader"]
DetPath --> |No| GPUPath["Use GPU tensor path"]
UseDetLoader --> PoseEst["Pose estimation"]
GPUPath --> PoseEst
PoseEst --> AP_Post([postprocess])
```

**Diagram sources**
- [alphapose_hpe.py:69-334](file://alphapose_hpe.py#L69-L334)

**Section sources**
- [alphapose_hpe.py:33-334](file://alphapose_hpe.py#L33-L334)

### OptimizedOpenVINOHPE and EPICCPUOptimizer: CPU Performance Tuning
OptimizedOpenVINOHPE extends OpenVINOBaseHPE with CPU-specific optimizations:
- Detects CPU capabilities and calculates optimal thread counts, streams, and performance hints.
- Applies NUMA-aware configuration and workload-specific tuning.
- Provides factory functions and benchmark utilities.

```mermaid
classDiagram
class OptimizedOpenVINOHPE {
+load_model()
+_configure_core(core)
+get_performance_stats()
}
class EPICCPUOptimizer {
+configure_openvino_core(core)
+optimize_system_settings()
+get_recommended_batch_size(model, resolution)
}
OptimizedOpenVINOHPE --> EPICCPUOptimizer : "uses"
```

**Diagram sources**
- [optimizations/enhanced_openvino_hpe.py:25-333](file://optimizations/enhanced_openvino_hpe.py#L25-L333)
- [optimizations/cpu_performance_optimizer.py:34-539](file://optimizations/cpu_performance_optimizer.py#L34-L539)

**Section sources**
- [optimizations/enhanced_openvino_hpe.py:25-333](file://optimizations/enhanced_openvino_hpe.py#L25-L333)
- [optimizations/cpu_performance_optimizer.py:34-539](file://optimizations/cpu_performance_optimizer.py#L34-L539)

### Visualization and Evaluation Utilities
- visualizer.render: Draws skeleton lines and keypoint circles, optionally showing scores and bounding boxes.
- evaluator: Aggregates results into COCO-format JSON/CSV and computes transmitted data volume per millisecond interval.

```mermaid
flowchart TD
Bodies["Bodies (list of Body)"] --> COCO["create_COCO_format(...)"]
COCO --> AppendJSON["append_COCO_format_json(...)"]
COCO --> AppendCSV["append_COCO_format_csv(...)"]
AppendCSV --> Tx["append_Tx_csv_data(...)"]
AppendJSON --> SaveJSON["save_COCO_format_json(...)"]
AppendCSV --> SaveCSV["save_COCO_format_csv(...)"]
Tx --> SaveTx["save_Tx_csv_data(...)"]
```

**Diagram sources**
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)

**Section sources**
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)

## Dependency Analysis
The framework exhibits clean separation of concerns:
- Entry point depends on concrete implementations and utilities.
- Implementations depend on BaseHPE and model-specific libraries.
- Optimizations depend on OpenVINOBaseHPE and CPU capability detection.
- Utilities are standalone and consumed by BaseHPE.

```mermaid
graph LR
MAIN["main.py"] --> OVB["openvino_base_hpe.py"]
MAIN --> MOV["movenet_hpe.py"]
MAIN --> ALP["alphapose_hpe.py"]
OVB --> BASE["base_hpe.py"]
MOV --> BASE
ALP --> BASE
OVB_OPT["enhanced_openvino_hpe.py"] --> OVB
OVB_OPT --> CPU["cpu_performance_optimizer.py"]
BASE --> VIS["utils/visualizer.py"]
BASE --> EVAL["utils/evaluator.py"]
```

**Diagram sources**
- [main.py:22-99](file://main.py#L22-L99)
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)
- [openvino_base_hpe.py:55-395](file://openvino_base_hpe.py#L55-L395)
- [movenet_hpe.py:12-111](file://movenet_hpe.py#L12-L111)
- [alphapose_hpe.py:33-334](file://alphapose_hpe.py#L33-L334)
- [optimizations/enhanced_openvino_hpe.py:25-333](file://optimizations/enhanced_openvino_hpe.py#L25-L333)
- [optimizations/cpu_performance_optimizer.py:34-539](file://optimizations/cpu_performance_optimizer.py#L34-L539)
- [utils/visualizer.py:4-49](file://utils/visualizer.py#L4-L49)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)

**Section sources**
- [main.py:22-99](file://main.py#L22-L99)
- [base_hpe.py:36-630](file://base_hpe.py#L36-L630)

## Performance Considerations
- Hardware acceleration:
  - PyNvCodec GPU decoding reduces CPU overhead for video streams and files.
  - OpenCV fallback ensures broad compatibility when GPU decoding is unavailable.
- OpenVINO tuning:
  - Performance hints (LATENCY/THROUGHPUT), thread counts, and streams can be configured via environment variables or constructor parameters.
  - OptimizedOpenVINOHPE automatically selects optimal settings for EPIC-class CPUs.
- Throughput vs. latency:
  - Higher thread counts and multiple streams improve throughput but may increase latency.
  - For real-time applications, LATENCY mode with fewer streams often yields better responsiveness.
- Batch sizing:
  - EPICCPUOptimizer estimates batch sizes considering memory and CPU constraints.
- **Updated** HTTP stream optimization:
  - Intelligent frame skipping prevents buffer overflow and maintains real-time performance.
  - Concurrent failure handling ensures graceful degradation under network instability.
  - Timeout management prevents resource leaks during long-running streams.

## Troubleshooting Guide
- PyNvCodec not available:
  - The framework falls back to OpenCV and prints warnings. Verify GPU drivers and PyNvCodec installation.
- Unsupported input types:
  - Ensure input paths are images, videos, or HTTP streams. Webcam indices must be numeric.
- Streaming URL issues:
  - Use FFmpeg backend for HTTP streams. Some URLs require buffering adjustments.
- GPU device selection:
  - MoveNet does not support GPU; the implementation forces CPU fallback.
  - OpenVINO models may fall back to CPU if GPU is unsupported.
- **Updated** HTTP stream processing issues:
  - Frame skipping messages indicate stream lag; adjust camera settings or network bandwidth.
  - Consecutive failure errors suggest network instability; check connection quality.
  - Timeout errors indicate processing limitations; adjust timeout or max_frames parameters.
  - Buffer overflow warnings indicate insufficient processing capacity; reduce input resolution or increase timeout.

**Section sources**
- [base_hpe.py:97-189](file://base_hpe.py#L97-L189)
- [openvino_base_hpe.py:87-90](file://openvino_base_hpe.py#L87-L90)
- [movenet_hpe.py:28-31](file://movenet_hpe.py#L28-L31)
- [main.py:30-45](file://main.py#L30-L45)

## Conclusion
The HPE framework achieves a clean, extensible architecture through the BaseHPE abstraction and a unified interface across diverse implementations. By separating model-specific logic from common functionality—preprocessing, inference orchestration, postprocessing, visualization, and evaluation—the system supports easy addition of new methods and deployment flexibility across CPU and GPU environments. Optimizations tailored for high-core-count systems further enhance performance, enabling practical real-time deployments.

**Updated** The enhanced HTTP stream processing capabilities with intelligent frame skipping, timeout management, and concurrent failure handling make the framework more robust for production deployments involving network-based video sources. These improvements ensure reliable operation under various network conditions while maintaining real-time performance characteristics essential for practical HPE applications.