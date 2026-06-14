# eBPF Tracing Diagram

This diagram mirrors the structure of your reference image, but it is customized for the RX tracing path in this repository.

```mermaid
flowchart LR
    subgraph Develop["Develop"]
        direction TB
        src["ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py<br/>Python loader + embedded C BPF"]
        boot["ffmpeg_hpe/bpftrace-tracer/entrypoint.sh<br/>resolves interface, RTSP broker IP, and HPE port"]
        src --> boot
    end

    subgraph Node["Linux Node"]
        direction LR

        subgraph User["User Space"]
            direction TB
            tracer["bcc-tracer container"]
            hpe["hpe container<br/>connects to rtsp-broker:8554"]
            rtsp["rtsp-broker<br/>MediaMTX"]
            out["hpe_video_rx.csv<br/>10 ms RX samples"]
        end

        subgraph Kernel["Kernel Space"]
            direction TB
            verify["Verify"]
            jit["JIT compiled"]
            load["Load"]
            hook["Attach raw socket hook"]
            maps["eBPF maps<br/>rx_bytes[0]"]
        end
    end

    src -->|1| verify
    boot --> tracer
    verify -->|2| jit
    jit -->|3| load
    load -->|4| hook
    hook -->|5| maps
    tracer -->|reads map every 10 ms| maps
    hpe -->|stream packets from RTSP| rtsp
    rtsp -->|RX traffic on HPE network namespace| hook
    maps -->|writes deltas| out
```

## How to read it

- `bcc_rx_bytes.py` builds the embedded BPF program and loads it through BCC.
- `entrypoint.sh` discovers the interface and the active RTSP/HPE ports before launching the tracer.
- The kernel validates the program, JIT-compiles it, loads it, and attaches it to the raw socket hook.
- The `bcc-tracer` container samples the `rx_bytes` map every 10 ms and writes the RX bandwidth trace to `hpe_video_rx.csv`.

> If you want the TX side too, the separate `perf_monitor` path uses `monitor_hpe/monitor_pid.sh` and a `sys_enter_sendto` bpftrace hook. That is a different diagram from this RX flow.
