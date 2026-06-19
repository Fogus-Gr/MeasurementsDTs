# Metrics Collection

<cite>
**Referenced Files in This Document**
- [prometheus.yml](file://prometheus.yml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [monitor_pid.sh](file://monitor_hpe/monitor_pid.sh)
- [monitor_pid_perf.sh](file://shared/perf_monitor/monitor_pid_perf.sh)
- [validate_run.py](file://ffmpeg_hpe/validate_run.py)
- [plot_graph.py](file://ffmpeg_hpe/plot_graph.py)
- [plot_smi_output.py](file://ffmpeg_hpe/plot_smi_output.py)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [plot_rx_bytes_trimmed_reset.py](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py)
- [main.py](file://main.py)
- [openvino_base_hpe.py](file://openvino_base_hpe.py)
- [alphapose_hpe.py](file://alphapose_hpe.py)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive validation framework documentation with automated quality checks
- Enhanced GPU metrics collection with improved Docker Compose orchestration
- Expanded performance monitoring capabilities with new plotting utilities
- Integrated advanced validation scripts for result verification and quality assurance
- Updated monitoring infrastructure with enhanced BCC tracer integration

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced Validation Framework](#enhanced-validation-framework)
7. [Advanced Monitoring Capabilities](#advanced-monitoring-capabilities)
8. [Dependency Analysis](#dependency-analysis)
9. [Performance Considerations](#performance-considerations)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Conclusion](#conclusion)

## Introduction
This document describes the enhanced metrics collection infrastructure for the Human Pose Estimation (HPE) framework. The system now features an integrated validation framework, comprehensive performance monitoring, and advanced GPU metrics collection capabilities. It explains how GPU metrics are collected using NVIDIA SMI-based scripts, how Prometheus scrapes those metrics, and how Docker Compose orchestrates the HPE pipeline along with monitoring services. The enhanced system includes automated validation, comprehensive plotting utilities, and robust quality assurance mechanisms.

## Project Structure
The enhanced metrics collection spans multiple interconnected components:
- Prometheus configuration with dedicated scrape jobs for GPU metrics
- Docker Compose orchestration with improved service dependencies and resource management
- Comprehensive validation framework for automated quality assurance
- Advanced plotting utilities for metrics visualization
- Enhanced monitoring infrastructure with BCC tracer integration
- GPU metrics collection with improved Docker containerization
- CPU and network metrics collection with enhanced accuracy

```mermaid
graph TB
subgraph "Prometheus Stack"
P["Prometheus<br/>config: prometheus.yml"]
end
subgraph "HPE Pipeline"
HPE["HPE Application<br/>main.py"]
HPE_OV["OpenVINO HPE<br/>openvino_base_hpe.py"]
HPE_AP["AlphaPose HPE<br/>alphapose_hpe.py"]
end
subgraph "Enhanced Monitoring"
DCMG["DCGM Exporter<br/>scrape job: dcgm-exporter:9400"]
GMET["GPU Metrics Collector<br/>run_nvidia_dcgm.sh"]
PMH["Per-PID Monitor<br/>monitor_pid.sh"]
PMR["Perf Monitor<br/>monitor_pid_perf.sh"]
VALID["Validation Framework<br/>validate_run.py"]
PLOT["Plotting Utilities<br/>plot_graph.py, plot_smi_output.py"]
end
subgraph "Advanced Tracing"
BCC["BCC Tracer<br/>bcc-tracer"]
TRACES["Trace Output<br/>tracer_output/"]
end
HPE --> HPE_OV
HPE --> HPE_AP
HPE --> PMH
HPE --> PMR
GMET --> P
DCMG --> P
VALID --> HPE
PLOT --> VALID
BCC --> TRACES
```

**Diagram sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)
- [monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)
- [plot_graph.py:1-59](file://ffmpeg_hpe/plot_graph.py#L1-L59)

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)

## Core Components
- **Prometheus scrape configuration**: Defines dedicated jobs for GPU metrics with 500ms scrape intervals targeting dcgm-exporter:9400
- **Enhanced GPU metrics collection**: Containerized scripts with improved Docker orchestration, supporting environment-driven configuration for output directories, intervals, and durations
- **Comprehensive validation framework**: Automated quality assurance system validating HPE outputs, GPU metrics, performance data, and network traces
- **Advanced plotting utilities**: Multiple visualization scripts for metrics analysis and reporting
- **Improved Docker Compose orchestration**: Enhanced service dependencies, resource limits, health checks, and GPU runtime configuration
- **Enhanced CPU and network metrics**: Per-PID monitor with improved accuracy and perf monitor with comprehensive system-level metrics
- **BCC tracer integration**: Advanced network traffic tracing with container-specific monitoring capabilities

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [Dockerfile.gpu_metrics:1-20](file://ffmpeg_hpe/Dockerfile.gpu_metrics#L1-L20)
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)
- [monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)

## Architecture Overview
The enhanced system integrates comprehensive GPU metrics collection, automated validation, and advanced monitoring into the HPE experiment pipeline. The architecture now includes a validation framework that automatically verifies experiment quality and generates detailed reports.

```mermaid
sequenceDiagram
participant User as "Operator"
participant DC as "Docker Compose"
participant HPE as "HPE Container"
participant GM as "GPU Metrics Collector"
participant PM as "Per-PID Monitor"
participant PR as "Prometheus"
participant VAL as "Validation Framework"
User->>DC : Start enhanced stack
DC->>HPE : Launch HPE with env vars
DC->>GM : Launch GPU metrics container
DC->>PM : Launch per-PID monitor
GM->>GM : Log GPU metrics to CSV
PM->>PM : Collect CPU/RSS/TX/RX for target PID
PR->>PR : Scrape job "dcgm-exporter" at 500ms
PR-->>PR : Store metrics in TSDB
VAL->>VAL : Validate results automatically
VAL-->>User : Generate quality report
```

**Diagram sources**
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)

## Detailed Component Analysis

### Prometheus Configuration
- **Scrape interval**: Globally set to 500ms for optimal GPU metrics resolution
- **Job configuration**: Dedicated job named "dcgm-exporter" configured to scrape dcgm-exporter:9400 with 500ms interval
- **Exporter alignment**: Ensures scrape intervals match GPU metrics collection timing for consistent data

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)

### Enhanced GPU Metrics Collector (Containerized)
- **Purpose**: Periodically query GPU metrics via NVIDIA SMI and write to CSV with improved error handling
- **Key improvements**:
  - Enhanced environment variable support with defaults for output directory, interval, and duration
  - Improved signal handling with proper cleanup procedures
  - Robust CSV header creation and validation
  - Background monitoring loop with graceful shutdown capabilities
  - Real-time timestamp generation with nanosecond precision
- **Output format**: CSV containing timestamp, GPU ID, utilization percentage, memory utilization, temperature, and power usage

```mermaid
flowchart TD
Start(["Start"]) --> CheckEnv["Read env: OUTPUT_DIR, INTERVAL, DURATION"]
CheckEnv --> InitCSV["Write CSV header"]
InitCSV --> Loop{"Duration reached?"}
Loop --> |No| Query["Run nvidia-smi query"]
Query --> Parse["Parse CSV lines per GPU"]
Parse --> Write["Append row to CSV"]
Write --> Sleep["Sleep INTERVAL"]
Sleep --> Loop
Loop --> |Yes| Cleanup["Stop background loop and exit"]
Cleanup --> End(["End"])
```

**Diagram sources**
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)

**Section sources**
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [Dockerfile.gpu_metrics:1-20](file://ffmpeg_hpe/Dockerfile.gpu_metrics#L1-L20)

### Enhanced Docker Compose Orchestration
- **Service enhancements**:
  - Improved GPU runtime configuration with NVIDIA_VISIBLE_DEVICES and CUDA_VISIBLE_DEVICES
  - Enhanced resource management with CPU and memory limits/reservations
  - Advanced health checks for all services with appropriate intervals and timeouts
  - Streamlined environment variables for HPE optimization (OpenVINO tuning, threading)
  - Enhanced networking with shared bridge network and DNS configuration
- **Security improvements**:
  - No-new-privileges settings and read-only filesystem configurations
  - Privileged mode for BCC tracer with specific capability additions
  - SYS_ADMIN, NET_ADMIN, NET_RAW capabilities for monitoring functions
- **Service dependencies**: Enhanced dependency chains ensuring proper startup order

```mermaid
graph TB
subgraph "Network"
N["streaming-network"]
end
H264["h264-streaming-server"] --> N
HPE["hpe"] --> N
GM["gpu-metrics"] --> N
PM["perf_monitor"] --> N
BT["bcc-tracer"] --> N
HPE --> H264
GM --> H264
GM --> HPE
PM --> H264
PM --> HPE
BT --> HPE
```

**Diagram sources**
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)

**Section sources**
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)

### Enhanced Per-PID Monitor (CPU/RAM/TX/RX)
- **Purpose**: Export comprehensive CPU percentage, RSS memory, and TX/RX bytes for target PID to CSV with improved accuracy
- **Enhanced features**:
  - Atomic file writing with flock-based locking for thread safety
  - Improved bpftrace integration with 10ms sampling intervals
  - Enhanced FIFO-based communication for network statistics
  - Comprehensive error handling and cleanup procedures
  - PID file timeout handling with graceful degradation
- **Output formats**:
  - pid_metrics.csv: timestamp, pid, cpu_percent, mem_rss_kb, tx_bytes, rx_bytes
  - network_stats.csv: timestamp, pid, interface, bytes, sent flag indicators

```mermaid
sequenceDiagram
participant Mon as "monitor_pid.sh"
participant BPF as "bpftrace"
participant FS as "CSV Files"
Mon->>Mon : Initialize CSV headers with locks
Mon->>Mon : Wait for TARGET_PID_FILE with timeout
Mon->>Mon : Read PID from file
Mon->>BPF : Start TX/RX rate computation (10ms)
loop Every 500ms
Mon->>Mon : Read CPU% and RSS with delta calculation
Mon->>FS : Write pid_metrics.csv (atomic with flock)
end
BPF-->>Mon : Emit TX/RX bytes via FIFO
Mon->>FS : Write network_stats.csv (atomic with flock)
```

**Diagram sources**
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)

**Section sources**
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)

### Enhanced Perf Monitor (Aggregate CPU/Memory)
- **Purpose**: Aggregate total CPU and RSS across monitored PIDs at configurable intervals with improved accuracy
- **Enhanced capabilities**:
  - Configurable monitoring intervals via INTERVAL environment variable
  - Comprehensive PID file handling with multiple PID support
  - Enhanced CPU tick calculations using precise timing measurements
  - Improved memory aggregation with RSS tracking
  - Active PID counting and system resource monitoring
- **Output**: perf_metrics.csv with timestamp, total_cpu_percent, total_mem_rss_kb, and active_pids

**Section sources**
- [monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)

### HPE Application Metrics Integration
- **Enhanced configuration**: Improved argument parsing and environment variable handling
- **Optimized performance**: Advanced OpenVINO backend tuning with CPU optimization flags
- **Flexible deployment**: Support for multiple HPE methods (OpenVINO, AlphaPose) with unified metrics collection
- **Measurement integration**: Configurable measurement intervals for data volume tracking

```mermaid
classDiagram
class Main {
+parse_arguments()
+get_hpe_method(args)
+main()
}
class OpenVINOBaseHPE {
+load_model()
+run_model(padded)
+postprocess(predictions)
+main_loop()
}
class AlphaPoseHPE {
+load_model()
+run_model(frame_input)
+postprocess(predictions)
+set_padding()
+pad_and_resize(frame)
}
Main --> OpenVINOBaseHPE : "selects"
Main --> AlphaPoseHPE : "selects"
```

**Diagram sources**
- [main.py:1-99](file://main.py#L1-L99)
- [openvino_base_hpe.py:1-653](file://openvino_base_hpe.py#L1-L653)
- [alphapose_hpe.py:1-334](file://alphapose_hpe.py#L1-L334)

**Section sources**
- [main.py:1-99](file://main.py#L1-L99)
- [openvino_base_hpe.py:1-653](file://openvino_base_hpe.py#L1-L653)
- [alphapose_hpe.py:1-334](file://alphapose_hpe.py#L1-L334)

## Enhanced Validation Framework
The system now includes a comprehensive validation framework that automatically verifies experiment quality and generates detailed reports.

### Validation Components
- **HPE Exit Code Validation**: Checks container exit codes for successful completion
- **Log Analysis**: Parses HPE logs for processed frame counts and FFmpeg statistics
- **JSON Output Validation**: Validates HPE JSON output CSV structure and frame sequencing
- **Network Trace Validation**: Compares BCC RX traffic with FFmpeg bytes-read within configurable tolerances
- **Performance Metrics Validation**: Verifies CPU utilization, memory usage, and active PID counts
- **GPU Metrics Validation**: Ensures GPU metrics CSV integrity and plausibility

### Quality Assurance Features
- **Configurable Tolerances**: Adjustable thresholds for RX tolerance, minimum CPU percent, and memory requirements
- **Automated Reporting**: Generates JSON and text validation reports with detailed metrics
- **Multi-criteria Validation**: Comprehensive checks across all monitoring components
- **Threshold-based Verification**: Plausible value validation with statistical analysis

**Section sources**
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)

## Advanced Monitoring Capabilities
The enhanced system provides comprehensive monitoring with specialized plotting utilities.

### Plotting Infrastructure
- **General Metrics Plotting**: [plot_graph.py](file://ffmpeg_hpe/plot_graph.py) - Creates CPU and memory usage visualizations
- **GPU Metrics Visualization**: [plot_smi_output.py](file://ffmpeg_hpe/plot_smi_output.py) - Specialized GPU utilization and temperature plots
- **Network Traffic Analysis**: [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py) and [plot_rx_bytes_trimmed_reset.py](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py) - Advanced RX traffic analysis with trimming and time-zeroing capabilities

### Monitoring Enhancements
- **Real-time Processing**: Continuous metrics collection with immediate CSV output
- **Atomic File Operations**: Thread-safe CSV writing with flock-based locking
- **Enhanced Error Handling**: Graceful degradation and cleanup procedures
- **Configurable Intervals**: Flexible sampling intervals for different monitoring needs

**Section sources**
- [plot_graph.py:1-59](file://ffmpeg_hpe/plot_graph.py#L1-L59)
- [plot_smi_output.py:1-21](file://ffmpeg_hpe/plot_smi_output.py#L1-L21)
- [plot_rx_bytes.py:1-33](file://ffmpeg_hpe/plot_rx_bytes.py#L1-L33)
- [plot_rx_bytes_trimmed_reset.py:1-38](file://ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py#L1-L38)

## Dependency Analysis
The enhanced system maintains clear dependency relationships while adding new validation and monitoring capabilities.

- **Prometheus dependencies**: Requires properly configured scrape jobs and reachable exporter endpoints
- **GPU metrics dependencies**: Relies on NVIDIA drivers, nvidia-smi availability, and proper container runtime configuration
- **Validation framework dependencies**: Depends on all monitoring components and experiment output files
- **Plotting utilities dependencies**: Requires Python environment with pandas and matplotlib libraries
- **BCC tracer dependencies**: Needs kernel tracing capabilities and proper privilege configuration

```mermaid
graph LR
PR["Prometheus"] --> CFG["prometheus.yml"]
GM["GPU Metrics Collector"] --> NSMI["nvidia-smi"]
PMH["Per-PID Monitor"] --> BPF["bpftrace"]
PMR["Perf Monitor"] --> PS["pidstat"]
HPE["HPE App"] --> CAP["OpenCV/FFmpeg"]
HPE --> OV["OpenVINO"]
HPE --> AP["AlphaPose"]
VAL["Validation Framework"] --> HPE
VAL --> GM
VAL --> PMH
VAL --> PMR
PLOT["Plotting Utilities"] --> VAL
```

**Diagram sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)
- [monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)
- [monitor_pid_perf.sh:1-107](file://shared/perf_monitor/monitor_pid_perf.sh#L1-L107)
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)

## Performance Considerations
The enhanced system provides optimized performance monitoring with careful consideration of overhead and accuracy.

### Optimization Strategies
- **Scraping interval synchronization**: Prometheus scrape interval (500ms) aligned with GPU metrics collection for optimal data consistency
- **Monitoring overhead minimization**:
  - Per-PID monitor with 10ms bpftrace sampling and 500ms CSV writing reduces I/O contention
  - Perf monitor uses 1-second intervals for aggregated metrics minimizing overhead
  - Atomic file operations prevent data corruption while maintaining performance
- **Resource allocation**: CPU and memory limits on monitoring containers prevent interference with HPE workloads
- **GPU runtime optimization**: Proper NVIDIA runtime configuration and device visibility for optimal GPU metrics collection
- **Validation efficiency**: Automated validation runs post-experiment to avoid real-time performance impact

### Scalability Considerations
- **Modular design**: Independent monitoring components can be scaled separately
- **Configurable intervals**: Adjustable sampling frequencies for different performance requirements
- **Resource isolation**: Separate containers for different monitoring functions prevent resource conflicts

## Troubleshooting Guide
Enhanced troubleshooting guidance for the expanded monitoring infrastructure.

### Prometheus and Exporter Issues
- **Scrape failures**: Verify scrape job configuration matches exporter endpoint and network connectivity
- **Metric gaps**: Ensure scrape intervals align with collection intervals to prevent data loss
- **Exporter unavailability**: Check exporter health and network accessibility from Prometheus container

### GPU Metrics Collection Problems
- **Driver compatibility**: Verify NVIDIA drivers and CUDA toolkit compatibility with container runtime
- **Container configuration**: Ensure proper NVIDIA runtime setup and device visibility
- **Permission issues**: Check container capabilities and security settings for GPU access
- **Metrics file problems**: Validate output directory permissions and CSV file integrity

### Validation Framework Issues
- **Missing validation reports**: Check experiment directory structure and file permissions
- **Validation failures**: Review threshold settings and adjust tolerances based on hardware capabilities
- **Incomplete validation**: Ensure all monitoring components are running and producing output files

### Monitoring Component Problems
- **Per-PID monitor failures**: Verify TARGET_PID_FILE existence and process visibility
- **BCC tracer issues**: Check kernel tracing capabilities and privilege configuration
- **Plotting errors**: Ensure Python dependencies (pandas, matplotlib) are available in plotting containers

### Performance Optimization
- **High monitoring overhead**: Adjust sampling intervals and consider component consolidation
- **Resource contention**: Review container resource limits and optimize allocation
- **Data consistency**: Verify atomic file operations and proper cleanup procedures

**Section sources**
- [prometheus.yml:1-8](file://prometheus.yml#L1-L8)
- [run_nvidia_dcgm.sh:1-86](file://ffmpeg_hpe/run_nvidia_dcgm.sh#L1-L86)
- [monitor_pid.sh:1-216](file://monitor_hpe/monitor_pid.sh#L1-L216)
- [docker-compose.yaml:1-206](file://ffmpeg_hpe/docker-compose.yaml#L1-L206)
- [validate_run.py:1-521](file://ffmpeg_hpe/validate_run.py#L1-L521)

## Conclusion
The enhanced HPE metrics collection infrastructure provides comprehensive monitoring, validation, and analysis capabilities. The integration of automated validation, advanced plotting utilities, and improved Docker orchestration creates a robust system for performance monitoring and quality assurance. Operators can leverage the enhanced framework to achieve reliable, low-overhead monitoring of GPU utilization, memory usage, thermal metrics, and system-level performance during HPE experiments, with automated quality verification and detailed reporting capabilities.