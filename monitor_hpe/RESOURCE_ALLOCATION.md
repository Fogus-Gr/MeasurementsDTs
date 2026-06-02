# Resource Allocation — `monitor_hpe` Rig

## Overview

The `monitor_hpe` experiment rig **automatically detects and adapts** to the available vCPUs on the host system. It works on any VM with **4 or more vCPUs**.

This document describes the resource allocation strategy. For complete usage instructions and auto-scaling behavior across different VM sizes, see:
- [`USAGE.md`](USAGE.md) — Complete usage guide with examples
- [`SCALING_GUIDE.md`](SCALING_GUIDE.md) — Auto-scaling behavior for 4-32 vCPU VMs

---

## Current Configuration (8-vCPU Cloud VM)

The default configuration is optimized for an **8-vCPU cloud GPU VM** with the following resource allocation:

- **HPE Service:** 6 vCPUs (OpenVINO inference)
- **Monitor Service:** 2 vCPUs (bpftrace monitoring)
- **Total:** 8 vCPUs

**Note:** These values are automatically adjusted based on the detected vCPU count and HPE method. See [`SCALING_GUIDE.md`](SCALING_GUIDE.md) for details.

---

## Configuration

### HPE Service (6 vCPUs)

```yaml
hpe:
  environment:
    - OV_THREADS=6              # Use 6 CPU threads for OpenVINO
    - OV_MODE=latency           # Optimize for single-stream latency
    - OV_CPU_PINNING=true       # Pin threads to cores for consistency
    - OV_HYPER_THREADING=false  # Disable HT for predictable measurements
  deploy:
    resources:
      limits:
        cpus: '6.0'             # Maximum 6 cores
        memory: 6G              # 6GB memory
      reservations:
        cpus: '4.0'             # Guaranteed 4 cores
        memory: 4G              # Guaranteed 4GB
```

**Rationale:**
- OpenVINO models (MoveNet, OpenPose, HigherHRNet, EfficientHRNet) benefit from multi-threading
- 6 threads provide optimal parallelization without starving the monitor service
- CPU pinning ensures consistent, reproducible performance measurements
- Hyper-threading disabled for more predictable CPU cycle measurements

### Monitor Service (2 vCPUs)

```yaml
monitor:
  deploy:
    resources:
      limits:
        cpus: '2.0'             # Maximum 2 cores
        memory: 512M            # 512MB memory
      reservations:
        cpus: '1.0'             # Guaranteed 1 core
        memory: 256M            # Guaranteed 256MB
```

**Rationale:**
- bpftrace monitoring is lightweight but needs headroom for burst activity
- 2 cores ensure monitoring doesn't interfere with HPE measurements
- Prevents resource contention during peak monitoring activity

---

## Resource Distribution for an 8 vCPU Cloud VM

```
┌─────────────────────────────────────────────────────────┐
│                    8-vCPU Cloud VM                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │         HPE Service (6 vCPUs)                │      │
│  │  - OpenVINO inference                        │      │
│  │  - OV_THREADS=6                              │      │
│  │  - CPU pinning enabled                       │      │
│  │  - Memory: 6GB                               │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │      Monitor Service (2 vCPUs)               │      │
│  │  - bpftrace CPU/memory monitoring            │      │
│  │  - Minimal interference                      │      │
│  │  - Memory: 512MB                             │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Performance Expectations

### Before (4 vCPUs, 1 OpenVINO thread)

```
CPU Allocation:  4 cores for HPE
OpenVINO:        1 thread
Utilization:     ~25% (1 core out of 4)
Throughput:      Baseline FPS
```

### After (6 vCPUs, 6 OpenVINO threads)

```
CPU Allocation:  6 cores for HPE
OpenVINO:        6 threads
Utilization:     ~100% (all 6 cores)
Throughput:      3-6x baseline FPS (model-dependent)
```

**Expected Improvements:**

| Model | Threads | Expected FPS Gain | Notes |
|---|---|---|---|
| MoveNet | 1 → 6 | 2-3x | Lightweight model, moderate parallelization |
| OpenPose | 1 → 6 | 4-6x | Complex model, excellent parallelization |
| HigherHRNet | 1 → 6 | 3-5x | Medium complexity, good parallelization |
| EfficientHRNet | 1 → 6 | 3-5x | Medium complexity, good parallelization |

---

## Tuning Guidelines

### Automatic Scaling

The `run_experiment.sh` script **automatically detects** the available vCPUs and adjusts resource allocation accordingly. No manual configuration is needed for different VM sizes.

See [`SCALING_GUIDE.md`](SCALING_GUIDE.md) for detailed auto-scaling behavior across 4-32 vCPU VMs.

### Manual Override (Advanced)

If you need to override the automatic allocation, you can set environment variables:

```bash
# Force specific thread count
OV_THREADS=4 ./run_experiment.sh movenet

# Force specific CPU/memory limits
HPE_CPU_LIMIT=4.0 HPE_MEMORY_LIMIT=8G ./run_experiment.sh movenet
```

### Historical Reference: Manual Configuration for Different VM Sizes

Before auto-scaling was implemented, manual configuration was required. These examples are kept for reference:

**4-vCPU VM:**
```yaml
hpe:
  environment:
    - OV_THREADS=3
  deploy:
    resources:
      limits:
        cpus: '3.0'

monitor:
  deploy:
    resources:
      limits:
        cpus: '1.0'
```

**16-vCPU VM:**
```yaml
hpe:
  environment:
    - OV_THREADS=14
  deploy:
    resources:
      limits:
        cpus: '14.0'

monitor:
  deploy:
    resources:
      limits:
        cpus: '2.0'
```

**General Rule:** Allocate 75-80% of vCPUs to HPE, 20-25% to monitoring.

---

## Verification

### Check Resource Allocation

```bash
# Start the experiment
cd monitor_hpe
./run_experiment.sh

# In another terminal, check CPU usage
docker stats

# Expected output:
# CONTAINER       CPU %     MEM USAGE
# monitor-hpe     ~600%     (6 cores × 100%)
# monitor-monitor ~50-100%  (burst activity)
```

### Verify OpenVINO Configuration

Check HPE container logs for OpenVINO settings:

```bash
docker logs monitor-hpe-hpe-1 | grep "OpenVINO Configuration" -A 10
```

**Expected output:**
```
[OpenVINO Configuration]
  Requested settings: threads=6, mode=latency, streams=None
  Effective settings:
    Performance mode: LATENCY
    CPU threads: 6
    CPU streams: 1
    CPU pinning: True
    Hyper-threading: False
```

---

## Troubleshooting

### Issue: HPE using less than 6 cores

**Symptom:** `docker stats` shows HPE at ~100-200% CPU instead of ~600%

**Causes:**
1. OpenVINO env vars not set correctly
2. Model doesn't parallelize well
3. I/O bottleneck (video decoding)

**Solution:**
```bash
# Check env vars
docker exec monitor-hpe-hpe-1 env | grep OV_

# Should show:
# OV_THREADS=6
# OV_MODE=latency
# OV_CPU_PINNING=true
# OV_HYPER_THREADING=false
```

### Issue: Monitor service interfering with HPE

**Symptom:** Inconsistent FPS, high variance in measurements

**Solution:** Increase monitor CPU limit to 2.0 (already done in current config)

---

## Related Files

- `run_experiment.sh` — Experiment orchestration script with auto-scaling implementation
- `docker-compose.yaml` — Resource allocation configuration with dynamic env vars
- `monitor_pid.sh` — bpftrace monitoring script
- `plot_graph.py` — Results visualization
- [`USAGE.md`](USAGE.md) — Complete usage guide with examples
- [`SCALING_GUIDE.md`](SCALING_GUIDE.md) — Auto-scaling behavior for 4-32 vCPU VMs

---

## References

- OpenVINO Performance Hints: https://docs.openvino.ai/latest/openvino_docs_OV_UG_Performance_Hints.html
- Docker Resource Constraints: https://docs.docker.com/config/containers/resource_constraints/
- CPU Pinning Best Practices: https://docs.openvino.ai/latest/openvino_docs_deployment_optimization_guide_dldt_optimization_guide.html

---

## See Also

- [../README.md](../README.md) — Main project README
- [../AGENTS.md](../AGENTS.md) — Agent guidance for working in this repository
- [../ffmpeg_hpe/](../ffmpeg_hpe/) — Full monitoring stack with RTSP streaming
- [../COMPLETE_AUDIT_SUMMARY.md](../COMPLETE_AUDIT_SUMMARY.md) — Complete audit and fixes summary
- [../OPENVINO_CONFIG_USEFULNESS_ANALYSIS.md](../OPENVINO_CONFIG_USEFULNESS_ANALYSIS.md) — OpenVINO configuration analysis
