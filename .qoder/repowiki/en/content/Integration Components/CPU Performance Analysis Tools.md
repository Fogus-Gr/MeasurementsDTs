# CPU Performance Analysis Tools

<cite>
**Referenced Files in This Document**
- [Dockerfile](file://Measure_plot_cpu_perf/Dockerfile)
- [run_perf_plot.sh](file://Measure_plot_cpu_perf/run_perf_plot.sh)
- [plot_perf_metrics.py](file://Measure_plot_cpu_perf/plot_perf_metrics.py)
- [Dockerfile.perf](file://monitor_hpe/Dockerfile.perf)
- [docker-compose.perf.yml](file://monitor_hpe/docker-compose.perf.yml)
- [monitor_pid.sh](file://monitor_hpe/monitor_pid.sh)
- [plot_graph.py](file://monitor_hpe/plot_graph.py)
- [run_experiment.sh](file://monitor_hpe/run_experiment.sh)
- [cpu_performance_optimizer.py](file://optimizations/cpu_performance_optimizer.py)
- [enhanced_openvino_hpe.py](file://optimizations/enhanced_openvino_hpe.py)
- [optimized_main.py](file://optimizations/optimized_main.py)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [monitor_pid.sh](file://ffmpeg_hpe/monitor_pid.sh)
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
This document describes a comprehensive CPU performance analysis and plotting toolkit built on Docker and Linux performance tools. It covers:
- A Docker-based environment for capturing CPU utilization and cycle metrics
- Scripts for launching performance measurements and generating plots
- A monitoring pipeline that tracks CPU, memory, and network metrics for a target process
- Integration with performance monitoring workflows and automated experiments
- Automated benchmarking and comparative analysis across CPU configurations
- Practical guidance for detecting performance regressions, validating optimizations, and tuning systems based on measured metrics

## Project Structure
The repository organizes performance tools by domain:
- Measure_plot_cpu_perf: Standalone CPU metric capture and plotting
- monitor_hpe: End-to-end monitoring of HPE workloads with Docker orchestration
- optimizations: CPU optimization utilities for OpenVINO-based HPE
- ffmpeg_hpe: Experiment automation integrating streaming, monitoring, and metrics collection

```mermaid
graph TB
subgraph "Measure_plot_cpu_perf"
MP_D["Dockerfile"]
MP_S["run_perf_plot.sh"]
MP_P["plot_perf_metrics.py"]
end
subgraph "monitor_hpe"
MH_D["Dockerfile.perf"]
MH_C["docker-compose.perf.yml"]
MH_M["monitor_pid.sh"]
MH_G["plot_graph.py"]
MH_R["run_experiment.sh"]
end
subgraph "optimizations"
O1["cpu_performance_optimizer.py"]
O2["enhanced_openvino_hpe.py"]
O3["optimized_main.py"]
end
subgraph "ffmpeg_hpe"
F_R["run_experiment.sh"]
F_M["monitor_pid.sh"]
end
MP_D --> MP_S --> MP_P
MH_C --> MH_M
MH_C --> MH_G
MH_C --> MH_R
O3 --> O2 --> O1
F_R --> F_M
```

**Diagram sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [run_perf_plot.sh:1-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L1-L25)
- [plot_perf_metrics.py:1-146](file://Measure_plot_cpu_perf/plot_perf_metrics.py#L1-L146)
- [Dockerfile.perf:1-19](file://monitor_hpe/Dockerfile.perf#L1-L19)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)
- [plot_graph.py:1-59](file://monitor_hpe/plot_graph.py#L1-L59)
- [run_experiment.sh:1-138](file://monitor_hpe/run_experiment.sh#L1-L138)
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)
- [enhanced_openvino_hpe.py:1-333](file://optimizations/enhanced_openvino_hpe.py#L1-L333)
- [optimized_main.py:1-257](file://optimizations/optimized_main.py#L1-L257)
- [run_experiment.sh:1-251](file://ffmpeg_hpe/run_experiment.sh#L1-L251)
- [monitor_pid.sh:1-151](file://ffmpeg_hpe/monitor_pid.sh#L1-L151)

**Section sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)

## Core Components
- CPU metric capture and plotting container:
  - Provides a Docker image with perf, Python, and plotting libraries
  - Runs perf against a target PID and generates plots and CSV
- Monitoring pipeline:
  - Orchestrated by Docker Compose to launch the monitored workload and the perf monitor
  - Captures CPU%, memory RSS, and network TX/RX for a target PID
  - Writes metrics to CSV and generates plots
- CPU optimization utilities:
  - Detects CPU capabilities and applies OpenVINO-specific tuning
  - Provides factory functions and benchmarking helpers
- Experiment automation:
  - Starts streaming server, workload, and monitoring
  - Aggregates logs, metrics, and artifacts into a timestamped results directory

**Section sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [run_perf_plot.sh:1-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L1-L25)
- [plot_perf_metrics.py:1-146](file://Measure_plot_cpu_perf/plot_perf_metrics.py#L1-L146)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)
- [plot_graph.py:1-59](file://monitor_hpe/plot_graph.py#L1-L59)
- [run_experiment.sh:1-138](file://monitor_hpe/run_experiment.sh#L1-L138)
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)
- [enhanced_openvino_hpe.py:1-333](file://optimizations/enhanced_openvino_hpe.py#L1-L333)
- [optimized_main.py:1-257](file://optimizations/optimized_main.py#L1-L257)
- [run_experiment.sh:1-251](file://ffmpeg_hpe/run_experiment.sh#L1-L251)
- [monitor_pid.sh:1-151](file://ffmpeg_hpe/monitor_pid.sh#L1-L151)

## Architecture Overview
The system combines Docker-based orchestration with Linux performance tools to collect and visualize CPU-centric metrics. Two complementary flows are available:
- Direct perf-based capture for a running PID
- Full-stack monitoring pipeline that captures CPU, memory, and network metrics for a target process

```mermaid
sequenceDiagram
participant User as "User"
participant DC as "Docker Compose"
participant HPE as "HPE Workload"
participant Mon as "Monitor (perf)"
participant Plot as "Plotter"
User->>DC : Start experiment
DC->>HPE : Launch workload container
DC->>Mon : Launch monitor container
Mon->>Mon : Read PID file and validate
Mon->>HPE : Attach to target PID
Mon->>Mon : Sample CPU%, Mem RSS, TX/RX (bpftrace)
Mon->>Mon : Write CSV periodically
Mon-->>User : CSV and plots on completion
Plot->>Plot : Generate plots from CSV
Plot-->>User : PNG and CSV outputs
```

**Diagram sources**
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)
- [plot_graph.py:1-59](file://monitor_hpe/plot_graph.py#L1-L59)

## Detailed Component Analysis

### CPU Metric Capture and Plotting Container
This component encapsulates perf-based CPU metrics capture and visualization:
- Installs perf and Python plotting libraries in a container
- Accepts a PID file and runs perf against the PID
- Parses perf output and produces plots and CSV

```mermaid
flowchart TD
Start(["Start"]) --> CheckPID["Check PID file exists"]
CheckPID --> |Missing| ExitErr["Exit with error"]
CheckPID --> |Present| ForEachPID["Iterate PIDs"]
ForEachPID --> PerfStat["Run perf stat for PID"]
PerfStat --> Parse["Parse perf output"]
Parse --> Plot["Generate plots and CSV"]
Plot --> End(["End"])
```

**Diagram sources**
- [run_perf_plot.sh:1-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L1-L25)
- [plot_perf_metrics.py:1-146](file://Measure_plot_cpu_perf/plot_perf_metrics.py#L1-L146)

**Section sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [run_perf_plot.sh:1-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L1-L25)
- [plot_perf_metrics.py:1-146](file://Measure_plot_cpu_perf/plot_perf_metrics.py#L1-L146)

### Monitoring Pipeline: CPU, Memory, and Network Metrics
This pipeline monitors a target process PID and exports metrics to CSV and plots:
- Reads PID from a mounted file
- Uses bpftrace to track TX/RX bytes per interval
- Periodically samples CPU% and memory RSS
- Writes synchronized CSV entries and generates plots

```mermaid
sequenceDiagram
participant Mon as "monitor_pid.sh"
participant PIDF as "PID File (/pids)"
participant Proc as "/proc PID"
participant BT as "bpftrace"
participant FS as "CSV Files"
Mon->>PIDF : Wait for PID file
PIDF-->>Mon : PID available
Mon->>Proc : Read CPU% and Mem RSS
Mon->>BT : Start TX/RX tracing
BT-->>Mon : TX/RX deltas every interval
Mon->>FS : Append metrics (thread-safe)
Mon-->>FS : Final CSV and plots
```

**Diagram sources**
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)
- [plot_graph.py:1-59](file://monitor_hpe/plot_graph.py#L1-L59)

**Section sources**
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)
- [plot_graph.py:1-59](file://monitor_hpe/plot_graph.py#L1-L59)

### CPU Optimization Utilities for OpenVINO HPE
These modules detect CPU capabilities and apply OpenVINO-specific tuning:
- Detects physical/logical cores, frequency, AVX support, and NUMA topology
- Calculates optimal thread counts, streams, and performance hints
- Applies system-level optimizations (CPU governor, power settings)
- Integrates with OpenVINO core configuration

```mermaid
classDiagram
class EPICCPUOptimizer {
+capabilities : CPUCapabilities
+optimal_config : Dict
+_detect_cpu_capabilities()
+_calculate_optimal_config()
+_tune_for_model(base_configs)
+configure_openvino_core(core)
+get_recommended_batch_size(model, resolution)
+optimize_system_settings()
}
class CPUCapabilities {
+physical_cores : int
+logical_cores : int
+base_frequency : float
+max_frequency : float
+cache_l3_mb : int
+numa_nodes : int
+architecture : str
+supports_avx2 : bool
+supports_avx512 : bool
}
EPICCPUOptimizer --> CPUCapabilities : "uses"
```

**Diagram sources**
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)

**Section sources**
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)
- [enhanced_openvino_hpe.py:1-333](file://optimizations/enhanced_openvino_hpe.py#L1-L333)
- [optimized_main.py:1-257](file://optimizations/optimized_main.py#L1-L257)

### Experiment Automation and Artifact Collection
The ffmpeg_hpe experiment orchestrator coordinates streaming, workload, and monitoring:
- Starts a streaming server and the HPE workload
- Measures container instantiation timing
- Copies performance data, traces, and logs to a timestamped results directory
- Supports GPU metrics and trace collection

```mermaid
flowchart TD
A["Start experiment"] --> B["Stop/remove existing containers"]
B --> C["Start streaming server"]
C --> D["Start HPE workload"]
D --> E["Start perf monitor and trace containers"]
E --> F["Wait for HPE to exit"]
F --> G["Collect logs and metrics"]
G --> H["Copy CSVs and traces"]
H --> I["Cleanup and report"]
```

**Diagram sources**
- [run_experiment.sh:1-251](file://ffmpeg_hpe/run_experiment.sh#L1-L251)

**Section sources**
- [run_experiment.sh:1-251](file://ffmpeg_hpe/run_experiment.sh#L1-L251)
- [monitor_pid.sh:1-151](file://ffmpeg_hpe/monitor_pid.sh#L1-L151)

## Dependency Analysis
Key dependencies and relationships:
- Dockerfiles define runtime environments for perf and monitoring
- Docker Compose orchestrates multi-container experiments
- Scripts depend on Linux tools (perf, bpftrace, ps, lscpu)
- Python modules rely on pandas, matplotlib, numpy, and OpenVINO APIs
- The optimization modules depend on psutil and platform detection

```mermaid
graph LR
DF1["Measure_plot_cpu_perf/Dockerfile"] --> PERF["perf"]
DF1 --> PY["Python libs"]
DF2["monitor_hpe/Dockerfile.perf"] --> BPF["bpftrace"]
DF2 --> PS["psutils"]
DC["monitor_hpe/docker-compose.perf.yml"] --> HPE["HPE workload"]
DC --> MON["Monitor (perf)"]
OPT["optimizations/cpu_performance_optimizer.py"] --> OV["OpenVINO"]
EXP["monitor_hpe/run_experiment.sh"] --> DC
EXP --> MON
```

**Diagram sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [Dockerfile.perf:1-19](file://monitor_hpe/Dockerfile.perf#L1-L19)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)

**Section sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [Dockerfile.perf:1-19](file://monitor_hpe/Dockerfile.perf#L1-L19)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)

## Performance Considerations
- Sampling intervals:
  - The monitoring pipeline samples every 500 ms and aggregates TX/RX every 10 ms internally
  - The standalone perf container samples at 100 ms intervals
- Throughput vs latency:
  - CPU optimization utilities select performance hints and thread/stream counts based on workload characteristics
- System-level tuning:
  - CPU governor and power management toggles can reduce latency spikes
- NUMA awareness:
  - Optimizer can set affinity and increase num_requests for multi-socket systems

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and remedies:
- Missing PID file:
  - The monitor waits up to 30 seconds; ensure the workload writes the PID file to the shared volume
- Permissions:
  - The perf container requires SYS_ADMIN, SYS_PTRACE, and IPC_LOCK capabilities
- bpftrace availability:
  - Ensure bpftrace is installed in the monitoring container
- CSV locking:
  - The monitor uses flock to serialize writes; verify lock files are cleaned up on exit
- Container naming conflicts:
  - The experiment script waits for container names to be fully released before cleanup

**Section sources**
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [run_experiment.sh:1-138](file://monitor_hpe/run_experiment.sh#L1-L138)

## Conclusion
This toolkit provides a repeatable, Dockerized workflow for CPU performance analysis:
- Capture CPU utilization and cycles with perf
- Monitor CPU, memory, and network metrics for a target process
- Integrate CPU optimization for OpenVINO-based HPE workloads
- Automate experiments and collect artifacts for comparative analysis
- Use the resulting plots and CSVs to detect regressions, validate optimizations, and guide system tuning

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### How to Measure CPU Utilization, Memory Usage, and System Metrics
- Perf-based capture:
  - Build and run the perf container; ensure a PID file exists; it will run perf against the PID and produce plots and CSV
- Full monitoring pipeline:
  - Start the HPE workload and monitor containers via Docker Compose; the monitor writes CSV and generates plots

**Section sources**
- [Dockerfile:1-18](file://Measure_plot_cpu_perf/Dockerfile#L1-L18)
- [run_perf_plot.sh:1-25](file://Measure_plot_cpu_perf/run_perf_plot.sh#L1-L25)
- [docker-compose.perf.yml:1-38](file://monitor_hpe/docker-compose.perf.yml#L1-L38)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)

### Comparative Analysis Across CPU Architectures
- Use the CPU optimizer to derive optimal thread/stream counts for different core counts
- Compare performance across experiments by organizing results in timestamped directories
- Validate improvements using the benchmark helper for OpenVINO models

**Section sources**
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)
- [enhanced_openvino_hpe.py:1-333](file://optimizations/enhanced_openvino_hpe.py#L1-L333)
- [optimized_main.py:1-257](file://optimizations/optimized_main.py#L1-L257)

### Performance Regression Detection and Optimization Validation
- Track FPS and throughput across runs; compare standard vs optimized configurations
- Use plots to visually inspect trends and anomalies
- Validate system tuning by comparing pre/post governor and power management settings

**Section sources**
- [optimized_main.py:1-257](file://optimizations/optimized_main.py#L1-L257)
- [monitor_pid.sh:1-204](file://monitor_hpe/monitor_pid.sh#L1-L204)

### System Tuning Recommendations
- Set CPU governor to performance mode when latency is critical
- Disable NUMA balancing and turbo boost toggles if they cause jitter
- Pin threads and disable hyper-threading for compute-bound inference on systems without HT
- Increase num_requests proportionally to streams for memory-bound models

**Section sources**
- [cpu_performance_optimizer.py:1-539](file://optimizations/cpu_performance_optimizer.py#L1-L539)