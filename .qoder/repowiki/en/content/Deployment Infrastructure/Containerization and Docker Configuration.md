# Containerization and Docker Configuration

<cite>
**Referenced Files in This Document**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)
- [HTTP-Client.launch.sh](file://recent-dash/HTTP-Client.launch.sh)
- [HTTP-Proxy.launch.sh](file://recent-dash/HTTP-Proxy.launch.sh)
- [HTTP-Server.launch.sh](file://recent-dash/HTTP-Server.launch.sh)
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
- Added comprehensive documentation for the new mpv service in recent-dash for containerized media playback
- Updated recent-dash architecture to include automated DASH segment fetching and playback capabilities
- Enhanced Dockerfile configurations for HTTP server, proxy, and client services
- Added detailed coverage of the mpv-entrypoint.sh script functionality and environment variable configuration
- Updated container networking and service dependencies to support the new media playback workflow

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
- **NEW**: Containerized media playback capabilities using mpv for recent-dash DASH streaming experiments.
- Best practices for container resource allocation, GPU passthrough, and production deployment considerations.
- Examples of scaling services and managing container lifecycles.

## Project Structure
The repository organizes containerization artifacts primarily under:
- ffmpeg_hpe: streaming pipeline, GPU metrics, and BPF tracer services
- recent-dash: HTTP server, proxy, client, and **NEW**: mpv media player for DASH streaming experiments
- rtsp-ipcam: H.264 streaming server
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
G["entrypoint.sh (bcc)"]
end
subgraph "recent-dash"
H["docker-compose.yml"]
I["HTTP-Server.Dockerfile"]
J["HTTP-Proxy.Dockerfile"]
K["HTTP-Client.Dockerfile"]
L["mpv-entrypoint.sh"]
M["Dockerfile_mpv"]
N["mpv service"]
end
subgraph "rtsp-ipcam"
O["docker-compose.yml"]
P["Dockerfile"]
Q["start_server.sh"]
end
subgraph "monitor_hpe"
R["Dockerfile"]
S["docker-compose.yaml"]
end
T["Dockerfile.hpe"]
U["prometheus.yml"]
V["docker-compose.yml (root)"]
A --> C
A --> D
A --> E
E --> F
E --> G
H --> I
H --> J
H --> K
H --> L
H --> M
H --> N
O --> P
O --> Q
S --> R
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [Dockerfile.gpu_metrics](file://ffmpeg_hpe/Dockerfile.gpu_metrics)
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
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
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)

## Core Components
- H.264 streaming server: Provides an HTTP H.264 stream for downstream consumers.
- HPE application: Performs pose estimation on the stream; supports GPU acceleration and configurable device selection.
- GPU metrics collector: Gathers GPU utilization and telemetry periodically.
- Performance monitor: Monitors host-level processes and system resources.
- BPF tracer: Captures and logs network traffic related to the HPE pipeline using BCC/BPF.
- **NEW**: Recent-DASH services: HTTP server, proxy, client, and **mpv media player** for automated DASH segment fetching and playback experiments.
- **NEW**: Containerized media playback: Automated DASH streaming playback using mpv with configurable warmup, retry, and logging capabilities.

Key orchestration highlights:
- Services share a dedicated bridge network for isolated communication.
- Health checks ensure readiness before dependent services start.
- Resource limits and reservations are configured for predictable performance.
- GPU passthrough is enabled via NVIDIA runtime and environment variables.
- **NEW**: mpv service automatically waits for DASH manifest availability and handles continuous playback with restart capabilities.

**Section sources**
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
- **NEW**: recent-dash services form a complete DASH streaming pipeline with automated media playback.

```mermaid
graph TB
subgraph "Network: streaming-network"
S["h264-streaming-server"]
H["hpe"]
G["gpu-metrics"]
P["perf_monitor"]
T["bcc-tracer"]
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
DS --> |"DASH Segments"| DP
DP --> |"Cached/Forwarded"| DC
DC --> |"Manifest"| DM
DM --> |"Automated Playback"| DS
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Detailed Component Analysis

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

### Performance Monitor
- Purpose: Observe host-level processes and system resources for the experiment.
- Privileges: Requires elevated capabilities and host PID namespace for accurate monitoring.
- Volumes: Mounts output and PID directories for artifact persistence and process tracking.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yaml](file://monitor_hpe/docker-compose.yaml)
- [Dockerfile](file://monitor_hpe/Dockerfile)

### BPF Tracer (BCC-based)
- Purpose: Capture TCP RX bytes for the H.264 stream between the streaming server and HPE.
- Image: Ubuntu-based with BCC built from source and Python dependencies.
- Execution: Detects the HPE listening port and attaches a raw socket filter to capture traffic on the default interface.
- Output: Writes per-timestamp RX deltas and cumulative byte counts to CSV.

Security and capabilities:
- Requires privileged mode and specific capabilities for kernel tracing.
- Shares the HPE service network namespace to simplify IP/port discovery.

**Section sources**
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)

### Recent-DASH Infrastructure (Alternative Orchestration)
- Purpose: Complete DASH streaming pipeline with HTTP server, proxy, client, and **automated media playback**.
- Services: http_server, http_proxy, http_client, **mpv**, perf_monitor, and a containerized BPF tracer.
- Networking: Dedicated bridge network with static IP assignments for predictable service discovery.
- **NEW**: mpv service with automated DASH segment fetching and continuous playback capabilities.
- **NEW**: Environment variable-driven configuration for warmup delays, retry intervals, and playback timing.
- Entrypoints: Launch scripts manage process lifecycle and PID tracking.

**Updated** Added comprehensive media playback capabilities with automated DASH segment handling.

**Section sources**
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [Dockerfile_mpv](file://recent-dash/Dockerfile_mpv)

### MPV Media Player Service (NEW)
- Purpose: **Automated DASH streaming playback** with continuous loop and intelligent error recovery.
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
- **NEW**: recent-dash services follow a strict startup order: http_server → http_proxy → http_client → mpv.
- **NEW**: mpv service depends on http_client being ready and serving the DASH manifest.

```mermaid
graph LR
H264["h264-streaming-server"] --> HPE["hpe"]
HPE --> GPU["gpu-metrics"]
HPE --> PERF["perf_monitor"]
HPE --> BPF["bcc-tracer"]
HTTP_SERVER["http_server"] --> HTTP_PROXY["http_proxy"]
HTTP_PROXY --> HTTP_CLIENT["http_client"]
HTTP_CLIENT --> MPV["mpv"]
```

**Diagram sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Performance Considerations
- Resource Allocation:
  - CPU and memory limits and reservations are defined per service to prevent noisy-neighbor effects.
  - HPE uses significant shared memory to support model inference.
  - **NEW**: mpv service has minimal resource footprint with 0.25 CPUs and 256MB memory limits.
- GPU Passthrough:
  - NVIDIA runtime and environment variables ensure the HPE container sees the correct GPU(s).
  - Device reservations are configured for guaranteed GPU access.
- Observability:
  - Healthchecks provide early failure detection.
  - GPU metrics and BPF tracing offer deep insights into throughput and bottlenecks.
  - **NEW**: mpv service provides detailed playback logs for debugging and performance analysis.
- FFMPEG Tuning:
  - Increased timeouts reduce premature failures on long streams.
- Security Hardening:
  - Non-root users, read-only root filesystems, and temporary filesystems for /tmp improve isolation.
- **NEW**: DASH Pipeline Optimization:
  - Static IP assignments eliminate DNS resolution overhead in the pipeline.
  - Resource-constrained services prevent resource contention during experiments.
  - Automated warmup mechanisms ensure stable playback conditions.

**Section sources**
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
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [run_nvidia_dcgm.sh](file://ffmpeg_hpe/run_nvidia_dcgm.sh)
- [entrypoint.sh](file://ffmpeg_hpe/bpftrace-tracer/entrypoint.sh)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

## Conclusion
The containerization setup provides a robust, observable, and scalable pipeline for streaming, inference, and monitoring. By leveraging Docker Compose, GPU passthrough, and BPF-based tracing, teams can reproduce and operate the HPE experiment consistently across environments. **The addition of the mpv service and enhanced recent-dash infrastructure now enables automated DASH segment fetching and playback capabilities, providing a complete experimental framework for caching and streaming research.** Applying the best practices outlined here ensures predictable performance, improved security, and easier maintenance.

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

### Container Networking and Port Mappings
- Bridge network: All services join a shared network for internal communication.
- **NEW**: Dedicated dash-caching network with static IP assignments for predictable service discovery.
- Ports:
  - Streaming server exposes a configurable port mapped to the host.
  - **NEW**: HTTP services use internal port 80 with configurable host port mapping.
  - **NEW**: mpv service runs without external port exposure (headless operation).
- DNS: Search domain configured for service discovery.
- **NEW**: Network isolation: mpv service operates in the same network as other recent-dash services.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Entrypoint Script Functionality
- Conditional GPU metrics launcher: Starts the GPU metrics script in the background when enabled.
- Argument forwarding: Executes the provided command or defaults to the main application.
- Graceful shutdown: Terminates background processes on SIGTERM.
- **NEW**: mpv entrypoint script provides intelligent warmup, retry, and logging capabilities for DASH playback.

**Section sources**
- [entrypoint.sh](file://ffmpeg_hpe/entrypoint.sh)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)

### Scaling and Lifecycle Management
- Scaling:
  - Duplicate the HPE service with different device assignments or separate instances for multiple inputs.
  - Scale the streaming server if bandwidth becomes a bottleneck.
  - **NEW**: Scale recent-dash services independently based on experiment requirements.
- Lifecycle:
  - Use restart policies to maintain service uptime.
  - Healthchecks ensure automatic restarts on failure.
  - Graceful shutdown via signals allows cleanup of background processes.
  - **NEW**: mpv service uses "unless-stopped" policy for continuous playback during experiments.

**Section sources**
- [docker-compose.yaml](file://ffmpeg_hpe/docker-compose.yaml)
- [docker-compose.yml](file://rtsp-ipcam/docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Prometheus and Grafana Integration
- Prometheus configuration file is included at the repository root for scraping metrics.
- Grafana dashboards can be configured to visualize GPU and system metrics collected by the pipeline.
- **NEW**: Recent-dash services include Coroot monitoring labels for enhanced observability.

**Section sources**
- [prometheus.yml](file://prometheus.yml)
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)

### Environment Variable Configuration Reference (NEW)
**NEW**: Comprehensive environment variable configuration for recent-dash services and mpv player.

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

**Section sources**
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [mpv-entrypoint.sh](file://recent-dash/mpv-entrypoint.sh)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)