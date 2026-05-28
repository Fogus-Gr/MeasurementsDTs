# Containerization and Docker Configuration

<cite>
**Referenced Files in This Document**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [bcc_tx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_tx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [Dockerfile](file://monitor_hpe/Dockerfile)
- [Dockerfile.hpe](file://Dockerfile.hpe)
- [prometheus.yml](file://prometheus.yml)
- [docker-compose.yml](file://docker-compose.yml)
- [README.md](file://README.md)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [USAGE.md](file://monitor_hpe/USAGE.md)
- [DYNAMIC_RESOURCE_ALLOCATION_SUMMARY.md](file://DYNAMIC_RESOURCE_ALLOCATION_SUMMARY.md)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)
- [bcc-bpf-tracing.md](file://docs/bcc-bpf-tracing.md)
</cite>

## Update Summary
**Changes Made**
- Enhanced GPU metrics collection with improved Docker configurations and comprehensive environment variable management for resource allocation
- Added comprehensive environment variable management for resource allocation (HPE_CPU_LIMIT, HPE_CPU_RESERVATION, HPE_MEMORY_LIMIT, HPE_MEMORY_RESERVATION)
- Integrated BCC-based TX byte counter with 10ms granularity measurements alongside RX byte counter
- Updated resource allocation strategy with dynamic CPU and memory limits based on system vCPUs and HPE method
- Enhanced monitoring capabilities with dual-direction traffic measurement (TX/RX) for complete network bandwidth analysis

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
- Docker Compose architecture for orchestrating multiple services including an RTSP broker, FFmpeg streamer, Human Pose Estimation (HPE) application, GPU metrics collector, performance monitor, and a BPF-based traffic tracer.
- Container networking, port mappings, and service dependencies.
- Dockerfile configuration for the HPE application, including base images, environment variables, and runtime dependencies.
- Entrypoint script functionality and container startup procedures.
- Best practices for container resource allocation, GPU passthrough, and production deployment considerations.
- Examples of scaling services and managing container lifecycles.

**Updated** The architecture now includes enhanced GPU metrics collection with comprehensive environment variable management for resource allocation and integrated BCC-based TX byte counter with 10ms granularity measurements for complete network bandwidth analysis.

## Project Structure
The repository organizes containerization artifacts primarily under:
- ffmpeg_hpe: RTSP streaming pipeline, GPU metrics, and BPF tracer services
- docker-compose.rtsp.yml: Alternative RTSP streaming configuration
- recent-dash: HTTP server, proxy, and related containers for caching experiments
- monitor_hpe: monitoring utilities and PID tracking
- Root-level Dockerfiles and compose files for top-level services

```mermaid
graph TB
subgraph "ffmpeg_hpe"
A["docker-compose.yaml"]
B["Dockerfile.gpu_metrics"]
C["entrypoint.sh"]
D["run_nvidia_dcgm.sh"]
E["Dockerfile.bcc"]
F["bcc_rx_bytes.py"]
G["bcc_tx_bytes.py"]
H["entrypoint.sh (bcc)"]
I["rtsp-broker:8554"]
J["streamer (jrottenberg/ffmpeg:4.4-nvidia)"]
K["HPE_CPU_LIMIT/HPE_CPU_RESERVATION"]
L["HPE_MEMORY_LIMIT/HPE_MEMORY_RESERVATION"]
end
subgraph "docker-compose.rtsp.yml"
M["docker-compose.rtsp.yml"]
N["mediamtx:latest"]
O["ffmpeg-streamer:4.4-ubuntu"]
end
subgraph "recent-dash"
P["docker-compose.yml"]
Q["HTTP-Server.Dockerfile"]
R["HTTP-Proxy.Dockerfile"]
S["entrypoint.sh"]
end
subgraph "monitor_hpe"
T["Dockerfile"]
U["docker-compose.yaml"]
V["Resource Allocation"]
end
W["Dockerfile.hpe"]
X["prometheus.yml"]
Y["docker-compose.yml (root)"]
A --> C
A --> D
A --> E
E --> F
E --> G
E --> H
A --> I
A --> J
A --> K
A --> L
M --> N
M --> O
P --> Q
P --> R
P --> S
U --> T
V --> U
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [bcc_tx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_tx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [Dockerfile](file://monitor_hpe/Dockerfile)
- [Dockerfile.hpe](file://Dockerfile.hpe)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)

## Core Components
- RTSP Broker (MediaMTX): Provides RTSP streaming infrastructure with HLS support for debugging.
- FFmpeg Streamer: Encodes and streams video using NVENC H.264 encoding with low-latency settings.
- HPE Application: Performs pose estimation on the RTSP stream; supports GPU acceleration and configurable device selection.
- GPU metrics collector: Gathers GPU utilization and telemetry periodically.
- Performance monitor: Monitors host-level processes and system resources.
- BPF tracer: Captures and logs network traffic related to the HPE pipeline using BCC/BPF with dual-direction TX/RX measurements.
- Recent-DASH services: HTTP server and proxy for caching experiments.

Key orchestration highlights:
- Services share a dedicated bridge network for isolated communication.
- Health checks ensure readiness before dependent services start.
- Comprehensive resource allocation with dynamic CPU and memory limits based on system capacity.
- GPU passthrough is enabled via NVIDIA runtime and environment variables.
- Dual-direction network monitoring with 10ms granularity for precise bandwidth analysis.

**Updated** The streaming architecture now includes enhanced resource allocation with environment variables (HPE_CPU_LIMIT, HPE_CPU_RESERVATION, HPE_MEMORY_LIMIT, HPE_MEMORY_RESERVATION) and integrated BCC-based TX/RX byte counters for complete network traffic analysis.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [USAGE.md](file://monitor_hpe/USAGE.md)

## Architecture Overview
The orchestration centers on a shared network and a strict startup order with enhanced resource management:
- rtsp-broker starts first and exposes RTSP (8554) and HLS (8888) ports.
- streamer depends on the broker and encodes video using NVENC with low-latency settings.
- hpe depends on both the broker and streamer being healthy and consumes the RTSP stream.
- gpu-metrics runs alongside hpe to collect GPU telemetry with configured resource limits.
- perf_monitor operates independently with controlled resource allocation.
- bcc-tracer operates with dual-direction monitoring (TX/RX) using 10ms granularity.

```mermaid
graph TB
subgraph "Network: streaming-network"
BROKER["rtsp-broker:8554"]
STREAMER["streamer (NVENC H.264)"]
H["hpe<br/>CPU: ${HPE_CPU_LIMIT}<br/>Memory: ${HPE_MEMORY_LIMIT}"]
G["gpu-metrics<br/>CPU: 0.1<br/>Memory: 128M"]
P["perf_monitor<br/>CPU: 0.25<br/>Memory: 256M"]
T["bcc-tracer<br/>TX/RX 10ms<br/>CPU: 0.5<br/>Memory: 512M"]
end
BROKER --> |"RTSP Stream"| STREAMER
STREAMER --> |"Encoded Stream"| H
H --> |"GPU Telemetry"| G
H --> |"System Metrics"| P
H --> |"Dual-direction Traffic"| T
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

## Detailed Component Analysis

### RTSP Broker (MediaMTX)
- Purpose: Provide RTSP streaming infrastructure with HLS support for debugging.
- Networking: Exposes RTSP (8554) and HLS (8888) ports on the host.
- Configuration: Uses MediaMTX with debug logging and on-demand streaming.
- Resource limits: CPU and memory limits with reservations for controlled resource usage.
- Healthcheck: No healthcheck due to distroless container limitations.

Operational notes:
- Port 8554 is used for RTSP streaming to the HPE application.
- Port 8888 provides HLS access for debugging and monitoring.
- Readiness is enforced externally by the experiment runner.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

### FFmpeg Streamer (NVENC Encoding)
- Purpose: Encode and stream video using NVIDIA NVENC H.264 encoding with low-latency settings.
- Image: jrottenberg/ffmpeg:4.4-nvidia with NVIDIA runtime capabilities.
- GPU Passthrough: Uses NVIDIA runtime with compute, utility, and video capabilities.
- Encoding Settings: NVENC low-latency with preset p2 and tune ll for balanced latency.
- Transport: Forces RTP over TCP for consistent packet capture by BPF tracer.
- Volume: Mounts video directory for input files.
- Dependencies: Depends on rtsp-broker being started.

Encoding configuration highlights:
- Low-latency NVENC settings (-preset p2 -tune ll)
- TCP transport for reliable packet capture
- Infinite loop (-stream_loop -1) for repeatable experiments
- GPU reservation for guaranteed hardware access

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

### HPE Application (Human Pose Estimation)
- Purpose: Consume the RTSP stream and perform pose estimation with optional OpenVINO and PyTorch backends.
- GPU Passthrough: Uses NVIDIA runtime and visible device configuration.
- Environment Variables: Controls input stream URL, device selection, timeouts, and buffer sizes.
- Shared Memory: Configured for large model requirements.
- Startup Command: Executes the main application with method, input, CSV output, and measurement interval parameters.
- Entrypoint Behavior: Conditionally starts GPU metrics in the background and executes the main command.
- **Updated**: Now supports dynamic resource allocation via HPE_CPU_LIMIT, HPE_CPU_RESERVATION, HPE_MEMORY_LIMIT, and HPE_MEMORY_RESERVATION environment variables.

Runtime configuration highlights:
- Device selection and CUDA visibility are explicitly set.
- FFMPEG timeouts are increased to accommodate long streams.
- Healthcheck monitors the main process.
- RTSP transport forced to TCP via OPENCV_FFMPEG_CAPTURE_OPTIONS.
- **Updated**: Resource allocation is dynamically calculated based on system vCPUs and HPE method.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [Dockerfile.hpe](file://Dockerfile.hpe)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [USAGE.md](file://monitor_hpe/USAGE.md)

### GPU Metrics Collector
- Purpose: Periodically collect GPU telemetry (utilization, memory, temperature, power) and write to CSV.
- Image: NVIDIA CUDA base image with NVIDIA utilities.
- Execution: Runs a monitoring script that queries GPU statistics at a configurable interval.
- Output: Writes CSV data to a mounted output directory.
- **Updated**: Now operates with controlled resource limits (0.1 CPU, 128M memory) to prevent interference with HPE measurements.

Operational notes:
- Supports duration-limited runs and graceful shutdown via signal handling.
- Designed to run in parallel with the HPE workload.
- **Updated**: Resource constraints ensure minimal impact on HPE performance.

**Section sources**
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

### Performance Monitor
- Purpose: Observe host-level processes and system resources for the experiment.
- Privileges: Requires elevated capabilities and host PID namespace for accurate monitoring.
- Volumes: Mounts output and PID directories for artifact persistence and process tracking.
- **Updated**: Operates with controlled resource allocation (0.25 CPU, 256M memory) to isolate from HPE workloads.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [Dockerfile](file://monitor_hpe/Dockerfile)

### BPF Tracer (BCC-based) - Enhanced with TX/RX Monitoring
- Purpose: Capture TCP RX and TX bytes for the RTSP stream between the streamer and HPE with 10ms granularity.
- Image: Ubuntu-based with BCC built from source and Python dependencies.
- Execution: Detects the HPE listening port and attaches both raw socket filters (RX) and tracepoints (TX) to capture traffic on the default interface.
- Output: Writes per-timestamp RX/TX deltas and cumulative byte counts to CSV.
- **Updated**: Now provides dual-direction monitoring with TX byte counter complementing RX byte counter.

Security and capabilities:
- Requires privileged mode and specific capabilities for kernel tracing.
- Shares the HPE service network namespace to simplify IP/port discovery.
- **Updated**: 10ms polling interval provides precise bandwidth measurements for real-time analysis.

**Section sources**
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [bcc_tx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_tx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

### Alternative RTSP Configuration
- Purpose: Alternative RTSP streaming setup using host networking for simplified deployment.
- Services: mediamtx (broker) and ffmpeg-streamer (encoder) with host networking.
- Configuration: Uses host networking for direct access to RTSP port 8554.
- Encoding: Direct video copying with TCP transport for reliable streaming.

**Section sources**
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)

### Recent-DASH Infrastructure (Alternative Orchestration)
- Purpose: HTTP server and proxy for caching experiments with configurable parameters.
- Services: http_server, http_proxy, http_client, perf_monitor, and a containerized BPF tracer.
- Networking: Host networking for the tracer; host PID sharing for process monitoring.
- Entrypoints: Launch scripts manage process lifecycle and PID tracking.

**Section sources**
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)

## Dependency Analysis
Inter-service dependencies and startup order with enhanced resource management:
- rtsp-broker starts first and exposes RTSP/HLS services.
- streamer depends on rtsp-broker being started and encodes video files.
- hpe depends on both rtsp-broker and streamer being healthy, with dynamic resource allocation applied.
- gpu-metrics and perf-monitor can start independently but benefit from the pipeline being active.
- bcc-tracer depends on the HPE container's network namespace and detects HPE's outbound connection to the broker.

```mermaid
graph LR
BROKER["rtsp-broker:8554"] --> STREAMER["streamer (NVENC)"]
STREAMER --> HPE["hpe<br/>Dynamic Resources"]
HPE --> GPU["gpu-metrics<br/>Controlled Limits"]
HPE --> PERF["perf_monitor<br/>Controlled Limits"]
HPE --> BPF["bcc-tracer<br/>TX/RX 10ms"]
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

## Performance Considerations
- Resource Allocation:
  - **Updated**: Comprehensive resource allocation system with HPE_CPU_LIMIT, HPE_CPU_RESERVATION, HPE_MEMORY_LIMIT, and HPE_MEMORY_RESERVATION environment variables.
  - CPU and memory limits and reservations are dynamically calculated based on system vCPUs and HPE method to prevent noisy-neighbor effects.
  - HPE uses significant shared memory to support model inference with controlled resource allocation.
- GPU Passthrough:
  - NVIDIA runtime and environment variables ensure the HPE container sees the correct GPU(s).
  - Device reservations are configured for guaranteed GPU access.
  - NVENC encoding provides hardware-accelerated H.264 encoding with low-latency settings.
- Observability:
  - Healthchecks provide early failure detection.
  - GPU metrics and BPF tracing offer deep insights into throughput and bottlenecks.
  - **Updated**: Dual-direction network monitoring with 10ms granularity for precise bandwidth analysis.
- FFMPEG Tuning:
  - Increased timeouts reduce premature failures on long streams.
  - NVENC low-latency settings (-preset p2 -tune ll) optimize for real-time streaming.
- Security Hardening:
  - Non-root users, read-only root filesystems, and temporary filesystems for /tmp improve isolation.
  - **Updated**: Controlled resource limits prevent resource contention between services.

**Updated** Enhanced resource allocation system with dynamic CPU and memory limits based on system capacity, plus dual-direction network monitoring for complete traffic analysis.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [USAGE.md](file://monitor_hpe/USAGE.md)

## Troubleshooting Guide
Common issues and remedies:
- HPE fails to start or exits quickly:
  - Verify the rtsp-broker is healthy and accessible on port 8554.
  - Confirm environment variables for input RTSP URL and device selection are correct.
  - Check GPU visibility and NVIDIA runtime configuration.
  - Verify RTSP stream is being produced by the streamer service.
  - **Updated**: Verify HPE resource allocation variables (HPE_CPU_LIMIT, HPE_CPU_RESERVATION, HPE_MEMORY_LIMIT, HPE_MEMORY_RESERVATION) are properly set.
- RTSP stream not available:
  - Check that rtsp-broker container is running and exposing ports 8554/8888.
  - Verify streamer service is encoding and publishing to rtsp://rtsp-broker:8554/stream.
  - Ensure video file exists in the mounted /data volume.
- GPU metrics container does not produce output:
  - Ensure NVIDIA drivers and utilities are present in the container.
  - Validate output directory permissions and mount points.
- BPF tracer cannot detect HPE port:
  - Confirm the tracer shares the HPE network namespace.
  - Verify the default interface is correctly detected and accessible.
  - Check that HPE establishes an outbound connection to the broker before the tracer starts.
  - **Updated**: Verify both TX and RX tracers are running with 10ms polling interval.
- Port conflicts or accessibility:
  - Review port mappings and ensure host ports 8554/8888 are free.
  - Validate firewall and network policies in the environment.
- NVENC encoding issues:
  - Verify NVIDIA GPU is available and properly configured.
  - Check that jrottenberg/ffmpeg:4.4-nvidia image supports NVENC capabilities.
  - Ensure proper GPU reservations are configured.
- **Updated**: Resource allocation issues:
  - Check that HPE_CPU_LIMIT and HPE_MEMORY_LIMIT are set appropriately for the system capacity.
  - Verify HPE_CPU_RESERVATION provides guaranteed CPU access for stable performance.
  - Monitor docker stats to confirm resource limits are being enforced.

**Updated** Troubleshooting guidance now includes resource allocation validation and dual-direction network monitoring verification.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)

## Conclusion
The containerization setup provides a robust, observable, and scalable pipeline for RTSP streaming, inference, and monitoring. By leveraging Docker Compose, RTSP streaming with MediaMTX, NVENC encoding, GPU passthrough, and BPF-based tracing with dual-direction monitoring, teams can reproduce and operate the HPE experiment consistently across environments. The new RTSP architecture with hardware-accelerated encoding provides improved performance and reliability compared to the legacy HTTP streaming approach. The enhanced resource allocation system with dynamic CPU and memory limits, combined with comprehensive network monitoring capabilities, ensures predictable performance, improved security, and easier maintenance. The addition of TX/RX byte counters with 10ms granularity provides unprecedented insight into network bandwidth utilization for optimization and troubleshooting.

## Appendices

### Dockerfile Configuration for HPE Application
Highlights:
- Base image tailored for CUDA and PyTorch development.
- Manual compilation of FFmpeg with NVIDIA CUDA/NVENC/NPP support.
- Manual compilation of OpenCV 4.10.0 with CUDA and FFMPEG support.
- Installation of Python dependencies and optional OpenVINO with GPU support.
- Model downloads and extension builds during image build.
- Entrypoint and default CMD for flexible invocation.

**Section sources**
- [Dockerfile.hpe](file://Dockerfile.hpe)

### Container Networking and Port Mappings
- Bridge network: All services join a shared network for internal communication.
- Ports:
  - RTSP broker exposes RTSP (8554) and HLS (8888) ports.
  - Alternative RTSP configuration uses host networking on port 8554.
  - Recent-DASH services expose port 80 internally; client can publish externally if needed.
- DNS: Search domain configured for service discovery.

**Updated** Networking configuration now uses RTSP broker (8554) and HLS (8888) ports instead of the legacy HTTP streaming server, with enhanced resource allocation controls.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Entrypoint Script Functionality
- Conditional GPU metrics launcher: Starts the GPU metrics script in the background when enabled.
- Argument forwarding: Executes the provided command or defaults to the main application.
- Graceful shutdown: Terminates background processes on SIGTERM.

**Section sources**
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)

### Scaling and Lifecycle Management
- Scaling:
  - Duplicate the HPE service with different device assignments or separate instances for multiple inputs.
  - Scale the RTSP broker and streamer if bandwidth becomes a bottleneck.
  - **Updated**: Adjust resource allocation variables (HPE_CPU_LIMIT, HPE_MEMORY_LIMIT) based on scaling requirements.
- Lifecycle:
  - Use restart policies to maintain service uptime.
  - Healthchecks ensure automatic restarts on failure.
  - Graceful shutdown via signals allows cleanup of background processes.
  - **Updated**: Resource limits prevent runaway resource consumption during scaling.

**Updated** Scaling considerations now include dynamic resource allocation variables for optimal performance scaling.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)

### Prometheus and Grafana Integration
- Prometheus configuration file is included at the repository root for scraping metrics.
- Grafana dashboards can be configured to visualize GPU and system metrics collected by the pipeline.

**Section sources**
- [prometheus.yml](file://prometheus.yml)
- [docker-compose.yml](file://docker-compose.yml)

### RTSP Streaming Architecture Migration
The repository has migrated from HTTP H.264 streaming to RTSP streaming for improved reliability and performance:

**Legacy Architecture:**
- h264-streaming-server: HTTP-based H.264 streaming over port 8089
- Direct HTTP stream consumption by HPE application

**Current Architecture:**
- rtsp-broker: RTSP streaming broker (bluenviron/mediamtx:1-ffmpeg)
- streamer: Hardware-accelerated NVENC encoding (jrottenberg/ffmpeg:4.4-nvidia)
- HPE application: RTSP stream consumption with TCP transport

**Migration Benefits:**
- Improved streaming reliability with RTSP protocol
- Hardware-accelerated encoding reduces CPU usage
- Better packet capture and monitoring capabilities
- Enhanced scalability and performance

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.rtsp.yml](file://docker-compose.rtsp.yml)
- [README.md](file://README.md)

### Enhanced Resource Allocation System
**Updated** The system now includes comprehensive environment variable management for resource allocation:

#### Dynamic Resource Calculation
- **HPE_CPU_LIMIT**: Maximum CPU cores allocated to HPE based on system vCPUs and method requirements
- **HPE_CPU_RESERVATION**: Guaranteed CPU cores for stable performance
- **HPE_MEMORY_LIMIT**: Maximum memory allocated to HPE based on model requirements
- **HPE_MEMORY_RESERVATION**: Guaranteed memory for critical operations

#### Implementation Details
- CPU limits calculated as HPE_VCPUS with method-specific adjustments
- Memory limits calculated as 1.5GB per vCPU for heavy models (HRNet) with minimum 6GB
- Reservation ratios optimized for stability (CPU: 67%, Memory: 75% for heavy models)
- Environment variables exported before docker compose execution

**Section sources**
- [run_experiment.sh](file://ffmpeg_hpe/run_experiment.sh)
- [USAGE.md](file://monitor_hpe/USAGE.md)
- [DYNAMIC_RESOURCE_ALLOCATION_SUMMARY.md](file://DYNAMIC_RESOURCE_ALLOCATION_SUMMARY.md)

### Dual-Direction Network Monitoring
**Updated** The BPF tracer now provides comprehensive network monitoring with 10ms granularity:

#### TX Byte Counter (bcc_tx_bytes.py)
- **Purpose**: Measures transmitted bytes from HPE process using sys_enter_sendto tracepoint
- **Implementation**: Attaches to sendto syscall events filtered by HPE PID
- **Output**: Timestamped TX deltas, cumulative bytes, and timing information
- **Polling Interval**: 10ms (0.01 seconds) for precise bandwidth measurement

#### RX Byte Counter (bcc_rx_bytes.py)
- **Purpose**: Measures received bytes for RTSP stream using raw socket filter
- **Implementation**: Parses Ethernet/TCP headers and accumulates packet lengths
- **Output**: Timestamped RX deltas, cumulative bytes, and timing information
- **Polling Interval**: 10ms (0.01 seconds) for synchronized TX/RX comparison

#### Integration Benefits
- **Complete Bandwidth Analysis**: Compare TX vs RX for network utilization insights
- **Real-time Monitoring**: 10ms intervals provide granular performance data
- **Kernel-level Accuracy**: BPF programs ensure precise packet counting without user-space overhead
- **Complementary Data**: TX/RX counters enable identification of network bottlenecks

**Section sources**
- [bcc_tx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_tx_bytes.py)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [bcc-bpf-tracing.md](file://docs/bcc-bpf-tracing.md)
- [plot_rx_bytes.py](file://ffmpeg_hpe/plot_rx_bytes.py)