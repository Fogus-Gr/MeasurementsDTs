# Log Parsing and Analysis

<cite>
**Referenced Files in This Document**
- [utils/log_parser.py](file://utils/log_parser.py)
- [utils/evaluator.py](file://utils/evaluator.py)
- [monitor.py](file://monitor.py)
- [measure_flops/measure_flops.sh](file://measure_flops/measure_flops.sh)
- [measure_gpu_dcgm/run_nvidia_dcgm.sh](file://measure_gpu_dcgm/run_nvidia_dcgm.sh)
- [measure_gpu_dcgm/plot_smi_output.py](file://measure_gpu_dcgm/plot_smi_output.py)
- [measure_plot_cpu_perf/plot_perf_metrics.py](file://measure_plot_cpu_perf/plot_perf_metrics.py)
- [ffmpeg_hpe/plot_graph.py](file://ffmpeg_hpe/plot_graph.py)
- [monitor_hpe/plot_graph.py](file://monitor_hpe/plot_graph.py)
- [ffmpeg_hpe/run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [ONBOARDING.md](file://ONBOARDING.md)
- [docs/session-report-2026-05-06.md](file://docs/session-report-2026-05-06.md)
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
This document explains the log parsing and analysis capabilities used to extract performance metrics and experiment results across CPU, GPU, network, and inference workloads. It covers:
- Structured log parsing for performance summaries, sessions, and video properties
- Timing data, memory usage, and throughput extraction
- Patterns for CPU utilization, GPU metrics, network bandwidth, and inference latency
- Aggregation methods for averages, variances, and statistical summaries
- Integration with experiment orchestration for automated result collection
- Examples of parsed log formats and extracted metric structures
- Error handling for malformed entries and missing data
- Benchmark interpretation and comparative analysis across HPE backends and configurations

## Project Structure
The repository organizes performance instrumentation and analysis across several modules:
- Logging and analysis utilities for structured logs and evaluation artifacts
- Threaded monitors for CPU/GPU metrics with CSV export
- Scripts for FLOPS and GPU metrics collection via NVIDIA tools
- Plotting utilities for time-series visualization
- Experiment orchestration scripts that collect CSV outputs and logs

```mermaid
graph TB
subgraph "Logging and Analysis"
LP["utils/log_parser.py"]
EVAL["utils/evaluator.py"]
end
subgraph "Monitors"
MON["monitor.py"]
end
subgraph "GPU Bench"
MF["measure_flops/measure_flops.sh"]
DCGM_RUN["measure_gpu_dcgm/run_nvidia_dcgm.sh"]
DCGM_PLOT["measure_gpu_dcgm/plot_smi_output.py"]
end
subgraph "CPU Bench"
PERF_PLOT["measure_plot_cpu_perf/plot_perf_metrics.py"]
end
subgraph "Experiment Orchestration"
RUN_EX["ffmpeg_hpe/run_experiment.sh"]
ONBOARD["ONBOARDING.md"]
SR["docs/session-report-2026-05-06.md"]
end
subgraph "Plotting"
FG["ffmpeg_hpe/plot_graph.py"]
MH["monitor_hpe/plot_graph.py"]
end
RUN_EX --> MON
RUN_EX --> MF
RUN_EX --> DCGM_RUN
RUN_EX --> FG
RUN_EX --> MH
MF --> DCGM_PLOT
MF --> PERF_PLOT
LP --> EVAL
```

**Diagram sources**
- [utils/log_parser.py:1-155](file://utils/log_parser.py#L1-L155)
- [utils/evaluator.py:1-114](file://utils/evaluator.py#L1-L114)
- [monitor.py:1-171](file://monitor.py#L1-L171)
- [measure_flops/measure_flops.sh:1-128](file://measure_flops/measure_flops.sh#L1-L128)
- [measure_gpu_dcgm/run_nvidia_dcgm.sh:1-29](file://measure_gpu_dcgm/run_nvidia_dcgm.sh#L1-L29)
- [measure_gpu_dcgm/plot_smi_output.py:1-106](file://measure_gpu_dcgm/plot_smi_output.py#L1-L106)
- [measure_plot_cpu_perf/plot_perf_metrics.py:1-146](file://measure_plot_cpu_perf/plot_perf_metrics.py#L1-L146)
- [ffmpeg_hpe/plot_graph.py:1-104](file://ffmpeg_hpe/plot_graph.py#L1-L104)
- [monitor_hpe/plot_graph.py:1-66](file://monitor_hpe/plot_graph.py#L1-L66)
- [ffmpeg_hpe/run_experiment.sh:332-405](file://ffmpeg_hpe/run_experiment.sh#L332-L405)
- [ONBOARDING.md:647-677](file://ONBOARDING.md#L647-L677)
- [docs/session-report-2026-05-06.md:229-253](file://docs/session-report-2026-05-06.md#L229-L253)

**Section sources**
- [ONBOARDING.md:647-677](file://ONBOARDING.md#L647-L677)

## Core Components
- Structured log parser: Reads newline-delimited JSON logs, filters event types, prints summaries, and exports flattened CSV for downstream analysis.
- Threaded monitors: Background sampling of CPU and GPU metrics with CSV export for time-aligned analysis.
- FLOPS and GPU metrics pipeline: Starts GPU/CPU monitors, profiles kernels, computes GFLOPS/TOPS/BW/Latency, and generates elapsed-time CSVs for plotting.
- Evaluation helpers: COCO-format keypoint serialization and per-interval bandwidth accumulation for throughput analysis.
- Plotting utilities: Time-aligned visualization of CPU/GPU/network metrics with robust input validation and error reporting.

**Section sources**
- [utils/log_parser.py:12-155](file://utils/log_parser.py#L12-L155)
- [monitor.py:32-171](file://monitor.py#L32-L171)
- [measure_flops/measure_flops.sh:17-128](file://measure_flops/measure_flops.sh#L17-L128)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)
- [measure_gpu_dcgm/plot_smi_output.py:13-106](file://measure_gpu_dcgm/plot_smi_output.py#L13-L106)
- [measure_plot_cpu_perf/plot_perf_metrics.py:16-146](file://measure_plot_cpu_perf/plot_perf_metrics.py#L16-L146)
- [ffmpeg_hpe/plot_graph.py:9-104](file://ffmpeg_hpe/plot_graph.py#L9-L104)
- [monitor_hpe/plot_graph.py:10-66](file://monitor_hpe/plot_graph.py#L10-L66)

## Architecture Overview
The system integrates experiment orchestration with instrumentation and post-processing:
- Experiment runner starts HPE, monitors, and tracers; collects CSV outputs and logs
- Monitors continuously sample CPU/GPU metrics and export CSVs
- FLOPS pipeline launches profiling and computes derived metrics
- Plotting utilities consume CSVs to produce time-aligned visualizations
- Log parser ingests structured logs for performance summaries and session metadata

```mermaid
sequenceDiagram
participant Exp as "Experiment Runner<br/>run_experiment.sh"
participant HPE as "HPE Container"
participant Mon as "Monitors<br/>monitor.py"
participant GPU as "GPU Bench<br/>measure_flops.sh"
participant Eval as "Evaluator<br/>utils/evaluator.py"
participant Plot as "Plotters<br/>plot_graph.py / plot_perf_metrics.py"
participant Log as "Structured Logs<br/>utils/log_parser.py"
Exp->>HPE : "Start HPE workload"
Exp->>Mon : "Start CPU/GPU monitors"
Exp->>GPU : "Launch profiling and monitors"
HPE-->>Eval : "Keypoints and timestamps"
GPU-->>Exp : "CSV outputs (CPU/GPU/FLOPS)"
Mon-->>Exp : "CSV outputs (CPU/GPU)"
Exp->>Plot : "Render time-aligned plots"
HPE-->>Log : "Emit structured logs"
Log-->>Exp : "Summaries and session info"
```

**Diagram sources**
- [ffmpeg_hpe/run_experiment.sh:332-405](file://ffmpeg_hpe/run_experiment.sh#L332-L405)
- [monitor.py:109-171](file://monitor.py#L109-L171)
- [measure_flops/measure_flops.sh:17-128](file://measure_flops/measure_flops.sh#L17-L128)
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)
- [ffmpeg_hpe/plot_graph.py:9-104](file://ffmpeg_hpe/plot_graph.py#L9-L104)
- [measure_plot_cpu_perf/plot_perf_metrics.py:16-146](file://measure_plot_cpu_perf/plot_perf_metrics.py#L16-L146)
- [utils/log_parser.py:12-155](file://utils/log_parser.py#L12-L155)

## Detailed Component Analysis

### Structured Log Parser
- Parses newline-delimited JSON logs into a DataFrame
- Filters and prints performance summaries, session events, and video property detections
- Exports flattened CSV for downstream analytics

```mermaid
flowchart TD
StartLP["Start parse_structured_logs()"] --> CheckFile["Check log file exists"]
CheckFile --> Exists{"Exists?"}
Exists --> |No| ReturnNone["Return None"]
Exists --> |Yes| ReadLines["Iterate lines"]
ReadLines --> TryJSON["Try json.loads(line)"]
TryJSON --> Valid{"Valid JSON?"}
Valid --> |No| Skip["Skip line"]
Valid --> |Yes| Append["Append event to list"]
Append --> NextLine["Next line"]
NextLine --> |More| ReadLines
NextLine --> |Done| BuildDF["Build DataFrame"]
BuildDF --> ReturnDF["Return DataFrame"]
```

**Diagram sources**
- [utils/log_parser.py:12-33](file://utils/log_parser.py#L12-L33)

Key extraction patterns:
- Performance summary fields: model_type, input_source, total_frames, fps_avg, inference_time_avg, timestamp
- Session events: method, input, device, timeout, max_frames, timestamp
- Video properties: input_url, fps, duration, total_frames, timestamp

Statistical summaries:
- Average FPS and inference time computed from aggregated performance events
- Optional flattened CSV export for external analysis

**Section sources**
- [utils/log_parser.py:12-155](file://utils/log_parser.py#L12-L155)

### Threaded Monitors (CPU/GPU)
- BaseMonitor manages background sampling with configurable intervals
- GpuStatsMonitor samples GPU utilization and memory via NVML
- CpuStatsMonitor samples CPU percent and memory via psutil
- CSV export supports time-aligned analysis with external plotting tools

```mermaid
classDiagram
class BaseMonitor {
+float interval
+Dict[] records
+start() void
+stop() void
+export_csv(filepath) void
+records Dict[]
-_sample() Dict~float~
-_run() void
}
class GpuStatsMonitor {
+int gpu_index
+float interval
+stop() void
-_sample() Dict~float~
}
class CpuStatsMonitor {
+float interval
-_sample() Dict~float~
}
BaseMonitor <|-- GpuStatsMonitor
BaseMonitor <|-- CpuStatsMonitor
```

**Diagram sources**
- [monitor.py:32-171](file://monitor.py#L32-L171)

Metrics and units:
- GPU: timestamp, gpu_util_percent, gpu_mem_used_MB, gpu_mem_total_MB
- CPU: timestamp, cpu_percent, ram_used_MB, ram_total_MB

**Section sources**
- [monitor.py:32-171](file://monitor.py#L32-L171)

### FLOPS and GPU Metrics Pipeline
- Launches GPU/CPU monitors and runs profiling with Nsight Compute
- Computes GFLOPS, TOPS, bandwidth, and warp latency
- Generates elapsed-time CSVs for plotting

```mermaid
sequenceDiagram
participant Script as "measure_flops.sh"
participant GPU as "nvidia-smi"
participant CPU as "ps"
participant NCU as "Nsight Compute"
participant Py as "Python Calculator"
Script->>GPU : "Start GPU monitor CSV"
Script->>CPU : "Start CPU monitor CSV"
Script->>NCU : "Profile workload"
NCU-->>Script : "Report CSV"
Script->>Py : "Compute metrics"
Py-->>Script : "GFLOPS, TOPS, BW, Latency"
Script->>GPU : "Stop monitor"
Script->>CPU : "Stop monitor"
```

**Diagram sources**
- [measure_flops/measure_flops.sh:17-128](file://measure_flops/measure_flops.sh#L17-L128)

Derived metrics:
- Measured GFLOPS, TOPS, Bandwidth (GB/s), Average Warp Latency
- Elapsed-time CSVs for aligned plotting

**Section sources**
- [measure_flops/measure_flops.sh:17-128](file://measure_flops/measure_flops.sh#L17-L128)

### Evaluation Helpers (Throughput and COCO Export)
- Converts detected poses to COCO keypoints with visibility flags
- Accumulates JSON output per millisecond interval to estimate bandwidth
- Saves COCO JSON and CSV, and per-millisecond byte counts

```mermaid
flowchart TD
StartEval["Start append_COCO_format_csv()"] --> Create["Create COCO keypoints"]
Create --> Serialize["Serialize to JSON"]
Serialize --> AppendCSV["Append to CSV rows"]
AppendCSV --> TxAcc["Accumulate bytes per interval"]
TxAcc --> FlushPrev["Flush previous interval if needed"]
FlushPrev --> FillMissing["Fill missing intervals with zero"]
FillMissing --> BufferReset["Reset buffer for new interval"]
BufferReset --> Save["Save CSV outputs"]
```

**Diagram sources**
- [utils/evaluator.py:35-114](file://utils/evaluator.py#L35-L114)

**Section sources**
- [utils/evaluator.py:11-114](file://utils/evaluator.py#L11-L114)

### Plotting Utilities
- ffmpeg_hpe/plot_graph.py: Validates CSVs, aligns timestamps, plots CPU%, memory (MB), and RX bytes
- monitor_hpe/plot_graph.py: Plots CPU% and memory (MB) over datetime timestamps
- measure_gpu_dcgm/plot_smi_output.py: Plots GPU utilization, memory utilization, temperature, power, and P-state transitions

```mermaid
sequenceDiagram
participant CSV as "CSV Inputs"
participant Val as "Validation"
participant Align as "Timestamp Alignment"
participant Plot as "Matplotlib"
CSV->>Val : "Load and validate columns"
Val->>Align : "Convert timestamps and compute elapsed"
Align->>Plot : "Render subplots"
Plot-->>Val : "Save PNG"
```

**Diagram sources**
- [ffmpeg_hpe/plot_graph.py:9-104](file://ffmpeg_hpe/plot_graph.py#L9-L104)
- [monitor_hpe/plot_graph.py:10-66](file://monitor_hpe/plot_graph.py#L10-L66)
- [measure_gpu_dcgm/plot_smi_output.py:13-106](file://measure_gpu_dcgm/plot_smi_output.py#L13-L106)

**Section sources**
- [ffmpeg_hpe/plot_graph.py:9-104](file://ffmpeg_hpe/plot_graph.py#L9-L104)
- [monitor_hpe/plot_graph.py:10-66](file://monitor_hpe/plot_graph.py#L10-L66)
- [measure_gpu_dcgm/plot_smi_output.py:13-106](file://measure_gpu_dcgm/plot_smi_output.py#L13-L106)

### Experiment Orchestration Integration
- run_experiment.sh orchestrates container lifecycle, PID discovery, diagnostics capture, and CSV collection
- ONBOARDING.md documents expected directory structure and CSV schemas
- session-report-2026-05-06.md highlights fixes for PID parsing, exit code logging, and container naming

```mermaid
flowchart TD
StartRun["Start run_experiment.sh"] --> Up["docker compose up"]
Up --> Discover["Discover HPE PID and monitor"]
Discover --> Run["Run HPE workload"]
Run --> Diag["Capture diagnostics on exit"]
Diag --> Copy["Copy CSV outputs and logs"]
Copy --> Done["Complete"]
```

**Diagram sources**
- [ffmpeg_hpe/run_experiment.sh:332-405](file://ffmpeg_hpe/run_experiment.sh#L332-L405)
- [ONBOARDING.md:647-677](file://ONBOARDING.md#L647-L677)
- [docs/session-report-2026-05-06.md:229-253](file://docs/session-report-2026-05-06.md#L229-L253)

**Section sources**
- [ffmpeg_hpe/run_experiment.sh:332-405](file://ffmpeg_hpe/run_experiment.sh#L332-L405)
- [ONBOARDING.md:647-677](file://ONBOARDING.md#L647-L677)
- [docs/session-report-2026-05-06.md:229-253](file://docs/session-report-2026-05-06.md#L229-L253)

## Dependency Analysis
- Experiment runner depends on monitor.py for CPU/GPU metrics and measure_flops.sh for profiling outputs
- Plotting utilities depend on CSV schemas documented in ONBOARDING.md
- Log parser consumes structured logs emitted during experiments

```mermaid
graph LR
RUN["run_experiment.sh"] --> MON["monitor.py"]
RUN --> MF["measure_flops.sh"]
MF --> DCGM["plot_smi_output.py"]
MF --> PERF["plot_perf_metrics.py"]
RUN --> FG["ffmpeg_hpe/plot_graph.py"]
RUN --> MH["monitor_hpe/plot_graph.py"]
LOG["utils/log_parser.py"] --> RUN
```

**Diagram sources**
- [ffmpeg_hpe/run_experiment.sh:332-405](file://ffmpeg_hpe/run_experiment.sh#L332-L405)
- [monitor.py:109-171](file://monitor.py#L109-L171)
- [measure_flops/measure_flops.sh:17-128](file://measure_flops/measure_flops.sh#L17-L128)
- [measure_gpu_dcgm/plot_smi_output.py:13-106](file://measure_gpu_dcgm/plot_smi_output.py#L13-L106)
- [measure_plot_cpu_perf/plot_perf_metrics.py:16-146](file://measure_plot_cpu_perf/plot_perf_metrics.py#L16-L146)
- [ffmpeg_hpe/plot_graph.py:9-104](file://ffmpeg_hpe/plot_graph.py#L9-L104)
- [monitor_hpe/plot_graph.py:10-66](file://monitor_hpe/plot_graph.py#L10-L66)
- [utils/log_parser.py:12-155](file://utils/log_parser.py#L12-L155)

**Section sources**
- [ONBOARDING.md:647-677](file://ONBOARDING.md#L647-L677)

## Performance Considerations
- Sampling intervals: Tune monitor.py intervals to balance overhead and resolution
- CSV alignment: Use elapsed timestamps or shared timestamps to align CPU/GPU/network series
- Derived metrics: Compute GFLOPS/TOPS/BW/Latency only when profiling data is present
- Plotting: Validate column presence and numeric conversion to avoid misalignment

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing or malformed structured logs: log parser skips invalid JSON lines and reports “No valid events found”
- Empty CSVs or missing columns: plotting utilities validate required columns and exit with explicit errors
- PID discovery failures: run_experiment.sh logs warnings when HPE PID cannot be found
- Non-zero exit codes: run_experiment.sh writes exit code to hpe_exit.log for diagnosis
- Container naming and defaults: session-report-2026-05-06.md documents fixes for container_name and VIDEO_FILE defaults

**Section sources**
- [utils/log_parser.py:14-29](file://utils/log_parser.py#L14-L29)
- [ffmpeg_hpe/plot_graph.py:11-26](file://ffmpeg_hpe/plot_graph.py#L11-L26)
- [monitor_hpe/plot_graph.py:11-16](file://monitor_hpe/plot_graph.py#L11-L16)
- [ffmpeg_hpe/run_experiment.sh:347-350](file://ffmpeg_hpe/run_experiment.sh#L347-L350)
- [ffmpeg_hpe/run_experiment.sh:377-382](file://ffmpeg_hpe/run_experiment.sh#L377-L382)
- [docs/session-report-2026-05-06.md:229-253](file://docs/session-report-2026-05-06.md#L229-L253)

## Conclusion
The repository provides a cohesive pipeline for collecting, parsing, and visualizing performance metrics across CPU, GPU, and network domains. Structured logs enable high-level performance summaries, while CSV outputs from monitors and profiling tools support detailed time-aligned analysis. Automated experiment orchestration ensures consistent data collection and facilitates comparative benchmarking across HPE backends and configurations.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Parsed Log Formats and Metric Structures
- Structured logs: event_type and data payload; performance_summary includes fps_avg, inference_time_avg, and totals
- Sessions: session_start/session_end with method, input, device, timeout, max_frames
- Video properties: fps, duration, total_frames, input_url
- CSV schemas (from ONBOARDING.md):
  - pid_metrics.csv: timestamp, pid, cpu_percent, mem_rss_kb, tx_bytes, rx_bytes
  - network_stats.csv: timestamp, pid, interface, bytes, sent
  - gpu_metrics.csv: timestamp, gpu_id, gpu_utilization, mem_utilization, temperature, power_usage
  - hpe_video_rx.csv: timestamp_ms, rx_bytes
  - hpe_video_tx.csv: timestamp_ms, tx_bytes

**Section sources**
- [ONBOARDING.md:647-677](file://ONBOARDING.md#L647-L677)