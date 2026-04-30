# BCC/BPF Network Tracing — Deep Dive

## Overview

This document explains the kernel-level network traffic tracing system used to measure RX (received) bytes during HPE experiments. The system uses eBPF (Extended Berkeley Packet Filter) via the BCC (BPF Compiler Collection) Python library.

---

## Why BPF Instead of tcpdump?

| Concern | BPF Advantage |
|---------|---------------|
| **Overhead** | BPF programs run in kernel space — no context switches per packet |
| **Filtering** | C-like programs compiled to BPF bytecode filter at kernel level |
| **Granularity** | Can filter by exact source/destination port |
| **I/O** | Only counts bytes; does not store packet data |
| **Precision** | Aggregates in-kernel, reads periodically (10 ms) from userspace |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ Kernel Space                                          │
│                                                        │
│  ┌──────────────────────────────────────────┐        │
│  │ BPF Socket Filter (count_rx)             │        │
│  │                                           │        │
│  │ 1. Parse Ethernet header                 │        │
│  │ 2. Filter IPv4 only                      │        │
│  │ 3. Filter TCP only                       │        │
│  │ 4. Read packet length                    │        │
│  │ 5. Accumulate in BPF_HASH map            │        │
│  │                                           │        │
│  │ rx_bytes[key=0] += packet_len            │        │
│  └──────────────────────────────────────────┘        │
│                                                        │
└──────────────────────────────────────────────────────┘
         ↑ attach_raw_socket(eth0)
         │
┌────────┴─────────────────────────────────────────────┐
│ User Space (bcc_rx_bytes.py)                          │
│                                                        │
│  Every 10ms:                                          │
│    current = rx_bytes[0]                              │
│    delta = current - previous                         │
│    Write: timestamp, delta, current, previous, dt_ms  │
│    previous = current                                 │
│                                                        │
│  Output: /opt/tracer/output/hpe_video_rx.csv          │
└──────────────────────────────────────────────────────┘
```

---

## The BCC Python Program (`bcc_rx_bytes.py`)

### Arguments

```bash
python3 bcc_rx_bytes.py <STREAMER_IP> <STREAMER_PORT> <HPE_PORT>
```

| Argument | Example | Description |
|----------|---------|-------------|
| `STREAMER_IP` | `172.18.0.2` | IP of the h264-streaming-server container |
| `STREAMER_PORT` | `8089` | Port the streamer listens on |
| `HPE_PORT` | _(auto-detected)_ | HPE's dynamic ephemeral source port |

---

### BPF C Program (embedded in Python)

```c
BPF_HASH(rx_bytes, u32, u64);  // Hash map: key=0, value=cumulative bytes

int count_rx(struct __sk_buff *skb) {
    // Parse Ethernet header
    struct ethhdr eth;
    bpf_skb_load_bytes(skb, 0, &eth, sizeof(eth));
    if (eth.h_proto != htons(ETH_P_IP)) return 0;  // IPv4 only

    // Parse IP header
    struct iphdr ip;
    bpf_skb_load_bytes(skb, ETH_HLEN, &ip, sizeof(ip));
    if (ip.protocol != IPPROTO_TCP) return 0;  // TCP only

    // Parse TCP header
    struct tcphdr tcp;
    bpf_skb_load_bytes(skb, ETH_HLEN + sizeof(ip), &tcp, sizeof(tcp));

    // Accumulate packet length
    u32 key = 0;
    u64 *val = rx_bytes.lookup_or_try_init(&key, &zero);
    if (val) { *val += skb->len; }

    return 0;  // Allow packet through
}
```

---

### BPF Attachment

```python
b = BPF(text=bpf_program, cflags=["-Wno-macro-redefined", "-Wno-address-of-packed-member"])
fn = b.load_func("count_rx", BPF.SOCKET_FILTER)
b.attach_raw_socket(fn, "eth0")
```

---

### Main Loop

```python
while True:
    current = rx_bytes[c_uint(0)].value
    delta = current - prev_bytes
    dt_ms = (now - prev_time) * 1000
    writer.writerow([timestamp_ms, delta, current, prev_bytes, dt_ms])
    prev_bytes = current
    prev_time = now
    sleep(0.01)  # 10ms interval
```

---

### Output CSV Format

**File**: `/opt/tracer/output/hpe_video_rx.csv`

| Column | Type | Description |
|--------|------|-------------|
| `timestamp_ms` | int | Milliseconds since epoch |
| `rx_video_bytes_delta` | int | RX bytes in this 10 ms interval |
| `rx_video_bytes_current` | int | Cumulative RX bytes to this point |
| `rx_video_bytes_prev` | int | Cumulative from previous interval |
| `dt_ms` | float | Actual elapsed time since last sample |

---

## Port Detection Mechanism (`entrypoint.sh`)

### How It Works

1. **Resolve streaming server hostname** to IP:
   ```bash
   getent hosts h264-streaming-server
   ```

2. **Get network interface** from default route:
   ```bash
   ip route | awk '/default/ {print $5}'
   ```

3. **Wait for HPE to establish TCP connection** to port 8089 (up to 10 attempts, 3 s apart):
   ```bash
   ss -ntp | grep ":8089"
   ```

4. **Extract HPE's dynamic source port**:
   ```bash
   ss -ntp | awk '/:8089/ {split($4, a, ":"); print a[length(a)]}' | head -1
   ```

5. **Pass detected port** to `bcc_rx_bytes.py`.

### Why Port Detection?

- HPE connects to the streamer on port `8089` but uses a random ephemeral source port.
- The BCC tracer shares HPE's network namespace (`network_mode: service:hpe`).
- It needs the exact source port to filter traffic accurately.
- Port detection runs **after** HPE starts and establishes the connection.

---

## Container Configuration

### Docker Compose Settings

```yaml
bcc-tracer:
  build:
    context: ./bpftrace-tracer
    dockerfile: Dockerfile.bcc
  volumes:
    - ./tracer_output:/opt/tracer/output
    - /lib/modules:/lib/modules:ro         # Kernel modules
    - /usr/src:/usr/src:ro                 # Kernel headers
    - /sys/kernel/debug:/sys/kernel/debug  # Debug/tracing interface
  user: root
  privileged: true
  network_mode: "service:hpe"              # Shares HPE's network namespace
  cap_add:
    - SYS_ADMIN      # Load BPF programs
    - NET_ADMIN      # Raw socket access
    - NET_RAW        # Raw socket access
    - IPC_LOCK       # Memory locking for BPF maps
    - SYS_RESOURCE   # Resource limit manipulation
  security_opt:
    - seccomp:unconfined
```

### Why These Privileges?

| Setting | Reason |
|---------|--------|
| `privileged: true` | Required for BPF program loading |
| `SYS_ADMIN` | Load BPF programs into the kernel |
| `NET_ADMIN` + `NET_RAW` | Create raw sockets for packet capture |
| `IPC_LOCK` | Lock BPF map memory pages (prevent swapping) |
| `SYS_RESOURCE` | Adjust resource limits for BPF maps |
| `seccomp: unconfined` | BPF syscalls are blocked by the default seccomp profile |
| `/lib/modules` + `/usr/src` | Kernel module and header access for BCC compilation |
| `/sys/kernel/debug` | Tracing filesystem interface |
| `network_mode: service:hpe` | See the same network interfaces as the HPE container |

---

## Kernel Requirements

### Minimum Kernel Version

| Version | Notes |
|---------|-------|
| **4.4+** | Basic eBPF support |
| **5.4+** | Full socket filter support (project runs on `5.4.0-216-generic`) |

### Required Kernel Config

```
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y
CONFIG_HAVE_EBPF_JIT=y
CONFIG_NET_CLS_BPF=m  # (or y)
CONFIG_BPF_EVENTS=y
```

### Verification

```bash
# Check BPF kernel options
grep -E "CONFIG_BPF" /boot/config-$(uname -r)

# Check for BPF errors at boot
dmesg | grep -i bpf
```

---

## `Dockerfile.bcc` Build

### Build Steps

1. **Base image**: Ubuntu (inherited from context)
2. **System dependencies**: `python3`, `pip`, `cmake`, `gcc`, `git`, `llvm`, `clang`, `tcpdump`, `iproute2`, `net-tools`
3. **BCC from source** (v0.25.0):
   ```bash
   git clone --depth 1 --branch v0.25.0 https://github.com/iovisor/bcc.git /tmp/bcc
   mkdir /tmp/bcc/build && cd /tmp/bcc/build
   cmake .. -DCMAKE_INSTALL_PREFIX=/usr
   make && make install
   rm -rf /tmp/bcc
   ```
4. **Python requirements**: `pip install` from `requirements.txt`
5. **Copy application files**: `bcc_rx_bytes.py`, `entrypoint.sh`

---

## Alternative Tracing Approaches

### Comparison Table

| Approach | Tool | File | Overhead | Precision | Best For |
|----------|------|------|----------|-----------|----------|
| **BCC** _(primary)_ | Python BPF API | `bcc_rx_bytes.py` | Very low | 10 ms intervals | Production benchmarks |
| **bpftrace** | bpftrace DSL | `trace_video_traffic.sh` | Very low | Event-level | Quick debugging |
| **tcpdump** | Packet capture | `trace_video_traffic_tcpdump.sh` | Medium | Full packets | Deep packet analysis |

### bpftrace Approach (`trace_video_traffic.sh`)

- Uses bpftrace one-liner scripts.
- Traces `tracepoint:net:netif_receive_skb` and `tracepoint:syscalls:sys_enter_sendto`.
- Simpler but less programmable than BCC.

### tcpdump Approach (`trace_video_traffic_tcpdump.sh`)

- Full packet capture:
  ```bash
  tcpdump -i eth0 tcp port 8089 -nn -tt
  ```
- Higher overhead — writes full packet data to disk.
- Useful for debugging: analyze packet contents, TCP flags, retransmissions.
- Post-processing with `grep`/`awk` to extract byte counts.

---

## Troubleshooting

### BCC Fails to Start

```bash
# Check kernel BPF support
grep -E "CONFIG_BPF" /boot/config-$(uname -r)

# Check dmesg for BPF errors
dmesg | grep -i bpf

# Verify kernel headers are installed
ls /lib/modules/$(uname -r)/build/
```

### Port Detection Fails

```bash
# Check HPE has established the connection
docker exec bcc-tracer ss -ntp | grep 8089

# Inspect tracer logs
docker logs bcc-tracer 2>&1 | grep -i "port\|detect\|monitor"

# Manual port extraction
docker exec bcc-tracer ss -ntp | awk '/:8089/ {split($4, a, ":"); print a[length(a)]}'
```

### Empty or Zero RX Data

```bash
# Verify the stream is flowing
curl -v http://172.18.0.2:8089/stream.h264 | head -c 100

# Check BCC attachment logs
docker logs bcc-tracer 2>&1 | tail -20

# Verify network namespace sharing (should show HPE's interfaces)
docker exec bcc-tracer ip addr
```

### Quick Data Validation

```bash
# Total RX bytes (in MB)
awk -F, 'NR>1 {sum+=$2} END {print sum/1024/1024 " MB"}' hpe_video_rx.csv

# Count non-zero intervals
awk -F, 'NR>1 && $2>0 {count++} END {print count " non-zero intervals"}' hpe_video_rx.csv

# Show start and end timestamps
head -2 hpe_video_rx.csv && echo "..." && tail -1 hpe_video_rx.csv
```

---

## Summary

The BCC/BPF tracing stack provides a low-overhead, kernel-level measurement of network RX bytes with 10 ms granularity. Key design decisions:

- **In-kernel aggregation** eliminates per-packet userspace overhead.
- **Shared network namespace** (`network_mode: service:hpe`) ensures the tracer sees exactly the same traffic as the HPE process.
- **Dynamic port detection** handles the ephemeral source port assigned by the OS when HPE opens its TCP connection to the streamer.
- **Raw socket filter** (not XDP or tc) keeps the implementation portable across kernel versions ≥ 4.4.
