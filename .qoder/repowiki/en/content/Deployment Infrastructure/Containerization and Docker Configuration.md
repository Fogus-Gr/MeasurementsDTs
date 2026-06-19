# Containerization and Docker Configuration

<cite>
**Referenced Files in This Document**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [run_experiment_bcc.sh](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/run_experiment_bcc.sh)
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)
- [bcc_rx_bytes.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [Dockerfile](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/Dockerfile)
- [docker_stats_monitor.py](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/docker_stats_monitor.py)
- [monitor_pid_perf.sh](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/monitor_pid_perf.sh)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [Dockerfile](file://rtsp-ipcam/Dockerfile)
- [start_server.sh](file://rtsp-ipcam/start_server.sh)
- [Dockerfile](file://monitor_hpe/Dockerfile)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [Dockerfile.hpe](file://Dockerfile.hpe)
- [prometheus.yml](file://prometheus.yml)
- [docker-compose.yml](file://docker-compose.yml)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive documentation for the new ffmpeg_hpe_backup_20260618 framework with enhanced Docker orchestration
- Expanded BPF tracing capabilities with detailed BCC tracer implementation and validation system
- Introduced comprehensive experiment validation system with automated quality assurance
- Enhanced performance monitoring with Docker API-based metrics collection
- Updated container networking and service dependencies to support the new backup framework

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
This document explains the containerization and Docker configuration used to orchestrate streaming, inference, and observability services. It covers:
- Docker Compose architecture for orchestrating multiple services including a streaming server, a Human Pose Estimation (HPE) application, GPU metrics collector, performance monitor, and a BPF-based traffic tracer.
- Container networking, port mappings, and service dependencies.
- Dockerfile configuration for the HPE application, including base images, environment variables, and runtime dependencies.
- Entrypoint script functionality and container startup procedures.
- **NEW**: Enhanced Docker orchestration framework with ffmpeg_hpe_backup_20260618 for comprehensive experiment management.
- **NEW**: Expanded BPF tracing capabilities with detailed traffic monitoring and validation system.
- **NEW**: Comprehensive experiment validation system with automated quality assurance and reporting.
- Best practices for container resource allocation, GPU passthrough, and production deployment considerations.
- Examples of scaling services and managing container lifecycles.

## Project Structure
The repository organizes containerization artifacts primarily under:
- ffmpeg_hpe: streaming pipeline, GPU metrics, and BPF tracer services
- **NEW**: ffmpeg_hpe_backup_20260618: Enhanced orchestration framework with experiment management and validation
- **NEW**: shared/perf_monitor: Advanced performance monitoring with Docker API integration
- recent-dash: HTTP server, proxy, client, and mpv media player for DASH streaming experiments
- rtsp-ipcam: H.264 streaming server
- monitor_hpe: monitoring utilities and PID tracking
- Root-level Dockerfiles and compose files for top-level services

```mermaid
graph TB
subgraph "ffmpeg_hpe_backup_20260618"
A["docker-compose.yaml"]
B["run_experiment_bcc.sh"]
C["validate_run.py"]
D["bcc_rx_bytes.py"]
E["Dockerfile.bcc"]
end
subgraph "shared/perf_monitor"
F["Dockerfile"]
G["docker_stats_monitor.py"]
H["monitor_pid_perf.sh"]
end
subgraph "ffmpeg_hpe"
I["docker-compose.yaml"]
J["Dockerfile.gpu_metrics"]
K["entrypoint.sh"]
L["run_nvidia_dcgm.sh"]
end
subgraph "recent-dash"
M["docker-compose.yml"]
N["HTTP-Server.Dockerfile"]
O["HTTP-Proxy.Dockerfile"]
P["HTTP-Client.Dockerfile"]
Q["mpv-entrypoint.sh"]
R["Dockerfile_mpv"]
end
subgraph "rtsp-ipcam"
S["docker-compose.yml"]
T["Dockerfile"]
U["start_server.sh"]
end
subgraph "monitor_hpe"
V["Dockerfile"]
W["docker-compose.yaml"]
end
X["Dockerfile.hpe"]
Y["prometheus.yml"]
Z["docker-compose.yml (root)"]
A --> B
A --> C
A --> D
A --> E
F --> G
F --> H
I --> J
I --> K
I --> L
M --> N
M --> O
M --> P
M --> Q
M --> R
S --> T
S --> U
W --> V
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [run_experiment_bcc.sh](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/run_experiment_bcc.sh)
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)
- [bcc_rx_bytes.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [Dockerfile](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/Dockerfile)
- [docker_stats_monitor.py](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/docker_stats_monitor.py)
- [monitor_pid_perf.sh](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/monitor_pid_perf.sh)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [Dockerfile](file://rtsp-ipcam/Dockerfile)
- [start_server.sh](file://rtsp-ipcam/start_server.sh)
- [Dockerfile](file://monitor_hpe/Dockerfile)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [Dockerfile.hpe](file://Dockerfile.hpe)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)

## Core Components
- H.264 streaming server: Provides an HTTP H.264 stream for downstream consumers.
- HPE application: Performs pose estimation on the stream; supports GPU acceleration and configurable device selection.
- GPU metrics collector: Gathers GPU utilization and telemetry periodically.
- Performance monitor: Monitors host-level processes and system resources using Docker API integration.
- BPF tracer: Captures and logs network traffic related to the HPE pipeline using BCC/BPF with advanced validation.
- **NEW**: Enhanced orchestration framework: Comprehensive experiment management with automated validation and reporting.
- **NEW**: Advanced performance monitoring: Docker API-based metrics collection with real-time CPU, memory, and PID tracking.
- **NEW**: Experiment validation system: Automated quality assurance with comprehensive data validation and reporting.
- **NEW**: Backup framework: ffmpeg_hpe_backup_20260618 provides enhanced orchestration and experiment management capabilities.

Key orchestration highlights:
- Services share a dedicated bridge network for isolated communication.
- Health checks ensure readiness before dependent services start.
- Resource limits and reservations are configured for predictable performance.
- GPU passthrough is enabled via NVIDIA runtime and environment variables.
- **NEW**: Enhanced experiment orchestration with automated timing, diagnostics, and validation.
- **NEW**: Comprehensive BPF tracing with port detection and traffic validation capabilities.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)

## Architecture Overview
The orchestration centers on a shared network and a strict startup order:
- h264-streaming-server starts first and is probed for readiness.
- hpe depends on the streaming server being healthy and sets environment variables to consume the stream.
- gpu-metrics runs alongside hpe to collect GPU telemetry.
- perf_monitor and bcc-tracer operate independently but can observe the pipeline.
- **NEW**: Enhanced orchestration framework manages complete experiment lifecycle with validation.
- **NEW**: Advanced performance monitoring provides real-time container metrics via Docker API.

```mermaid
graph TB
subgraph "Network: streaming-network"
S["h264-streaming-server"]
H["hpe"]
G["gpu-metrics"]
P["perf_monitor"]
T["bcc-tracer"]
end
subgraph "Network: backup-framework"
BE["backup-experiment-manager"]
BV["validation-system"]
BT["traffic-tracer"]
end
subgraph "Network: dash-caching_network"
DS["http_server"]
DP["http_proxy"]
DC["http_client"]
DM["mpv_player"]
end
S --> |"Stream"| H
H --> |"GPU Telemetry"| G
H --> |"System Metrics"| P
H --> |"Traffic Tracing"| T
BE --> |"Experiment Control"| H
BV --> |"Quality Assurance"| H
BT --> |"Traffic Monitoring"| T
DS --> |"DASH Segments"| DP
DP --> |"Cached/Forwarded"| DC
DC --> |"Manifest"| DM
DM --> |"Automated Playback"| DS
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Detailed Component Analysis

### Enhanced Orchestration Framework (ffmpeg_hpe_backup_20260618)
- **NEW**: Comprehensive experiment management with automated lifecycle control.
- **NEW**: Advanced timing and diagnostics collection for performance analysis.
- **NEW**: Integrated validation system with automated quality assurance.
- **NEW**: Enhanced BPF tracing with port detection and traffic validation.
- **NEW**: Structured results organization with timestamped directories and comprehensive metadata.

Key features:
- Automated container startup and shutdown with precise timing measurements.
- Comprehensive diagnostics collection including container logs and system state.
- Integrated validation system with automated quality checks and reporting.
- Enhanced BPF tracing with automatic port detection and traffic validation.
- Structured results organization with timestamped directories and comprehensive metadata.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [run_experiment_bcc.sh](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/run_experiment_bcc.sh)
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)

### H.264 Streaming Server
- Purpose: Serve an H.264 stream over HTTP for real-time consumption.
- Networking: Exposes a configurable port and mounts a video directory.
- Security: Non-root user, read-only root filesystem, and temporary filesystem for /tmp.
- Healthcheck: Validates HTTP endpoint availability.
- Resource limits: CPU/memory limits and reservations for controlled resource usage.

Operational notes:
- Port mapping is configurable via environment variables.
- Volume mounts enable flexible video source configuration.

**Section sources**
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [Dockerfile](file://rtsp-ipcam/Dockerfile)
- [start_server.sh](file://rtsp-ipcam/start_server.sh)

### HPE Application (Human Pose Estimation)
- Purpose: Consume the H.264 stream and perform pose estimation with optional OpenVINO and PyTorch backends.
- GPU Passthrough: Uses NVIDIA runtime and visible device configuration.
- Environment Variables: Controls input stream URL, device selection, timeouts, and buffer sizes.
- Shared Memory: Configured for large model requirements.
- Startup Command: Executes the main application with method, input, CSV output, and measurement interval parameters.
- Entrypoint Behavior: Conditionally starts GPU metrics in the background and executes the main command.

Runtime configuration highlights:
- Device selection and CUDA visibility are explicitly set.
- FFMPEG timeouts are increased to accommodate long streams.
- Healthcheck monitors the main process.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [Dockerfile.hpe](file://Dockerfile.hpe)

### GPU Metrics Collector
- Purpose: Periodically collect GPU telemetry (utilization, memory, temperature, power) and write to CSV.
- Image: NVIDIA CUDA base image with NVIDIA utilities.
- Execution: Runs a monitoring script that queries GPU statistics at a configurable interval.
- Output: Writes CSV data to a mounted output directory.

Operational notes:
- Supports duration-limited runs and graceful shutdown via signal handling.
- Designed to run in parallel with the HPE workload.

**Section sources**
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)

### Advanced Performance Monitor (Enhanced)
- **NEW**: Docker API-based performance monitoring with real-time metrics collection.
- **NEW**: Comprehensive CPU, memory, and PID tracking with Docker socket integration.
- **NEW**: Automatic container discovery and monitoring with configurable intervals.
- **NEW**: Structured CSV output with detailed performance metrics and container identification.

Key features:
- Real-time Docker API integration for container metrics collection.
- Automatic target container discovery and monitoring.
- Comprehensive performance metrics including CPU percentage, memory usage, and active PIDs.
- Structured CSV output with timestamped entries and container metadata.
- Configurable monitoring intervals and output directories.

**Section sources**
- [Dockerfile](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/Dockerfile)
- [docker_stats_monitor.py](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/docker_stats_monitor.py)
- [monitor_pid_perf.sh](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/monitor_pid_perf.sh)

### Enhanced BPF Tracer (Expanded Capabilities)
- **NEW**: Advanced BPF tracing with automatic port detection and traffic validation.
- **NEW**: Comprehensive traffic monitoring with configurable sampling intervals.
- **NEW**: Structured CSV output with timestamped RX byte measurements.
- **NEW**: Robust error handling and validation with detailed logging.

Key features:
- Automatic port detection and streamer IP discovery.
- Configurable sampling intervals with environment variable support.
- Structured CSV output with timestamp, delta, cumulative, and time delta measurements.
- Robust error handling with detailed logging and validation.
- Raw socket filtering with BCC for low-level network traffic capture.

**Section sources**
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)

### Comprehensive Experiment Validation System (NEW)
- **NEW**: Automated quality assurance with comprehensive data validation.
- **NEW**: Multi-level validation including exit codes, log parsing, and metric consistency.
- **NEW**: Detailed reporting with PASS/FAIL status and comprehensive metrics.
- **NEW**: Configurable thresholds for performance and validation criteria.

Validation levels:
- HPE container exit code validation (must be 0).
- Log parsing for processed frames and FFmpeg bytes read.
- JSON CSV validation for structural integrity and sequential frame numbering.
- TX CSV validation for payload byte consistency.
- BCC RX validation with configurable tolerance for byte comparison.
- Performance metrics validation with CPU and memory thresholds.
- GPU metrics validation for telemetry consistency.

**Section sources**
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)

### Recent-DASH Infrastructure (Alternative Orchestration)
- Purpose: Complete DASH streaming pipeline with HTTP server, proxy, client, and automated media playback.
- Services: http_server, http_proxy, http_client, mpv, perf_monitor, and a containerized BPF tracer.
- Networking: Dedicated bridge network with static IP assignments for predictable service discovery.
- **NEW**: Enhanced orchestration with automated DASH segment fetching and continuous playback capabilities.
- **NEW**: Environment variable-driven configuration for warmup delays, retry intervals, and playback timing.
- Entrypoints: Launch scripts manage process lifecycle and PID tracking.

**Section sources**
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)

### MPV Media Player Service (NEW)
- Purpose: Automated DASH streaming playback with continuous loop and intelligent error recovery.
- **NEW**: Built on Debian slim base with mpv and curl dependencies for reliable playback.
- **NEW**: Intelligent warmup mechanism that waits for DASH manifest availability before starting playback.
- **NEW**: Configurable retry delays, warmup periods, and start delays through environment variables.
- **NEW**: Continuous playback loop with automatic restart on failures and detailed logging.
- **NEW**: Minimal resource footprint with null video/audio outputs for headless operation.

Environment Variable Configuration:
- `DASH_PLAYER_URL`: URL of the DASH manifest (defaults to http://http_client/manifest.mpd)
- `DASH_PLAYER_WARMUP_SECONDS`: Warmup period before checking manifest availability (default: 30s)
- `DASH_PLAYER_RETRY_DELAY_SECONDS`: Delay between retry attempts (default: 1s)
- `DASH_PLAYER_START_DELAY_SECONDS`: Delay before starting mpv playback (default: 5s)

Operational Features:
- Manifest availability validation using curl with timeout constraints
- Infinite loop playback with automatic restart on process exit
- Comprehensive logging with last 40 lines captured on restart
- Null output devices for headless operation (no GUI required)
- DASH demuxer format specification for proper segment handling

**Section sources**
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)

### HTTP Server, Proxy, and Client Services (Enhanced)
- **HTTP Server**: Serves DASH video segments with configurable caching parameters and CDN-like behavior.
- **HTTP Proxy**: Implements caching logic with configurable algorithms and rate limiting parameters.
- **HTTP Client**: Acts as the DASH player frontend, exposing the manifest and handling proxy forwarding.
- **NEW**: Integrated volume mounting for segment management and automated asset provisioning.

Service Configuration Highlights:
- Multi-stage Docker builds for optimized image sizes
- Environment variable-driven configuration for all services
- Static IP assignments within the dedicated bridge network
- Resource limits and CPU/memory constraints for predictable performance
- Launch scripts handle domain resolution and service initialization

**Section sources**
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [HTTP-Server.launch.sh](file://recent-dash/HTTP-Server.launch.sh)
- [HTTP-Proxy.launch.sh](file://recent-dash/HTTP-Proxy.launch.sh)
- [HTTP-Client.launch.sh](file://recent-dash/HTTP-Client.launch.sh)

## Dependency Analysis
Inter-service dependencies and startup order:
- hpe depends on h264-streaming-server being healthy.
- gpu-metrics and perf_monitor can start independently but benefit from the pipeline being active.
- bcc-tracer depends on the HPE container's network namespace and detects HPE's outbound connection to the streamer.
- **NEW**: Enhanced orchestration framework manages complete experiment lifecycle with validation.
- **NEW**: Performance monitor uses Docker API for real-time metrics collection.
- **NEW**: BPF tracer operates independently with automatic port detection capabilities.
- **NEW**: Validation system runs after experiment completion for quality assurance.

```mermaid
graph LR
H264["h264-streaming-server"] --> HPE["hpe"]
HPE --> GPU["gpu-metrics"]
HPE --> PERF["perf_monitor"]
HPE --> BPF["bcc-tracer"]
BACKUP["backup-experiment-manager"] --> HPE
BACKUP --> GPU
BACKUP --> PERF
BACKUP --> BPF
VALIDATION["validation-system"] --> BACKUP
HTTP_SERVER["http_server"] --> HTTP_PROXY["http_proxy"]
HTTP_PROXY --> HTTP_CLIENT["http_client"]
HTTP_CLIENT --> MPV["mpv"]
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Performance Considerations
- Resource Allocation:
  - CPU and memory limits and reservations are defined per service to prevent noisy-neighbor effects.
  - HPE uses significant shared memory to support model inference.
  - **NEW**: Enhanced orchestration framework provides precise timing measurements for resource optimization.
  - **NEW**: Docker API-based performance monitoring offers real-time resource utilization insights.
- GPU Passthrough:
  - NVIDIA runtime and environment variables ensure the HPE container sees the correct GPU(s).
  - Device reservations are configured for guaranteed GPU access.
- Observability:
  - Healthchecks provide early failure detection.
  - GPU metrics and BPF tracing offer deep insights into throughput and bottlenecks.
  - **NEW**: Comprehensive validation system ensures data quality and experiment reliability.
  - **NEW**: Docker API monitoring provides detailed container-level performance metrics.
- FFMPEG Tuning:
  - Increased timeouts reduce premature failures on long streams.
- Security Hardening:
  - Non-root users, read-only root filesystems, and temporary filesystems for /tmp improve isolation.
- **NEW**: Enhanced Experiment Management:
  - Structured results organization with timestamped directories.
  - Comprehensive diagnostics collection for troubleshooting.
  - Automated validation ensures experiment quality and reproducibility.
  - Configurable sampling intervals for BPF tracing optimization.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Troubleshooting Guide
Common issues and remedies:
- HPE fails to start or exits quickly:
  - Verify the streaming server is healthy and reachable.
  - Confirm environment variables for input URL and device selection are correct.
  - Check GPU visibility and NVIDIA runtime configuration.
- GPU metrics container does not produce output:
  - Ensure NVIDIA drivers and utilities are present in the container.
  - Validate output directory permissions and mount points.
- BPF tracer cannot detect HPE port:
  - Confirm the tracer shares the HPE network namespace.
  - Verify the default interface is correctly detected and accessible.
  - Check that HPE establishes an outbound connection to the streamer before the tracer starts.
  - **NEW**: Check BPF tracer logs for port detection messages and validation errors.
- **NEW**: Enhanced orchestration framework issues:
  - Verify experiment script has proper permissions and dependencies.
  - Check container timing measurements for startup delays and initialization issues.
  - Review validation reports for specific quality assurance failures.
- **NEW**: Performance monitor Docker API errors:
  - Ensure Docker socket is properly mounted (/var/run/docker.sock).
  - Verify target container name matches the monitored container.
  - Check Docker API accessibility and permissions.
- **NEW**: Validation system failures:
  - Review validation report for specific check failures and metrics.
  - Verify required files exist in results directory (JSON, TX, BCC, perf, GPU).
  - Check threshold values and adjust validation criteria if needed.
- **NEW**: mpv service fails to start DASH playback:
  - Verify the DASH manifest is available at the expected URL (http://http_client/manifest.mpd).
  - Check network connectivity between mpv and http_client services.
  - Review mpv logs for detailed error information (last 40 lines captured on restart).
  - Adjust warmup and retry delays if the manifest takes longer to generate.
- **NEW**: DASH pipeline service dependencies:
  - Ensure http_server is fully initialized before http_proxy starts.
  - Verify http_proxy can reach http_server on the configured port.
  - Check that http_client has successfully mounted the DASH manifest file.
- Port conflicts or accessibility:
  - Review port mappings and ensure host ports are free.
  - Validate firewall and network policies in the environment.
  - **NEW**: Check that the mpv service port is not conflicting with other services.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [run_experiment_bcc.sh](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/run_experiment_bcc.sh)
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Conclusion
The containerization setup provides a robust, observable, and scalable pipeline for streaming, inference, and monitoring. By leveraging Docker Compose, GPU passthrough, and BPF-based tracing, teams can reproduce and operate the HPE experiment consistently across environments. **The addition of the enhanced ffmpeg_hpe_backup_20260618 framework introduces comprehensive experiment management, advanced performance monitoring, and automated validation capabilities, providing a complete solution for scientific experimentation and quality assurance.** The enhanced orchestration framework, combined with the comprehensive validation system, ensures reliable, reproducible, and high-quality experimental results for streaming and inference research.

## Appendices

### Enhanced Dockerfile Configuration for ffmpeg_hpe_backup_20260618
**NEW**: Comprehensive orchestration framework with experiment management capabilities.

#### Enhanced Docker Compose Configuration
- Multi-service orchestration with precise resource allocation and dependency management.
- GPU-enabled HPE service with configurable device selection and OpenVINO optimization.
- Advanced BPF tracer with automatic port detection and traffic validation.
- Enhanced performance monitoring with Docker API integration.
- Structured results organization with timestamped directories and comprehensive metadata.

#### BPF Tracer Dockerfile
- **NEW**: Ubuntu 22.04 base with comprehensive BCC installation from source.
- **NEW**: Full kernel header support and development dependencies for BPF programming.
- **NEW**: Python 3.9+ with BCC library and dependencies for traffic monitoring.
- **NEW**: Configurable sampling intervals via environment variables.

#### Performance Monitor Dockerfile
- **NEW**: Ubuntu 20.04 base with Docker API integration tools.
- **NEW**: Linux tools, bpftrace, and Python 3.8+ for performance monitoring.
- **NEW**: World-writable output directory for seamless volume mounting.
- **NEW**: Optimized for minimal image size with essential monitoring tools.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [Dockerfile](file://ffmpeg_hpe_backup_20260618/shared/perf_monitor/Dockerfile)

### Enhanced Dockerfile Configuration for Recent-DASH Services
**NEW**: Multi-stage Docker builds for optimized image sizes and reduced attack surface.

#### HTTP Server Dockerfile
- Multi-stage build: Downloads and prepares DASH assets in first stage, copies only necessary files to final image.
- Asset preparation: Automatically clones the recent-dash-proposed-caching repository and extracts video segments.
- Launch script integration: Copies and configures the HTTP-Server.launch.sh script for service startup.
- Environment variables: Configurable service parameters including caching behavior and public folder locations.

#### HTTP Proxy Dockerfile  
- Multi-stage build: Separates asset preparation from runtime execution for security and optimization.
- Cache implementation: Integrates the proxy server with configurable caching algorithms and rate limiting.
- Parameter flexibility: Extensive environment variable support for tuning proxy behavior.
- Launch script automation: Handles domain resolution and parameter processing for reliable startup.

#### HTTP Client Dockerfile
- Multi-stage build: Optimizes for minimal runtime footprint while maintaining functionality.
- Manifest serving: Exposes DASH manifest files while routing segment requests through the proxy.
- Volume mounting: Supports external segment management through bind mounts.
- Launch script orchestration: Manages proxy domain resolution and service initialization.

#### MPV Dockerfile
- **NEW**: Lightweight Debian slim base with minimal dependencies (curl, mpv, ca-certificates).
- **NEW**: Dedicated entrypoint script for intelligent playback management.
- **NEW**: No complex build steps - pure runtime container focused on media playback.

**Section sources**
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)

### Enhanced Experiment Management and Validation
**NEW**: Comprehensive experiment orchestration with automated quality assurance.

#### Experiment Script Features
- **NEW**: Automated container lifecycle management with precise timing measurements.
- **NEW**: Comprehensive diagnostics collection including container logs and system state.
- **NEW**: Structured results organization with timestamped directories and metadata.
- **NEW**: Integrated validation system with automated quality checks and reporting.

#### Validation System Capabilities
- **NEW**: Multi-level validation including exit codes, log parsing, and metric consistency.
- **NEW**: Detailed reporting with PASS/FAIL status and comprehensive metrics.
- **NEW**: Configurable thresholds for performance and validation criteria.
- **NEW**: Automated quality assurance for scientific experimentation.

**Section sources**
- [run_experiment_bcc.sh](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/run_experiment_bcc.sh)
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)

### Container Networking and Port Mappings
- Bridge network: All services join a shared network for internal communication.
- **NEW**: Dedicated dash-caching network with static IP assignments for predictable service discovery.
- **NEW**: Enhanced orchestration framework uses service-level networking for precise dependency management.
- Ports:
  - Streaming server exposes a configurable port mapped to the host.
  - **NEW**: HTTP services use internal port 80 with configurable host port mapping.
  - **NEW**: mpv service runs without external port exposure (headless operation).
  - **NEW**: BPF tracer operates on host network with privileged access for traffic monitoring.
- DNS: Search domain configured for service discovery.
- **NEW**: Network isolation: Enhanced framework maintains service separation while enabling necessary communication.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Enhanced Entrypoint Script Functionality
- **NEW**: Enhanced orchestration framework with automated experiment management.
- **NEW**: Advanced timing and diagnostics collection for performance analysis.
- **NEW**: Integrated validation system with automated quality assurance.
- **NEW**: Conditional GPU metrics launcher: Starts the GPU metrics script in the background when enabled.
- **NEW**: Argument forwarding: Executes the provided command or defaults to the main application.
- **NEW**: Graceful shutdown: Terminates background processes on SIGTERM.
- **NEW**: mpv entrypoint script provides intelligent warmup, retry, and logging capabilities for DASH playback.

**Section sources**
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [run_experiment_bcc.sh](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/run_experiment_bcc.sh)

### Enhanced Scaling and Lifecycle Management
- **NEW**: Enhanced orchestration framework supports independent scaling of experiment components.
- **NEW**: Automated experiment lifecycle with precise timing and validation.
- **NEW**: Comprehensive diagnostics collection for troubleshooting and optimization.
- Scaling:
  - Duplicate the HPE service with different device assignments or separate instances for multiple inputs.
  - Scale the streaming server if bandwidth becomes a bottleneck.
  - **NEW**: Scale recent-dash services independently based on experiment requirements.
  - **NEW**: Enhanced framework supports parallel experiment execution with isolated results.
- Lifecycle:
  - Use restart policies to maintain service uptime.
  - Healthchecks ensure automatic restarts on failure.
  - Graceful shutdown via signals allows cleanup of background processes.
  - **NEW**: Enhanced framework uses "unless-stopped" policy for continuous playback during experiments.
  - **NEW**: Automated validation ensures experiment quality before cleanup.
- **NEW**: Docker API monitoring provides real-time container metrics for dynamic scaling decisions.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Prometheus and Grafana Integration
- Prometheus configuration file is included at the repository root for scraping metrics.
- Grafana dashboards can be configured to visualize GPU and system metrics collected by the pipeline.
- **NEW**: Enhanced framework includes Docker API metrics for comprehensive container monitoring.
- **NEW**: Recent-dash services include Coroot monitoring labels for enhanced observability.

**Section sources**
- [prometheus.yml](file://prometheus.yml)
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Enhanced Environment Variable Configuration Reference (NEW)
**NEW**: Comprehensive environment variable configuration for enhanced orchestration framework and recent-dash services.

#### Enhanced Framework Variables
- `VIDEO_FILE`: Path to video file for streaming (loaded from .env if not set)
- `STREAMER_CPUS`, `STREAMER_RESERVATION_CPUS`: CPU allocation for streaming server
- `HPE_CPUS`: CPU allocation for HPE container
- `BCC_SAMPLE_INTERVAL_MS`: Sampling interval for BPF tracing (default: 10ms)
- `PERF_MONITOR_INTERVAL`: Interval for Docker API performance monitoring (default: 0.5s)

#### Service-Level Variables
- `DASH_SERVER_IP`: Static IP assignment for http_server (default: 172.28.0.2)
- `DASH_PROXY_IP`: Static IP assignment for http_proxy (default: 172.28.0.3)  
- `DASH_CLIENT_IP`: Static IP assignment for http_client (default: 172.28.0.4)
- `DASH_SUBNET`: Network subnet configuration (default: 172.28.0.0/24)
- `HTTP_SERVER_CPU_LIMIT`, `HTTP_SERVER_MEMORY_LIMIT`: Resource limits for http_server
- `HTTP_PROXY_CPU_LIMIT`, `HTTP_PROXY_MEMORY_LIMIT`: Resource limits for http_proxy
- `HTTP_CLIENT_CPU_LIMIT`, `HTTP_CLIENT_MEMORY_LIMIT`: Resource limits for http_client
- `MPV_CPU_LIMIT`, `MPV_MEMORY_LIMIT`: Resource limits for mpv service

#### MPV Player Variables
- `DASH_PLAYER_URL`: DASH manifest URL (default: http://http_client/manifest.mpd)
- `DASH_PLAYER_WARMUP_SECONDS`: Warmup delay before manifest check (default: 30)
- `DASH_PLAYER_RETRY_DELAY_SECONDS`: Retry interval for manifest availability (default: 1)
- `DASH_PLAYER_START_DELAY_SECONDS`: Delay before starting mpv playback (default: 5)

#### Proxy Configuration Variables
- `SERVICE_ADDITIONAL_PARAMETERS`: Proxy algorithm and rate limiting parameters
- `HTTP_SERVER_DOMAIN`, `HTTP_SERVER_PORT`: Upstream server configuration
- `HTTP_PROXY_DOMAIN`, `HTTP_PROXY_PORT`: Downstream proxy configuration

#### Validation System Variables
- `RX_TOLERANCE_PERCENT`: Allowed BCC RX vs FFmpeg bytes-read delta (default: 2.0%)
- `MIN_AVG_CPU_PERCENT`: Minimum plausible average HPE container CPU percent (default: 1.0%)
- `MIN_MEMORY_MB`: Minimum plausible HPE container memory working set (default: 50.0MB)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [validate_run.py](file://ffmpeg_hpe_backup_20260618/ffmpeg_hpe/validate_run.py)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)