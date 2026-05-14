# Network Monitoring System

<cite>
**Referenced Files in This Document**
- [README.md](file://recent-dash/README.md)
- [docker-compose.yml](file://recent-dash/docker-compose.yml)
- [docker-compose.infra.yml](file://recent-dash/docker-compose.infra.yml)
- [prometheus.yml](file://recent-dash/prometheus.yml)
- [run_experiment.sh](file://recent-dash/run_experiment.sh)
- [entrypoint.sh](file://recent-dash/entrypoint.sh)
- [HTTP-Server.Dockerfile](file://recent-dash/HTTP-Server.Dockerfile)
- [HTTP-Server.launch.sh](file://recent-dash/HTTP-Server.launch.sh)
- [HTTP-Proxy.Dockerfile](file://recent-dash/HTTP-Proxy.Dockerfile)
- [HTTP-Proxy.launch.sh](file://recent-dash/HTTP-Proxy.launch.sh)
- [HTTP-Client.Dockerfile](file://recent-dash/HTTP-Client.Dockerfile)
- [HTTP-Client.launch.sh](file://recent-dash/HTTP-Client.launch.sh)
- [trace_container_net.sh](file://recent-dash/bpftrace-tracer/trace_container_net.sh)
- [monitor_pid_perf.sh](file://recent-dash/perf_monitor/monitor_pid_perf.sh)
- [bcc-bpf-tracing.md](file://docs/bcc-bpf-tracing.md)
- [bcc_rx_bytes.py](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py)
- [Dockerfile.bcc](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc)
- [run_experiment_bcc.sh](file://ffmpeg_hpe/run_experiment_bcc.sh)
- [Report on RX TX traffic discrepancy.md](file://Report on RX TX traffic discrepancy.md)
</cite>

## Update Summary
**Changes Made**
- Updated network monitoring architecture section to clarify why bpftrace handles TX traffic while bcc-tracer handles RX traffic
- Added detailed explanation of kernel context differences between TX and RX traffic capture
- Updated CSV file source specifications to reflect accurate data collection methods
- Enhanced troubleshooting guidance with specific examples of traffic discrepancy analysis

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Network Monitoring Architecture](#network-monitoring-architecture)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)
11. [Appendices](#appendices)

## Introduction
This document describes the recent-dash network monitoring system designed to track HTTP traffic and performance metrics across a DASH streaming pipeline. It explains BPF tracing capabilities for live network packet analysis, performance monitoring tools for CPU and memory metrics, and the HTTP proxy/client/server configuration. The system now features a dual-tracing architecture where bpftrace captures TX (transmit) traffic while a separate bcc-based tracer captures RX (receive) traffic, providing comprehensive visibility into network performance characteristics.

## Project Structure
The recent-dash project organizes monitoring and streaming components into modular Docker services and supporting scripts:
- Streaming stack: HTTP server (CDN-like), HTTP proxy (with caching), and HTTP client (DASH player endpoint).
- Observability stack: Prometheus, Coroot, and ClickHouse for metrics and storage.
- Dual monitoring systems: bpftrace-based TX traffic tracer and bcc-based RX traffic tracer.
- Performance monitoring: pidstat-based performance monitor.

```mermaid
graph TB
subgraph "Streaming Services"
HS["HTTP Server<br/>HTTP-Server.Dockerfile"]
HP["HTTP Proxy<br/>HTTP-Proxy.Dockerfile"]
HC["HTTP Client<br/>HTTP-Client.Dockerfile"]
end
subgraph "Observability"
PROM["Prometheus<br/>prometheus.yml"]
COROOT["Coroot<br/>docker-compose.infra.yml"]
CH["ClickHouse<br/>docker-compose.infra.yml"]
end
subgraph "Monitoring Systems"
PERF["Perf Monitor<br/>monitor_pid_perf.sh"]
BPFTRACE["bpftrace TX Tracer<br/>trace_container_net.sh"]
BCC_TRACER["bcc RX Tracer<br/>bcc_rx_bytes.py"]
ENDPOINTS["Endpoint Tracers<br/>Dockerfile.bcc"]
end
HS --> HP
HP --> HC
PERF --> HS
PERF --> HP
PERF --> HC
BPFTRACE --> HS
BPFTRACE --> HP
BPFTRACE --> HC
BCC_TRACER --> HS
BCC_TRACER --> HP
BCC_TRACER --> HC
PROM --> COROOT
COROOT --> CH
```

**Diagram sources**
- [docker-compose.yml:1-103](file://recent-dash/docker-compose.yml#L1-L103)
- [docker-compose.infra.yml:1-101](file://recent-dash/docker-compose.infra.yml#L1-L101)
- [prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)
- [monitor_pid_perf.sh:1-72](file://recent-dash/perf_monitor/monitor_pid_perf.sh#L1-L72)
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)
- [bcc_rx_bytes.py:1-120](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py#L1-L120)

**Section sources**
- [docker-compose.yml:1-103](file://recent-dash/docker-compose.yml#L1-L103)
- [docker-compose.infra.yml:1-101](file://recent-dash/docker-compose.infra.yml#L1-L101)
- [prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

## Core Components
- HTTP Server: Serves DASH video segments and manifests.
- HTTP Proxy: Acts as a caching proxy between client and server.
- HTTP Client: Exposes a DASH endpoint for players.
- Perf Monitor: Gathers CPU and memory metrics for monitored PIDs.
- bpftrace TX Tracer: Captures transmit traffic via kernel tracepoints (TX bytes).
- bcc RX Tracer: Captures receive traffic via eBPF socket filters (RX bytes).
- Observability Stack: Prometheus scraping, Coroot for visualization, ClickHouse for storage.

Key runtime behaviors:
- Container startup and port exposure are orchestrated via Docker Compose.
- PID discovery and aggregation are handled by the perf monitor using a shared PID file.
- Network tracing writes periodic CSV outputs for downstream analysis.
- Dual tracer architecture provides comprehensive TX/RX traffic visibility.

**Section sources**
- [docker-compose.yml:1-103](file://recent-dash/docker-compose.yml#L1-L103)
- [entrypoint.sh:1-24](file://recent-dash/entrypoint.sh#L1-L24)
- [monitor_pid_perf.sh:1-72](file://recent-dash/perf_monitor/monitor_pid_perf.sh#L1-L72)
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)
- [bcc_rx_bytes.py:1-120](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py#L1-L120)

## Architecture Overview
The system forms a three-tier streaming pipeline with integrated observability and dual-tracing architecture for comprehensive network monitoring.

```mermaid
sequenceDiagram
participant Player as "DASH Player"
participant Client as "HTTP Client"
participant Proxy as "HTTP Proxy"
participant Server as "HTTP Server"
participant Perf as "Perf Monitor"
participant BpfTX as "bpftrace TX Tracer"
participant BccRX as "bcc RX Tracer"
participant Prom as "Prometheus"
participant Coroot as "Coroot"
Player->>Client : GET manifest.mpd
Client->>Proxy : Forwarded request
Proxy->>Server : Fetch segments (with cache)
Server-->>Proxy : Video segments
Proxy-->>Client : Serve cached/fetched content
Client-->>Player : Stream segments
Note over Proxy,Server : TX traffic observed via bpftrace trace.csv
Note over Proxy,BccRX : RX traffic observed via bcc RX CSV
Note over Proxy,Perf : CPU/memory tracked via pidstat
Perf-->>Prom : Metrics scraped
BpfTX-->>Prom : TX metrics scraped
BccRX-->>Prom : RX metrics scraped
Prom-->>Coroot : Aggregated metrics
Coroot-->>Player : Dashboards and alerts
```

**Diagram sources**
- [docker-compose.yml:1-103](file://recent-dash/docker-compose.yml#L1-L103)
- [prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)
- [monitor_pid_perf.sh:1-72](file://recent-dash/perf_monitor/monitor_pid_perf.sh#L1-L72)
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)
- [bcc_rx_bytes.py:1-120](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py#L1-L120)

## Detailed Component Analysis

### HTTP Server
- Purpose: Hosts DASH segments and manifests.
- Configuration: Exposed on port 80; configurable via environment variables.
- Build: Clones the referenced repository and prepares binaries and public content.

Operational notes:
- Additional parameters can tune serving behavior.
- Public folder is mounted for serving content.

**Section sources**
- [HTTP-Server.Dockerfile:1-59](file://recent-dash/HTTP-Server.Dockerfile#L1-L59)
- [HTTP-Server.launch.sh:1-15](file://recent-dash/HTTP-Server.launch.sh#L1-L15)
- [docker-compose.yml:3-15](file://recent-dash/docker-compose.yml#L3-L15)

### HTTP Proxy
- Purpose: Caching proxy between client and server.
- Configuration: Accepts upstream server address/port and cache directory; supports additional parameters for cache policy and scheduling.
- Lifecycle: Entrypoint writes main and child PIDs to a shared location for monitoring.

Operational notes:
- Parameters include cache algorithm, rates, and queue sizes.
- PID file enables external performance monitoring.

**Section sources**
- [HTTP-Proxy.Dockerfile:1-49](file://recent-dash/HTTP-Proxy.Dockerfile#L1-L49)
- [HTTP-Proxy.launch.sh:1-20](file://recent-dash/HTTP-Proxy.launch.sh#L1-L20)
- [entrypoint.sh:1-24](file://recent-dash/entrypoint.sh#L1-L24)
- [docker-compose.yml:16-33](file://recent-dash/docker-compose.yml#L16-L33)

### HTTP Client
- Purpose: Exposes a DASH endpoint for clients (e.g., VLC).
- Configuration: Forwards requests to the configured proxy domain/port.
- Build: Copies the local binary and sets up a launch script.

Operational notes:
- Port mapping exposes the client service externally.
- Public folder is served as the DASH endpoint.

**Section sources**
- [HTTP-Client.Dockerfile:1-55](file://recent-dash/HTTP-Client.Dockerfile#L1-L55)
- [HTTP-Client.launch.sh:1-19](file://recent-dash/HTTP-Client.launch.sh#L1-L19)
- [docker-compose.yml:34-51](file://recent-dash/docker-compose.yml#L34-L51)

### Perf Monitor
- Purpose: Periodically aggregates CPU and memory metrics for a set of PIDs.
- Mechanism: Uses pidstat to sample at 1-second intervals; sums across PIDs and writes CSV with timestamp.
- Inputs: PID file path and output directory are configurable.

Operational notes:
- Continuously monitors until stopped.
- Produces a CSV suitable for correlation with network traces.

**Section sources**
- [monitor_pid_perf.sh:1-72](file://recent-dash/perf_monitor/monitor_pid_perf.sh#L1-L72)
- [docker-compose.yml:52-69](file://recent-dash/docker-compose.yml#L52-L69)

### bpftrace TX Tracer
- Purpose: Captures transmit (TX) traffic via kernel tracepoints.
- Mechanism: Monitors `net:net_dev_queue` and `net:netif_receive_skb` tracepoints; generates CSV with timestamped RX/TX byte counts.
- Inputs: Network interface name and debugfs/module paths are mounted.

Operational notes:
- Runs continuously until stopped.
- Outputs a CSV with timestamp and cumulative RX/TX bytes.
- Handles TX traffic by monitoring packet enqueue events.

**Section sources**
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)
- [docker-compose.yml:70-98](file://recent-dash/docker-compose.yml#L70-L98)

### bcc RX Tracer
- Purpose: Captures receive (RX) traffic via eBPF socket filters.
- Mechanism: Attaches to raw sockets on eth0 interface; filters by streamer IP and HPE port; maintains in-kernel byte counters.
- Inputs: STREAMER_IP, STREAMER_PORT, and HPE_PORT parameters.

Operational notes:
- Uses shared network namespace with HPE container for accurate traffic matching.
- Provides 10ms granularity RX byte measurements.
- Writes to `/opt/tracer/output/hpe_video_rx.csv`.

**Section sources**
- [bcc_rx_bytes.py:1-120](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py#L1-L120)
- [Dockerfile.bcc:1-49](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc#L1-L49)
- [run_experiment_bcc.sh:1-316](file://ffmpeg_hpe/run_experiment_bcc.sh#L1-L316)

### Observability Stack (Prometheus, Coroot, ClickHouse)
- Prometheus: Scrapes node and cluster agents, plus Coroot.
- Coroot: Provides dashboards and alerting, backed by ClickHouse.
- docker-compose.infra.yml defines volumes, ports, and service dependencies.

Operational notes:
- Prometheus configuration is mounted from prometheus.yml.
- Coroot bootstraps connections to Prometheus and ClickHouse.

**Section sources**
- [docker-compose.infra.yml:1-101](file://recent-dash/docker-compose.infra.yml#L1-L101)
- [prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

### Experiment Orchestration
- Purpose: Automates building, starting, measuring, and collecting artifacts from the monitoring stack.
- Features:
  - Measures container instantiation times.
  - Starts services in order and waits for readiness.
  - Copies performance and trace outputs to a dated results directory.
  - Collects container logs for diagnostics.
  - Supports both bpftrace TX and bcc RX tracer outputs.

Operational notes:
- Results are organized under a timestamped directory with logs, traces, and perf outputs.
- Summarizes proxy parameters and machine characteristics.
- Enhanced with BCC tracer integration for comprehensive RX monitoring.

**Section sources**
- [run_experiment.sh:1-286](file://recent-dash/run_experiment.sh#L1-L286)
- [run_experiment_bcc.sh:1-316](file://ffmpeg_hpe/run_experiment_bcc.sh#L1-L316)

## Network Monitoring Architecture

**Updated** Clarified the dual-tracing architecture and kernel context differences between TX and RX traffic capture.

The recent-dash system implements a sophisticated dual-tracing architecture that provides comprehensive visibility into network traffic characteristics:

### TX Traffic Monitoring (bpftrace)
- **Kernel Context**: Monitors transmit path via `net:net_dev_queue` tracepoint
- **Data Source**: `/opt/tracer/output/trace.csv` 
- **Traffic Scope**: Captures all outgoing packets from monitored interfaces
- **Measurement Method**: Tracks packet enqueue events for TX byte accumulation
- **Output Format**: `timestamp_ms,rx_bytes,tx_bytes` (cumulative values)

### RX Traffic Monitoring (bcc)
- **Kernel Context**: Monitors receive path via `netif_receive_skb` tracepoint
- **Data Source**: `/opt/tracer/output/hpe_video_rx.csv`
- **Traffic Scope**: Filters specific HPE video stream traffic
- **Measurement Method**: In-kernel aggregation with 10ms sampling intervals
- **Output Format**: `timestamp_ms,rx_video_bytes_delta,rx_video_bytes_current,rx_video_bytes_prev,dt_ms`

### Kernel Context Differences
The fundamental difference lies in where each tracer attaches in the network stack:

- **TX Path (bpftrace)**: Attaches to packet transmission events in the kernel's network device queue
- **RX Path (bcc)**: Attaches to packet reception events in the network stack's receive path

This architectural decision ensures comprehensive coverage of both directions of network traffic while leveraging the strengths of each tracing approach.

**Section sources**
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)
- [bcc_rx_bytes.py:1-120](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py#L1-L120)
- [bcc-bpf-tracing.md:1-364](file://docs/bcc-bpf-tracing.md#L1-L364)

## Dependency Analysis
The system exhibits clear service dependencies and shared resource usage:
- HTTP Client depends on HTTP Proxy.
- HTTP Proxy depends on HTTP Server.
- Perf Monitor and both Tracers rely on the host namespace and shared PID file.
- Observability services depend on each other and on Prometheus configuration.
- BCC tracer shares network namespace with HPE container for accurate RX traffic matching.

```mermaid
graph LR
HS["HTTP Server"] --> HP["HTTP Proxy"]
HP --> HC["HTTP Client"]
HP --> EP["Entrypoint PID file"]
PERF["Perf Monitor"] --> EP
BPFTRACE["bpftrace TX Tracer"] --> HS
BPFTRACE --> HP
BPFTRACE --> HC
BCC_TRACER["bcc RX Tracer"] --> HS
BCC_TRACER --> HP
BCC_TRACER --> HC
PROM["Prometheus"] --> COROOT["Coroot"]
COROOT --> CH["ClickHouse"]
```

**Diagram sources**
- [docker-compose.yml:1-103](file://recent-dash/docker-compose.yml#L1-L103)
- [docker-compose.infra.yml:1-101](file://recent-dash/docker-compose.infra.yml#L1-L101)
- [entrypoint.sh:1-24](file://recent-dash/entrypoint.sh#L1-L24)

**Section sources**
- [docker-compose.yml:1-103](file://recent-dash/docker-compose.yml#L1-L103)

## Performance Considerations
- Sampling cadence: Perf Monitor samples at 1-second intervals; adjust for overhead vs. resolution needs.
- bpftrace tracing overhead: Kernel tracepoints are lightweight but still introduce overhead; limit to necessary interfaces.
- bcc tracing overhead: eBPF socket filters provide very low overhead with in-kernel aggregation.
- Container isolation: Host PID and network modes enable precise monitoring but require elevated privileges.
- Disk I/O: Ensure sufficient disk space for CSV outputs and Prometheus/ClickHouse data retention.
- Dual tracer coordination: Both tracers operate independently but share the same timestamp context for correlation.

## Troubleshooting Guide

**Updated** Enhanced with specific guidance for traffic discrepancy analysis and dual-tracing architecture.

Common issues and remedies:
- **Empty bpftrace trace file**: Verify bpftrace permissions and debugfs mounts; confirm the interface name matches the host.
- **Missing PIDs**: Ensure the proxy entrypoint writes the PID file and that the perf monitor can read it.
- **Port conflicts**: Check port mappings for client and observability services; update docker-compose if needed.
- **Logs collection**: Use the experiment script to gather logs from all services into the results directory.
- **Connectivity**: Confirm DNS resolution for domains and that HTTP_PROXY_DOMAIN/IP are correctly set.
- **Traffic discrepancy analysis**: Use the RX/TX traffic discrepancy report to understand measurement differences between Docker stats, bpftrace, and HPE container RX.

### Traffic Discrepancy Analysis
When analyzing network traffic discrepancies:
- **Docker stats**: Comprehensive measurement including all protocol overhead and retransmissions
- **bpftrace trace.csv**: RX bytes measurement with potential payload-only counting
- **HPE container RX**: Application-level receive bytes with potential partial stream consumption

**Section sources**
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)
- [monitor_pid_perf.sh:1-72](file://recent-dash/perf_monitor/monitor_pid_perf.sh#L1-L72)
- [run_experiment.sh:155-191](file://recent-dash/run_experiment.sh#L155-L191)
- [Report on RX TX traffic discrepancy.md:1-109](file://Report on RX TX traffic discrepancy.md#L1-L109)

## Conclusion
The recent-dash monitoring system integrates a DASH streaming pipeline with a sophisticated dual-tracing architecture that captures both TX and RX traffic characteristics. The bpftrace-based TX tracer and bcc-based RX tracer provide comprehensive visibility into network performance, while pidstat-based performance monitoring tracks CPU and memory usage. All components are orchestrated via Docker Compose and observable through Prometheus, Coroot, and ClickHouse. The provided scripts and configurations enable repeatable experiments, artifact collection, and actionable insights for latency and bandwidth analysis in distributed streaming environments.

## Appendices

### Setup Procedures
- Build and start the streaming stack:
  - Build images and start services using the provided commands.
  - Connect a DASH client (e.g., VLC) to the client's exposed port using the manifest URL.
- Start monitoring:
  - Launch perf monitor, bpftrace TX tracer, and bcc RX tracer containers.
  - Verify CSV outputs appear in the designated directories for both TX and RX monitoring.
- Collect and correlate data:
  - Use the experiment orchestration script to gather logs, traces, and performance metrics into a timestamped results directory.
  - Correlate TX and RX measurements for comprehensive traffic analysis.

**Section sources**
- [README.md:1-20](file://recent-dash/README.md#L1-L20)
- [run_experiment.sh:70-153](file://recent-dash/run_experiment.sh#L70-L153)
- [run_experiment_bcc.sh:1-316](file://ffmpeg_hpe/run_experiment_bcc.sh#L1-L316)

### Packet Capture with bpftrace
- Ensure host PID and network namespaces are accessible.
- Mount debugfs and kernel modules; specify the correct network interface.
- Observe CSV output containing timestamped RX/TX byte counts from the TX tracer.

**Section sources**
- [docker-compose.yml:70-98](file://recent-dash/docker-compose.yml#L70-L98)
- [trace_container_net.sh:1-64](file://recent-dash/bpftrace-tracer/trace_container_net.sh#L1-L64)

### Packet Capture with bcc (RX)
- Configure bcc tracer with proper network namespace sharing.
- Set STREAMER_IP, STREAMER_PORT, and HPE_PORT parameters.
- Monitor `/opt/tracer/output/hpe_video_rx.csv` for RX byte measurements.

**Section sources**
- [bcc_rx_bytes.py:1-120](file://ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py#L1-L120)
- [Dockerfile.bcc:1-49](file://ffmpeg_hpe/bpftrace-tracer/Dockerfile.bcc#L1-L49)

### Real-Time Performance Monitoring
- Configure Prometheus to scrape node and cluster agents, plus Coroot.
- Use Coroot dashboards to visualize CPU, memory, and network metrics over time.
- Correlate TX/RX measurements from both tracers for comprehensive analysis.

**Section sources**
- [docker-compose.infra.yml:1-101](file://recent-dash/docker-compose.infra.yml#L1-L101)
- [prometheus.yml:1-23](file://recent-dash/prometheus.yml#L1-L23)

### Examples

#### Network Latency Analysis
- Correlate DASH manifest fetch times with proxy cache hits/misses.
- Use trace CSV timestamps to align with client playback events and compute per-request latencies.
- Analyze TX/RX traffic patterns to identify bottlenecks in the streaming pipeline.

#### Bandwidth Utilization Tracking
- Track RX/TX bytes per interval from both bpftrace and bcc tracer outputs.
- Aggregate over time windows to estimate throughput and identify spikes.
- Compare Docker stats with bpftrace measurements to validate accuracy.

#### Troubleshooting Distributed System Performance Issues
- Compare CPU and memory usage from the perf monitor against network throughput.
- Inspect proxy logs and cache parameters to diagnose stalls or excessive misses.
- Analyze traffic discrepancy reports to understand measurement differences and potential causes.

**Section sources**
- [monitor_pid_perf.sh:1-72](file://recent-dash/perf_monitor/monitor_pid_perf.sh#L1-L72)
- [HTTP-Proxy.launch.sh:1-20](file://recent-dash/HTTP-Proxy.launch.sh#L1-L20)
- [Report on RX TX traffic discrepancy.md:1-109](file://Report on RX TX traffic discrepancy.md#L1-L109)