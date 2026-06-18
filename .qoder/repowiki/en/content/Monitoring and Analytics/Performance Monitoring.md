# Performance Monitoring

<cite>
**Referenced Files in This Document**
- [prometheus.yml](file://prometheus.yml)
- [recent-dash/prometheus.yml](file://recent-dash/prometheus.yml)
- [monitor_hpe/docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [ffmpeg_hpe/docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [monitor_hpe/monitor_pid.sh](file://monitor_hpe/monitor_pid.sh)
- [ffmpeg_hpe/monitor_pid.sh](file://ffmpeg_hpe/monitor_pid.sh)
- [ffmpeg_hpe/run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [Measure_gpu_dcgm/run_nvidia_dcgm.sh](file://Measure_gpu_dcgm/run_nvidia_dcgm.sh)
- [Measure_plot_cpu_perf/run_perf_plot.sh](file://Measure_plot_cpu_perf/run_perf_plot.sh)
- [Measure_plot_cpu_perf/plot_perf_metrics.py](file://Measure_plot_cpu_perf/plot_perf_metrics.py)
- [ffmpeg_hpe/plot_smi_output.py](file://ffmpeg_hpe/plot_smi_output.py)
- [ffmpeg_hpe/plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [shared/perf_monitor/monitor_pid_perf.sh](file://shared/perf_monitor/monitor_pid_perf.sh)
- [shared/perf_monitor/Dockerfile](file://shared/perf_monitor/Dockerfile)
- [monitor_hpe/Dockerfile.perf](file://monitor_hpe/Dockerfile.perf)
</cite>

## Update Summary
**Changes Made**
- Added documentation for centralized performance monitoring infrastructure through shared/perf_monitor/monitor_pid_perf.sh
- Updated core components section to reflect unified monitoring approach
- Revised detailed component analysis to include the new centralized monitoring script
- Enhanced architecture overview to show the shared monitoring container integration
- Updated dependency analysis to reflect the new centralized Dockerfile structure

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
This document describes the performance monitoring capabilities in the HPE framework. It explains how CPU utilization, GPU performance metrics, memory consumption, and network throughput are tracked in real time, how Prometheus scrapes metrics, how Grafana dashboards can visualize KPIs, and how custom monitoring scripts integrate with the system. The framework now features a centralized performance monitoring infrastructure that consolidates monitoring logic across multiple experiment rigs into a single, reusable component. It also covers setting up dashboards, configuring alerting, interpreting metrics, identifying optimization opportunities, and establishing baseline performance targets. Finally, it provides troubleshooting workflows and best practices for maintaining optimal performance.

## Project Structure
The performance monitoring stack spans several Docker Compose configurations and monitoring scripts, now featuring a centralized monitoring infrastructure:
- Real-time process metrics are collected via a centralized /proc-based monitoring script that provides consistent CPU utilization sampling using /proc/$PID/stat deltas.
- GPU metrics are captured using nvidia-smi-based scripts.
- Prometheus is configured to scrape exporters and agents.
- Grafana dashboards consume Prometheus data to visualize KPIs and trends.
- Scripts generate plots for offline analysis and capacity planning.

```mermaid
graph TB
subgraph "Runtime"
HPE["HPE Application<br/>Container"]
Streamer["RTSP Streaming Server<br/>Container"]
GPU["GPU Metrics Collector<br/>Container"]
SharedPerf["Centralized Perf Monitor<br/>Container"]
end
subgraph "Monitoring"
ProcDelta["/proc Delta Sampling<br/>CPU/Mem"]
NSMI["nvidia-smi Logging<br/>GPU Stats"]
BPF["bpftrace Tracing<br/>Network TX/RX"]
end
subgraph "Metrics"
Prom["Prometheus Scrape Configs"]
Exp["DCGM Exporter / Node Agent"]
end
subgraph "Visualization"
Graf["Grafana Dashboards"]
end
HPE --> SharedPerf
GPU --> NSMI
SharedPerf --> ProcDelta
HPE --> BPF
HPE --> Prom
GPU --> Prom
Prom --> Graf
Exp --> Graf
```

**Diagram sources**
- [ffmpeg_hpe/docker-compose.yaml:119-125](file://ffmpeg_hpe/docker-compose.yaml#L119-L125)
- [shared/perf_monitor/Dockerfile:1-29](file://shared/perf_monitor/Dockerfile#L1-L29)
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [recent-dash/prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

**Section sources**
- [ffmpeg_hpe/docker-compose.yaml:1-201](file://ffmpeg_hpe/docker-compose.yaml#L1-L201)
- [monitor_hpe/docker-compose.yaml:1-52](file://monitor_hpe/docker-compose.yaml#L1-L52)
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [recent-dash/prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

## Core Components
- Centralized per-process CPU/memory monitoring:
  - Unified /proc-based monitoring script that calculates CPU utilization using /proc/$PID/stat deltas for consistent sampling.
  - Supports multiple PIDs from a single PID file with automatic tracking and cleanup.
- GPU metrics logging:
  - nvidia-smi-based periodic logging of GPU utilization, memory utilization, temperature, and power.
- Prometheus scraping:
  - Dedicated scrape jobs for DCGM exporter and node/cluster agents.
- Grafana dashboards:
  - Visualize Prometheus metrics for KPIs, trends, and capacity planning.
- Offline plotting:
  - Scripts to generate plots from collected CSV data for analysis and reporting.

Key metrics produced:
- CPU utilization (%), memory RSS (KB), and active PID count from the centralized monitoring.
- GPU utilization (%), memory utilization (%), temperature (°C), power (W), and memory usage (total/free/used).

**Updated** Added centralized monitoring component using /proc-based delta calculations for consistent CPU utilization sampling.

**Section sources**
- [shared/perf_monitor/monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [ffmpeg_hpe/run_nvidia_dcgm.sh:30-75](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L30-L75)
- [Measure_gpu_dcgm/run_nvidia_dcgm.sh:7-16](file://Measure_gpu_dcgm/run_nvidia_dcgm.sh#L7-L16)
- [prometheus.yml:5-8](file://prometheus.yml#L5-L8)
- [recent-dash/prometheus.yml:6-23](file://recent-dash/prometheus.yml#L6-L23)

## Architecture Overview
The monitoring architecture integrates containerized workloads with centralized real-time metrics collection and centralized scraping.

```mermaid
sequenceDiagram
participant HPE as "HPE Container"
participant Shared as "Centralized Perf Monitor"
participant Proc as "/proc Delta Sampling"
participant NSMI as "nvidia-smi"
participant Prom as "Prometheus"
participant Graf as "Grafana"
HPE->>Shared : Write target PIDs to /pids/dash.pid
Shared->>Proc : Calculate CPU% via /proc/$PID/stat deltas
Shared->>Proc : Read memory RSS from /proc/$PID/status
Shared-->>Prom : Export perf_metrics.csv with timestamp, totals
NSMI-->>Prom : Export CSV metrics via mounted /output
Prom-->>Graf : Scrape jobs for exporters and agents
Graf-->>HPE : Dashboards for KPIs/trends
```

**Diagram sources**
- [shared/perf_monitor/monitor_pid_perf.sh:27-106](file://shared/perf_monitor/monitor_pid_perf.sh#L27-L106)
- [shared/perf_monitor/Dockerfile:24-28](file://shared/perf_monitor/Dockerfile#L24-L28)
- [prometheus.yml:5-8](file://prometheus.yml#L5-L8)
- [recent-dash/prometheus.yml:6-23](file://recent-dash/prometheus.yml#L6-L23)

## Detailed Component Analysis

### Centralized Performance Monitoring Infrastructure
The new centralized monitoring infrastructure consolidates performance monitoring logic into a single, reusable component that provides consistent CPU utilization sampling using /proc/$PID/stat deltas instead of blocking pidstat utility.

```mermaid
flowchart TD
Start(["Start Centralized Monitoring"]) --> CheckPID["Check PID file existence<br/>and readability"]
CheckPID --> ReadPIDs["Read all PIDs from PID file"]
ReadPIDs --> InitCSV["Initialize perf_metrics.csv with headers"]
InitCSV --> Loop["Main monitoring loop"]
Loop --> CalcProc["Calculate /proc delta for each PID"]
CalcProc --> SumTotals["Sum CPU%, memory, and active PIDs"]
SumTotals --> WriteCSV["Write consolidated metrics to CSV"]
WriteCSV --> Sleep["Sleep for configured interval"]
Sleep --> Loop
```

**Diagram sources**
- [shared/perf_monitor/monitor_pid_perf.sh:27-106](file://shared/perf_monitor/monitor_pid_perf.sh#L27-L106)

**Section sources**
- [shared/perf_monitor/monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)

### Real-Time Per-Process Metrics (CPU, Memory)
The centralized monitoring script provides comprehensive per-process metrics with improved efficiency:
- Calculates CPU utilization using /proc/$PID/stat field 14+15 (utime+stime) deltas for instant, non-blocking sampling.
- Reads memory RSS from /proc/$PID/status VmRSS field.
- Tracks multiple PIDs from a single PID file with automatic cleanup of terminated processes.
- Provides consolidated metrics including total CPU percentage, total memory usage, and active PID count.

```mermaid
flowchart TD
Start(["Start Monitoring"]) --> WaitPID["Wait for PID file<br/>timeout 30s"]
WaitPID --> ReadPID["Read target PID(s)"]
ReadPID --> InitCSV["Initialize CSV headers"]
InitCSV --> LaunchProc["Launch /proc delta calculations"]
LaunchProc --> Loop["Main loop every INTERVAL seconds"]
Loop --> CheckPID{"Process alive?"}
CheckPID --> |No| Cleanup["Cleanup and exit"]
CheckPID --> |Yes| SampleProc["Sample CPU % and RSS"]
SampleProc --> CalcDelta["Calculate CPU% via /proc deltas"]
CalcDelta --> SumTotals["Sum metrics across all PIDs"]
SumTotals --> WriteCSV["Write consolidated metrics to CSV"]
WriteCSV --> Sleep["Sleep INTERVAL seconds"]
Sleep --> Loop
```

**Diagram sources**
- [shared/perf_monitor/monitor_pid_perf.sh:19-25](file://shared/perf_monitor/monitor_pid_perf.sh#L19-L25)
- [shared/perf_monitor/monitor_pid_perf.sh:75-92](file://shared/perf_monitor/monitor_pid_perf.sh#L75-L92)

**Section sources**
- [shared/perf_monitor/monitor_pid_perf.sh:19-92](file://shared/perf_monitor/monitor_pid_perf.sh#L19-L92)

### GPU Metrics Collection
GPU metrics are collected periodically using nvidia-smi and written to CSV:
- ffmpeg_hpe/run_nvidia_dcgm.sh: configurable interval and duration, writes header, loops with nvidia-smi queries, and supports termination via signal.
- Measure_gpu_dcgm/run_nvidia_dcgm.sh: simplified loop writing timestamped GPU stats.

```mermaid
flowchart TD
Start(["Start GPU Metrics"]) --> Header["Write CSV header"]
Header --> Loop["Loop with interval"]
Loop --> Query["Run nvidia-smi queries"]
Query --> Append["Append timestamped rows to CSV"]
Append --> CheckDur{"Duration reached?"}
CheckDur --> |No| Sleep["Sleep interval"]
Sleep --> Loop
CheckDur --> |Yes| Stop(["Stop and cleanup"])
```

**Diagram sources**
- [ffmpeg_hpe/run_nvidia_dcgm.sh:46-80](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L46-L80)
- [Measure_gpu_dcgm/run_nvidia_dcgm.sh:10-27](file://Measure_gpu_dcgm/run_nvidia_dcgm.sh#L10-L27)

**Section sources**
- [ffmpeg_hpe/run_nvidia_dcgm.sh:1-84](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L84)
- [Measure_gpu_dcgm/run_nvidia_dcgm.sh:1-29](file://Measure_gpu_dcgm/run_nvidia_dcgm.sh#L1-L29)

### Prometheus Scraping and Grafana Dashboards
Prometheus is configured to scrape:
- DCGM exporter for GPU metrics.
- Node/cluster agents for host/container metrics.

```mermaid
graph LR
Prom["Prometheus Config"] --> JobDCGM["Job 'dcgm-exporter'<br/>targets: dcgm-exporter:9400"]
Prom --> JobNA["Job 'node-agent'<br/>targets: node-agent:9100"]
Prom --> JobCA["Job 'cluster-agent'<br/>targets: cluster-agent:9100"]
Prom --> JobCoroot["Job 'coroot'<br/>targets: coroot:8080"]
```

**Diagram sources**
- [prometheus.yml:5-8](file://prometheus.yml#L5-L8)
- [recent-dash/prometheus.yml:6-23](file://recent-dash/prometheus.yml#L6-L23)

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [recent-dash/prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

### CPU Performance Profiling (Optional)
A separate CPU profiling workflow uses perf to capture cpu-clock and cycles at intervals and generates plots.

```mermaid
sequenceDiagram
participant User as "Operator"
participant Script as "run_perf_plot.sh"
participant Perf as "perf"
participant Py as "plot_perf_metrics.py"
User->>Script : Execute with PID file
Script->>Perf : Run perf stat for target PID(s)
Perf-->>Script : Emit CSV-like lines
Script->>Py : Invoke plotting script
Py-->>User : Save performance_metrics.png and perf_data.csv
```

**Diagram sources**
- [Measure_plot_cpu_perf/run_perf_plot.sh:11-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L11-L25)
- [Measure_plot_cpu_perf/plot_perf_metrics.py:16-145](file://Measure_plot_cpu_perf/plot_perf_metrics.py#L16-L145)

**Section sources**
- [Measure_plot_cpu_perf/run_perf_plot.sh:1-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L1-L25)
- [Measure_plot_cpu_perf/plot_perf_metrics.py:1-146](file://Measure_plot_cpu_perf/plot_perf_metrics.py#L1-L146)

### Network Throughput Visualization
Network RX/TX traces can be plotted from CSV outputs for trend analysis and capacity planning.

```mermaid
flowchart TD
CSV["Network CSV (RX/TX)"] --> Load["Load CSV with pandas"]
Load --> Trim["Trim to first nonzero RX"]
Trim --> Plot["Plot RX bytes per interval"]
Plot --> Save["Save PNG"]
```

**Diagram sources**
- [ffmpeg_hpe/plot_rx_bytes.py:10-23](file://ffmpeg_hpe/plot_rx_bytes.py#L10-L23)

**Section sources**
- [ffmpeg_hpe/plot_rx_bytes.py:1-24](file://ffmpeg_hpe/plot_rx_bytes.py#L1-L24)

### GPU Metric Visualization
GPU metrics CSV can be plotted to visualize utilization and temperature over time.

```mermaid
flowchart TD
CSV["GPU CSV"] --> Load["Load with pandas"]
Load --> TS["Convert timestamp"]
TS --> Plot["Plot GPU Utilization and Temperature"]
Plot --> Save["Save PNG"]
```

**Diagram sources**
- [ffmpeg_hpe/plot_smi_output.py:6-20](file://ffmpeg_hpe/plot_smi_output.py#L6-L20)

**Section sources**
- [ffmpeg_hpe/plot_smi_output.py:1-21](file://ffmpeg_hpe/plot_smi_output.py#L1-L21)

## Dependency Analysis
- Container orchestration:
  - ffmpeg_hpe/docker-compose.yaml defines HPE, streaming server, GPU metrics collector, and centralized perf monitor using shared infrastructure.
  - monitor_hpe/docker-compose.yaml defines a minimal monitoring setup for standalone experiments.
- Centralized monitoring infrastructure:
  - shared/perf_monitor/monitor_pid_perf.sh provides unified monitoring logic with /proc-based delta calculations.
  - shared/perf_monitor/Dockerfile creates a lightweight container with essential monitoring tools.
- Metrics producers:
  - Centralized /proc-based scripts produce CSV metrics consumed by Prometheus.
  - nvidia-smi scripts produce CSV metrics consumed by Prometheus.
- Scraping and visualization:
  - Prometheus scrape configs define targets for DCGM exporter and node/cluster agents.
  - Grafana dashboards consume Prometheus data.

```mermaid
graph TB
SH["shared/perf_monitor/"] --> MON["monitor_pid_perf.sh"]
SH --> DF["Dockerfile"]
DC["ffmpeg_hpe/docker-compose.yaml"] --> HPE["HPE"]
DC --> STR["Streaming Server"]
DC --> GPU["GPU Metrics"]
DC --> PM["Centralized Perf Monitor"]
PM --> MON
MON --> PROC["/proc Delta Calculations"]
MH["monitor_hpe/docker-compose.yaml"] --> MON2["monitor_pid.sh"]
HPE --> BPF["bpftrace"]
GPU --> NSMI["nvidia-smi"]
PROM["prometheus.yml / recent-dash/prometheus.yml"] --> EXP["DCGM/Node/Cluster Agents"]
PROM --> OUT["Mounted /output CSVs"]
OUT --> GRAF["Grafana Dashboards"]
```

**Diagram sources**
- [shared/perf_monitor/monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [shared/perf_monitor/Dockerfile:1-29](file://shared/perf_monitor/Dockerfile#L1-L29)
- [ffmpeg_hpe/docker-compose.yaml:119-125](file://ffmpeg_hpe/docker-compose.yaml#L119-L125)
- [monitor_hpe/docker-compose.yaml:1-52](file://monitor_hpe/docker-compose.yaml#L1-L52)
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [recent-dash/prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

**Section sources**
- [shared/perf_monitor/monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [shared/perf_monitor/Dockerfile:1-29](file://shared/perf_monitor/Dockerfile#L1-L29)
- [ffmpeg_hpe/docker-compose.yaml:1-201](file://ffmpeg_hpe/docker-compose.yaml#L1-L201)
- [monitor_hpe/docker-compose.yaml:1-52](file://monitor_hpe/docker-compose.yaml#L1-L52)
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [recent-dash/prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

## Performance Considerations
- Sampling cadence:
  - Centralized monitoring runs at configurable intervals (default 0.5s) with instant /proc-based calculations.
  - nvidia-smi logging interval defaults to 0.5s; tune for accuracy and storage cost.
- Resource efficiency:
  - /proc-based delta calculations eliminate blocking external tools like pidstat, reducing overhead.
  - Single centralized container reduces resource duplication across multiple experiment rigs.
- Resource isolation:
  - Containers specify CPU/memory limits/reservations to avoid noisy-neighbor effects.
  - Monitoring containers are constrained to reduce measurement interference.
- I/O and locking:
  - CSV writes use flock and sync to ensure atomicity and durability.
- Network throughput:
  - TX/RX rates are computed per interval; ensure intervals align with Prometheus scrape frequency.

**Updated** Added considerations for centralized monitoring efficiency and resource optimization.

## Troubleshooting Guide
Common issues and resolutions:
- Missing PID file:
  - Ensure the HPE container writes the PID file to the shared /pids volume before monitoring starts.
  - For centralized monitoring, verify /pids/dash.pid contains valid numeric PIDs.
- /proc access permissions:
  - The centralized monitoring container requires appropriate permissions to read /proc filesystem.
- nvidia-smi not found:
  - Confirm NVIDIA drivers and runtime are available in the GPU metrics container.
- Prometheus scrape failures:
  - Verify exporter endpoints are reachable and scrape intervals match exporter cadence.
- CSV not generated:
  - Check that the output directory is writable and mounted into the monitoring containers.
- Centralized monitoring issues:
  - Verify /proc/$PID/stat and /proc/$PID/status are accessible for all monitored processes.
  - Check that the monitoring script has proper permissions to read process information.

Operational checks:
- Validate container health and logs after startup.
- Confirm CSV files appear under /output and are timestamped.
- Use offline plotting scripts to verify metric integrity.
- Monitor centralized container resource usage separately from monitored applications.

**Updated** Added troubleshooting guidance specific to centralized monitoring infrastructure.

**Section sources**
- [shared/perf_monitor/monitor_pid_perf.sh:28-39](file://shared/perf_monitor/monitor_pid_perf.sh#L28-L39)
- [shared/perf_monitor/Dockerfile:19-20](file://shared/perf_monitor/Dockerfile#L19-L20)
- [monitor_hpe/docker-compose.yaml:32-44](file://monitor_hpe/docker-compose.yaml#L32-L44)
- [ffmpeg_hpe/docker-compose.yaml:94-115](file://ffmpeg_hpe/docker-compose.yaml#L94-L115)
- [prometheus.yml:5-8](file://prometheus.yml#L5-L8)
- [recent-dash/prometheus.yml:6-23](file://recent-dash/prometheus.yml#L6-L23)

## Conclusion
The HPE framework's performance monitoring stack now features a centralized infrastructure that consolidates monitoring logic across multiple experiment rigs into a single, reusable component. The new shared/perf_monitor/monitor_pid_perf.sh script provides consistent CPU utilization sampling using /proc/$PID/stat deltas, eliminating blocking pidstat utility and improving monitoring efficiency. Combined with per-process metrics (CPU, memory, network), GPU telemetry, and Prometheus-based ingestion, this enables Grafana-driven KPIs, trend analysis, and capacity planning. By tuning sampling intervals, isolating resources, and validating exporters, teams can maintain visibility into system performance and quickly identify bottlenecks and degradation.

**Updated** Enhanced conclusion to reflect the benefits of centralized monitoring infrastructure.

## Appendices

### Setup Checklist
- Configure Prometheus scrape jobs for DCGM exporter and node/cluster agents.
- Deploy centralized monitoring container with appropriate capabilities and mounts.
- Run experiments and verify CSV outputs and Grafana dashboards.
- Establish baselines and configure alerts for CPU, memory, GPU, and network thresholds.
- For centralized monitoring, ensure /pids/dash.pid contains valid PIDs for all processes to monitor.

**Updated** Added setup guidance for centralized monitoring infrastructure.

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [recent-dash/prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)
- [monitor_hpe/docker-compose.yaml:28-50](file://monitor_hpe/docker-compose.yaml#L28-L50)
- [ffmpeg_hpe/docker-compose.yaml:116-140](file://ffmpeg_hpe/docker-compose.yaml#L116-L140)
- [shared/perf_monitor/Dockerfile:1-29](file://shared/perf_monitor/Dockerfile#L1-L29)