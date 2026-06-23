# Project Review: FFmpeg HPE with Network Monitoring

## Current Implementation

### 1. Streaming Setup
- RTSP server container streaming H.264 video
- Containerized HPE MoveNet algorithm for stream processing
- BPF tracer for network monitoring

### 2. Measurement Approach
- BPF script captures RX bytes at 100ms intervals
- Tracks TCP traffic on port 8089
- Outputs timestamps and byte counts to CSV

### 3. Infrastructure
- Docker Compose for service orchestration
- Resource limits and health checks implemented
- GPU metrics collection

## Strengths

1. **Container Isolation**: Good separation of concerns
2. **Resource Management**: Proper CPU/memory limits
3. **Data Collection**: Structured metrics collection

## Areas for Improvement

### 1. Network Measurement Accuracy
**Current**: Using `sk_rmem_alloc` which shows kernel buffer usage.

**Recommended**:
```c
kretprobe:__netif_receive_skb
{
    $skb = (struct sk_buff *)arg0;
    $ip = $skb->head + $skb->network_header;
    $tcp = $ip + ($ip->ihl * 4);
    
    if ($tcp->dest == htons($TARGET_PORT)) {
        @rx_bytes = $skb->len;
    }
}

### 2. Timing Precision
**Current**: Sampling at 100ms intervals
**Recommended**:
  * Consider 10ms sampling for H.264
  * Add hardware timestamps if needed

###3. IP Camera Emulation
  * Add RTSP authentication
  * Implement SDP negotiation
  * Support multiple streams
  * Simulate network conditions

### 4. Data Analysis
  * Bitrate calculation
  * Frame size distribution
  * Inter-arrival time analysis

### Implementation Plan
    * **Update BPF Script**
        + Use kretprobe:__netif_receive_skb
        + Add packet drop monitoring
    * **Enhance Streaming**
        + Add RTSP authentication
        + Implement SDP
        + Support multiple streams
    * **Improve Metrics**
        + Add bitrate calculation
        + Track frame sizes
        + Monitor timing

---

## Interpreting CPU Utilization

Docker reports CPU usage as a percentage of a single host core:
- **100%** = 1 full host core
- A container with `cpus: "1.75"` can use up to **175%**
- A container with `cpus: "3.0"` can use up to **300%**

The `perf_monitor` CSV column `total_cpu_percent` always represents
percentage of **1 host core**. To calculate saturation of the container's
CPU budget:

```
saturation_pct = reported_cpu / (container_cpu_limit × 100) × 100
```

**Example:** `perf_monitor` reports `165%` for a 3.0-CPU HPE container.
The container is using 1.65 cores out of 3.0 (55% saturation, 45% headroom).