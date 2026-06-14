# Data Processing and Analysis

<cite>
**Referenced Files in This Document**
- [main.py](file://main.py)
- [base_hpe.py](file://base_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [video_detection.py](file://utils/video_detection.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)
- [log_parser.py](file://utils/log_parser.py)
- [open_pose.py](file://models/OpenVINO/model_api/models/open_pose.py)
- [coco_det.py](file://models/AlphaPose/alphapose/datasets/coco_det.py)
- [halpe_68_noface.py](file://models/AlphaPose/alphapose/datasets/halpe_68_noface.py)
- [plot_perf_metrics.py](file://Measure_plot_cpu_perf/plot_perf_metrics.py)
- [plot_smi_output.py](file://Measure_gpu_dcgm/plot_smi_output.py)
- [plot_graph.py](file://ffmpeg_hpe/plot_graph.py)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [plot_rx_bytes_trimmed_reset.py](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [run_nvidia_dcgm.sh](file://Measure_gpu_dcgm/run_nvidia_dcgm.sh)
- [run_perf_plot.sh](file://Measure_plot_cpu_perf/run_perf_plot.sh)
- [stream_video_server.py](file://dev_tools/stream_video_server.py)
- [stream_video_server_adaptive.py](file://dev_tools/stream_video_server_adaptive.py)
- [test_hpe_regressions.py](file://tests/test_hpe_regressions.py)
</cite>

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
10. [Appendices](#appendices)

## Introduction
This document describes the data processing and analysis capabilities of the Human Pose Estimation (HPE) system. It covers:
- COCO format export for keypoints and bounding boxes, including JSON/CSV serialization and annotation structures
- Visualization tools for rendering skeletons and keypoint overlays on frames
- Video detection utilities for processing video streams and batch workflows
- Log parsing for performance metrics and experiment results
- Statistical analysis, result aggregation, and export formats
- Evaluation metrics calculation, benchmarking interpretation, and comparative analysis across HPE backends
- Data validation, quality assurance, and result verification procedures

## Project Structure
The repository organizes HPE backends, utilities, and analysis scripts across distinct areas:
- Backends: AlphaPose, OpenVINO, and MobileNet-based HPE implementations
- Utilities: video detection, visualization, evaluation, and log parsing
- Analysis and plotting: CPU/GPU performance plots, network traffic plots, and experiment orchestration
- Dev tools: streaming servers for testing and adaptive streaming
- Tests: regression checks for pose estimation stability

```mermaid
graph TB
subgraph "Backends"
AP["AlphaPose HPE"]
OV["OpenVINO HPE"]
MN["MobileNet HPE"]
end
subgraph "Utilities"
VD["Video Detection Utils"]
VS["Visualizer"]
EV["Evaluator"]
LP["Log Parser"]
end
subgraph "Analysis"
CPUP["CPU Perf Plot"]
GPUP["GPU SMI Plot"]
NETP["Network Rx Plots"]
EXP["Experiment Runner"]
end
subgraph "Dev Tools"
SVR["Stream Server"]
ASVR["Adaptive Stream Server"]
end
AP --> VS
OV --> VS
MN --> VS
AP --> EV
OV --> EV
MN --> EV
VD --> EV
LP --> EV
EXP --> AP
EXP --> OV
EXP --> MN
CPUP --> EXP
GPUP --> EXP
NETP --> EXP
SVR --> VD
ASVR --> VD
```

**Section sources**
- [main.py](file://main.py)
- [base_hpe.py](file://base_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [video_detection.py](file://utils/video_detection.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)
- [log_parser.py](file://utils/log_parser.py)
- [plot_perf_metrics.py](file://Measure_plot_cpu_perf/plot_perf_metrics.py)
- [plot_smi_output.py](file://Measure_gpu_dcgm/plot_smi_output.py)
- [plot_graph.py](file://ffmpeg_hpe/plot_graph.py)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [plot_rx_bytes_trimmed_reset.py](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [run_nvidia_dcgm.sh](file://Measure_gpu_dcgm/run_nvidia_dcgm.sh)
- [run_perf_plot.sh](file://Measure_plot_cpu_perf/run_perf_plot.sh)
- [stream_video_server.py](file://dev_tools/stream_video_server.py)
- [stream_video_server_adaptive.py](file://dev_tools/stream_video_server_adaptive.py)

## Core Components
- Backend HPE implementations:
  - AlphaPose HPE: end-to-end pipeline with detector and pose model
  - OpenVINO HPE: optimized inference pipeline with COCO conversion
  - MobileNet HPE: lightweight inference for mobile targets
- Video detection utilities: frame processing, batching, and stream handling
- Visualization: skeleton rendering and keypoint overlay on frames
- Evaluation: metrics computation and result aggregation
- Log parsing: extraction of performance and experiment metadata
- Analysis and plotting: CPU/GPU metrics and network traffic visualization
- Streaming servers: local RTSP-like servers for testing

**Section sources**
- [base_hpe.py](file://base_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [video_detection.py](file://utils/video_detection.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)
- [log_parser.py](file://utils/log_parser.py)

## Architecture Overview
The system integrates backend HPE models with a unified processing pipeline. Data flows from input sources (files, streams) through detection/postprocessing, visualization, and evaluation, with optional export to COCO JSON/CSV.

```mermaid
sequenceDiagram
participant SRC as "Input Source"
participant DET as "Detector"
participant POSE as "Pose Model"
participant PP as "Postprocess"
participant VIS as "Visualizer"
participant EVAL as "Evaluator"
participant OUT as "Export"
SRC->>DET : "Frame(s)"
DET->>POSE : "Detected ROIs"
POSE->>PP : "Keypoints + Scores"
PP->>VIS : "Skeleton + Keypoints"
VIS->>EVAL : "Aggregated Metrics"
EVAL->>OUT : "COCO JSON/CSV"
```

**Diagram sources**
- [base_hpe.py](file://base_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)

## Detailed Component Analysis

### COCO Export and Annotation Structures
- AlphaPose dataset utilities define COCO-compatible structures for detection and whole-body annotations, including bounding boxes and keypoints.
- OpenVINO HPE converts internal pose entries to COCO format with standardized joint ordering and confidence scores.
- Export formats:
  - JSON: COCO-style annotations with images, annotations, categories, and keypoints arrays
  - CSV: tabular representation of per-person keypoints and bounding boxes

Implementation highlights:
- COCO detection dataset loader and keypoint handling
- OpenVINO pose conversion to COCO format with reordering and confidence scaling
- Aggregation of per-frame results into COCO dataset structure

```mermaid
flowchart TD
Start(["Start Frame"]) --> Detect["Run Detector"]
Detect --> Extract["Extract Keypoints + Scores"]
Extract --> Convert["Convert to COCO Format"]
Convert --> Validate["Validate Annotations"]
Validate --> Aggregate["Aggregate to Dataset"]
Aggregate --> ExportJSON["Export COCO JSON"]
Aggregate --> ExportCSV["Export COCO CSV"]
ExportJSON --> End(["Done"])
ExportCSV --> End
```

**Diagram sources**
- [coco_det.py](file://models/AlphaPose/alphapose/datasets/coco_det.py)
- [halpe_68_noface.py](file://models/AlphaPose/alphapose/datasets/halpe_68_noface.py)
- [open_pose.py](file://models/OpenVINO/model_api/models/open_pose.py)

**Section sources**
- [coco_det.py](file://models/AlphaPose/alphapose/datasets/coco_det.py)
- [halpe_68_noface.py](file://models/AlphaPose/alphapose/datasets/halpe_68_noface.py)
- [open_pose.py](file://models/OpenVINO/model_api/models/open_pose.py)

### Visualization Tools: Skeletons and Keypoint Overlays
- Visualizer renders skeletons and keypoint overlays on frames, enabling quick inspection of pose outputs.
- Integration points:
  - Base HPE class invokes visualization during processing loops
  - Backend-specific postprocessors supply keypoints and scores

```mermaid
sequenceDiagram
participant LOOP as "Main Loop"
participant PROC as "Postprocess"
participant VIS as "Visualizer"
participant DISP as "Display/Save"
LOOP->>PROC : "predictions"
PROC->>VIS : "keypoints, scores"
VIS->>DISP : "frame with overlays"
DISP-->>LOOP : "processed frame"
```

**Diagram sources**
- [base_hpe.py](file://base_hpe.py)
- [visualizer.py](file://utils/visualizer.py)

**Section sources**
- [base_hpe.py](file://base_hpe.py)
- [visualizer.py](file://utils/visualizer.py)

### Video Detection Utilities: Streams and Batch Workflows
- Unified video detection utilities handle initialization, frame processing, batching, and loop control.
- Features:
  - Stream vs file input detection
  - Timeout and frame limits
  - Padding/resizing for consistent model input
  - Batch processing and async pipelines (backend-dependent)

```mermaid
flowchart TD
Init(["Init Capture"]) --> Loop{"More Frames?"}
Loop --> |Yes| Read["Read Frame"]
Read --> Pre["Preprocess (Pad/Resize)"]
Pre --> Infer["Run Model"]
Infer --> Post["Postprocess"]
Post --> Loop
Loop --> |No| Done(["Exit"])
```

**Diagram sources**
- [base_hpe.py](file://base_hpe.py)
- [video_detection.py](file://utils/video_detection.py)

**Section sources**
- [base_hpe.py](file://base_hpe.py)
- [video_detection.py](file://utils/video_detection.py)

### Log Parsing and Experiment Results Extraction
- Log parser extracts performance metrics and experiment metadata from structured logs.
- Typical outputs:
  - Throughput, latency, memory usage
  - Backend-specific stats (OpenVINO, AlphaPose)
  - Environment and configuration flags

```mermaid
flowchart TD
LStart(["Log File"]) --> Parse["Parse Lines"]
Parse --> Extract["Extract Metrics"]
Extract --> Normalize["Normalize Units"]
Normalize --> Aggregate["Aggregate Stats"]
Aggregate --> Export["Export CSV/JSON"]
Export --> LEnd(["Results Ready"])
```

**Diagram sources**
- [log_parser.py](file://utils/log_parser.py)

**Section sources**
- [log_parser.py](file://utils/log_parser.py)

### Statistical Analysis, Aggregation, and Export Formats
- Evaluator computes per-frame and aggregate metrics (e.g., PCK, AUC, mAP).
- Aggregation methods:
  - Per-person averages
  - Dataset-wide summaries
  - Confidence thresholds and filtering
- Export formats:
  - CSV for spreadsheets and dashboards
  - JSON for programmatic consumption

```mermaid
flowchart TD
SStart(["Per-Framed Metrics"]) --> Filter["Filter by Thresholds"]
Filter --> Sum["Summarize Per-Person"]
Sum --> DS["Dataset-Wide Stats"]
DS --> Export["Export CSV/JSON"]
Export --> SEnd(["Aggregated Results"])
```

**Diagram sources**
- [evaluator.py](file://utils/evaluator.py)

**Section sources**
- [evaluator.py](file://utils/evaluator.py)

### Evaluation Metrics and Benchmarking Interpretation
- Metrics:
  - Keypoint detection accuracy (PCK, PCKh)
  - Pose grouping quality (person scores)
  - Speed and throughput (frames/sec)
- Benchmarking:
  - Compare backends under identical conditions
  - Interpret trade-offs between accuracy and latency
  - Use aggregated CSV/JSON for comparative analysis

```mermaid
graph LR
MET["Metrics"] --> COMP["Comparative Analysis"]
COMP --> VIS["Dashboards/Charts"]
VIS --> DEC["Actionable Insights"]
```

[No sources needed since this diagram shows conceptual workflow, not actual code structure]

**Section sources**
- [evaluator.py](file://utils/evaluator.py)

### Comparative Analysis Between HPE Backends
- Backends:
  - AlphaPose: flexible, research-grade
  - OpenVINO: optimized inference
  - MobileNet: lightweight
- Comparison criteria:
  - Accuracy (COCO metrics)
  - Latency and throughput
  - Resource usage (CPU/GPU)
  - Ease of deployment

```mermaid
graph TB
A["AlphaPose"] --> CMP["Compare"]
O["OpenVINO"] --> CMP
M["MobileNet"] --> CMP
CMP --> RES["Shared Metrics & Reports"]
```

[No sources needed since this diagram shows conceptual workflow, not actual code structure]

**Section sources**
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)

### Data Validation, Quality Assurance, and Result Verification
- Validation steps:
  - Bounding box sanity checks
  - Keypoint score thresholds
  - Coordinate normalization and clipping
- QA:
  - Regression tests for pose estimation
  - Consistency checks across frames
  - Export integrity (COCO JSON/CSV validity)
- Verification:
  - Manual inspection via visualizer
  - Automated checks via evaluator

```mermaid
flowchart TD
VStart(["Incoming Results"]) --> BB["Validate BBoxes"]
BB --> KP["Validate Keypoints"]
KP --> TH["Threshold Checks"]
TH --> INT["Integrity Check"]
INT --> PASS{"Pass?"}
PASS --> |Yes| OK["Accept"]
PASS --> |No| FIX["Flag & Investigate"]
OK --> VEnd(["Verified"])
FIX --> VEnd
```

**Diagram sources**
- [evaluator.py](file://utils/evaluator.py)
- [test_hpe_regressions.py](file://tests/test_hpe_regressions.py)

**Section sources**
- [evaluator.py](file://utils/evaluator.py)
- [test_hpe_regressions.py](file://tests/test_hpe_regressions.py)

## Dependency Analysis
The system exhibits layered dependencies: backends depend on shared video detection and visualization utilities, while evaluation and logging tie everything together.

```mermaid
graph TB
BH["Base HPE"] --> AV["AlphaPose HPE"]
BH --> OV["OpenVINO HPE"]
BH --> MV["MobileNet HPE"]
AV --> VU["Video Detection Utils"]
OV --> VU
MV --> VU
VU --> VL["Visualizer"]
VU --> EV["Evaluator"]
EV --> LP["Log Parser"]
EXP["Experiment Runner"] --> AV
EXP --> OV
EXP --> MV
EXP --> CPUP["CPU Perf Plot"]
EXP --> GPUP["GPU SMI Plot"]
EXP --> NETP["Network Rx Plots"]
```

**Diagram sources**
- [base_hpe.py](file://base_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [movenet_hpe.py](file://movenet_hpe.py)
- [video_detection.py](file://utils/video_detection.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)
- [log_parser.py](file://utils/log_parser.py)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [plot_perf_metrics.py](file://Measure_plot_cpu_perf/plot_perf_metrics.py)
- [plot_smi_output.py](file://Measure_gpu_dcgm/plot_smi_output.py)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [plot_rx_bytes_trimmed_reset.py](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py)

**Section sources**
- [base_hpe.py](file://base_hpe.py)
- [video_detection.py](file://utils/video_detection.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)
- [log_parser.py](file://utils/log_parser.py)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)

## Performance Considerations
- Throughput and latency:
  - Use batch processing where supported
  - Optimize preprocessing (padding/resizing) and postprocessing
- GPU/CPU utilization:
  - Monitor via SMI and perf plots
  - Tune backend configurations (OpenVINO, AlphaPose)
- Network traffic:
  - Observe RX byte plots for streaming workloads
- Experiment orchestration:
  - Automate runs and collect metrics systematically

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and remedies:
- Inference failures:
  - Verify model paths and backend adapters
  - Check input shape and preprocessing alignment
- Visualization anomalies:
  - Confirm keypoint indices and COCO ordering
  - Inspect score thresholds and normalization
- Export errors:
  - Validate COCO JSON schema compliance
  - Ensure CSV column counts match expectations
- Streaming problems:
  - Test with local stream servers
  - Validate RTSP-like endpoints and codecs

**Section sources**
- [base_hpe.py](file://base_hpe.py)
- [visualizer.py](file://utils/visualizer.py)
- [evaluator.py](file://utils/evaluator.py)
- [log_parser.py](file://utils/log_parser.py)
- [stream_video_server.py](file://dev_tools/stream_video_server.py)
- [stream_video_server_adaptive.py](file://dev_tools/stream_video_server_adaptive.py)

## Conclusion
The system provides a robust pipeline for HPE data processing and analysis, from raw frames to validated COCO exports and performance insights. By leveraging backend-specific strengths, unified utilities, and comprehensive evaluation/logging, teams can reliably compare methods, interpret benchmarks, and ensure result quality.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Appendix A: End-to-End Experiment Workflow
- Orchestrate experiments with the runner script
- Collect CPU/GPU metrics and network RX plots
- Parse logs and export aggregated results

```mermaid
sequenceDiagram
participant RUN as "Runner Script"
participant CPU as "CPU Perf Plot"
participant GPU as "GPU SMI Plot"
participant NET as "Network RX Plot"
participant LOG as "Log Parser"
participant REP as "Report"
RUN->>CPU : "Capture metrics"
RUN->>GPU : "Capture metrics"
RUN->>NET : "Capture RX bytes"
RUN->>LOG : "Parse logs"
LOG->>REP : "Aggregate results"
CPU->>REP : "Throughput/Latency"
GPU->>REP : "Utilization"
NET->>REP : "Bandwidth"
```

**Diagram sources**
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [plot_perf_metrics.py](file://Measure_plot_cpu_perf/plot_perf_metrics.py)
- [plot_smi_output.py](file://Measure_gpu_dcgm/plot_smi_output.py)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [plot_rx_bytes_trimmed_reset.py](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py)
- [log_parser.py](file://utils/log_parser.py)