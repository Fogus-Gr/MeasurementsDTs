# Analysis: OpenVINO Configuration Usefulness for `monitor_hpe` Rig

## Question

Is the OpenVINO configuration code in `openvino_base_hpe.py` (lines 64-92) useful for the `monitor_hpe` experiment rig?

---

## TL;DR Answer

**YES, but it's using suboptimal defaults.** The OpenVINO configuration is useful and affects performance, but `monitor_hpe` doesn't set any environment variables, so it uses hardcoded defaults that may not be optimal for the 4-core container.

---

## Current State Analysis

### What `monitor_hpe` Does

**Purpose:** Baseline CPU monitoring experiment (no streaming server)
- Runs HPE inference on local video files
- Monitors CPU usage, memory, and process metrics
- Measures raw inference performance without network overhead

**Container Resources:**
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Up to 4 cores
      memory: 4G
    reservations:
      cpus: '2.0'      # Guaranteed 2 cores
      memory: 2G
```

### OpenVINO Configuration in `openvino_base_hpe.py`

**Default Values (when no env vars set):**
```python
self.ov_threads = 1                    # Only 1 thread!
self.ov_mode = "latency"               # Latency mode
self.ov_streams = None                 # Auto (typically 1 for latency mode)
self.ov_cpu_pinning = False            # No CPU pinning
self.ov_hyper_threading = False        # Hyper-threading disabled
```

**What These Settings Do:**

1. **`ov_threads=1`** → OpenVINO uses only 1 CPU thread for inference
   - **Problem:** Container has 4 cores available, but only using 1
   - **Impact:** Severely underutilizes available CPU resources

2. **`ov_mode="latency"`** → Optimizes for single-request latency
   - **Appropriate for:** Real-time single-stream processing
   - **Alternative:** `"throughput"` mode for batch processing

3. **`ov_streams=None`** → Auto-determined (typically 1 for latency mode)
   - **Impact:** Single inference stream

4. **`ov_cpu_pinning=False`** → Threads can migrate between cores
   - **Impact:** Potential cache misses, less consistent performance

5. **`ov_hyper_threading=False`** → Doesn't use logical cores
   - **Impact:** May leave performance on the table if HT is available

---

## Performance Impact

### Current Configuration (Defaults)

```
Container: 4 cores available
OpenVINO: 1 thread, latency mode
Utilization: ~25% of available CPU (1 core out of 4)
```

**Result:** Significant underutilization of container resources.

### Optimal Configuration for `monitor_hpe`

Since `monitor_hpe` is a **baseline performance measurement** rig, it should use resources efficiently:

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - OV_THREADS=4              # Use all 4 cores
  - OV_MODE=latency           # Keep latency mode for single-stream
  - OV_CPU_PINNING=true       # Pin threads for consistent performance
  - OV_HYPER_THREADING=false  # Disable HT for more predictable results
```

**Expected Impact:**
- **Throughput:** 2-4x improvement (depending on model parallelizability)
- **CPU Utilization:** ~100% instead of ~25%
- **Consistency:** Better with CPU pinning

---

## Comparison with Other Rigs

### `ffmpeg_hpe` Rig

**Purpose:** Full monitoring stack with RTSP streaming

**Current State:** Also doesn't set OpenVINO env vars (same defaults)

**Recommendation:** Should also configure OpenVINO threads based on `HPE_METHOD`

### `optimizations/` Directory

**Purpose:** Dedicated CPU optimization experiments

**Current State:** Has `enhanced_openvino_hpe.py` with sophisticated CPU optimization

**Difference:** Uses `EPICCPUOptimizer` to auto-detect optimal settings based on CPU topology

---

## Recommendations

### 1. For `monitor_hpe` (Immediate)

**Add OpenVINO configuration to `docker-compose.yaml`:**

```yaml
services:
  hpe:
    environment:
      - PYTHONUNBUFFERED=1
      - OV_THREADS=4              # Match container CPU limit
      - OV_MODE=latency           # Single-stream optimization
      - OV_CPU_PINNING=true       # Consistent performance
      - OV_HYPER_THREADING=false  # Predictable measurements
```

**Why:**
- Utilizes all 4 available cores
- More accurate baseline measurements
- Consistent, reproducible results

### 2. For `ffmpeg_hpe` (Recommended)

**Make OpenVINO threads conditional on method:**

```yaml
services:
  hpe:
    environment:
      - OV_THREADS=${OV_THREADS:-4}
      - OV_MODE=${OV_MODE:-latency}
      - OV_CPU_PINNING=${OV_CPU_PINNING:-true}
```

**In `run_experiment.sh`:**
```bash
# Set OpenVINO threads based on method complexity
case "$HPE_METHOD" in
  openpose|alphapose)
    export OV_THREADS=4  # Complex models benefit from more threads
    ;;
  movenet|ae1|ae2|ae3)
    export OV_THREADS=2  # Simpler models, leave headroom for monitoring
    ;;
esac
```

### 3. For All Rigs (Best Practice)

**Document OpenVINO tuning in README:**

```markdown
## Performance Tuning

### OpenVINO Configuration

Control inference performance via environment variables:

- `OV_THREADS`: Number of CPU threads (default: 1)
- `OV_MODE`: `latency` or `throughput` (default: latency)
- `OV_STREAMS`: Number of inference streams (default: auto)
- `OV_CPU_PINNING`: Pin threads to cores (default: false)
- `OV_HYPER_THREADING`: Use logical cores (default: false)

Example:
```bash
OV_THREADS=4 OV_CPU_PINNING=true ./run_experiment.sh movenet
```
```

---

## Verdict

### Is the OpenVINO configuration code useful?

✅ **YES** — The configuration code is useful and necessary for performance tuning.

### Is it being used effectively in `monitor_hpe`?

❌ **NO** — `monitor_hpe` doesn't set any OpenVINO env vars, so it uses suboptimal defaults (1 thread on a 4-core container).

### Should it be removed?

❌ **NO** — Keep the code, but **add proper configuration** to `monitor_hpe/docker-compose.yaml`.

---

## Impact Summary

| Aspect | Current (1 thread) | Recommended (4 threads) | Improvement |
|---|---|---|---|
| CPU Utilization | ~25% | ~100% | 4x |
| Throughput (FPS) | Baseline | 2-4x higher | 2-4x |
| Measurement Accuracy | Good | Better (full load) | More realistic |
| Reproducibility | Good | Better (with pinning) | More consistent |

---

## Action Items

### High Priority
1. ✅ Add OpenVINO env vars to `monitor_hpe/docker-compose.yaml`
2. ✅ Add OpenVINO env vars to `ffmpeg_hpe/docker-compose.yaml`

### Medium Priority
3. Document OpenVINO tuning in README
4. Add OpenVINO configuration to `run_experiment.sh` scripts

### Low Priority
5. Consider auto-detecting optimal thread count based on container CPU limit
6. Add performance comparison tests (1 thread vs. 4 threads)

---

## Example Fix for `monitor_hpe/docker-compose.yaml`

```yaml
services:
  hpe:
    image: monitor-hpe:latest
    build:
      context: ..
      dockerfile: Dockerfile_base
    entrypoint: ["/app/entrypoint.sh"]
    command: python3 main.py --method movenet --input /videos/${VIDEO_FILE:-ultimatum/hd_00_00.mp4}
    pid: "host"
    cap_add:
      - SYS_PTRACE
    security_opt:
      - seccomp=unconfined
    volumes:
      - ./pids:/pids:rw
      - /home/user/MeasurementsDTs/videos:/videos:ro
    environment:
      - PYTHONUNBUFFERED=1
      # OpenVINO CPU optimization for 4-core container
      - OV_THREADS=4
      - OV_MODE=latency
      - OV_CPU_PINNING=true
      - OV_HYPER_THREADING=false
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G
```

**Expected Result:** 2-4x higher FPS with full CPU utilization.
