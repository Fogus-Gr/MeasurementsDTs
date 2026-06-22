# CPU Tuning Guide (OpenVINO)

This document distills the relevant CPU performance optimization strategies originally developed in the `archive/optimizations/` folder, updated to reflect the current containerized architecture of the project.

## Why the Old Python Scripts Were Retired
The `archive/optimizations/` folder contained Python scripts (`cpu_performance_optimizer.py` and `enhanced_openvino_hpe.py`) that attempted to dynamically inject OpenVINO settings and execute host-level system commands. These were retired and moved to the archive because:
1. **Docker Incompatibility:** System-level commands like `cpupower frequency-set` and modifying `/proc/sys/kernel/numa_balancing` fail inside unprivileged Docker containers.
2. **Cgroup Ignorance:** The old scripts used `psutil.cpu_count()` which detects the host's total physical cores, ignoring the strict CPU limits set by Docker `docker-compose.yaml`.
3. **Better Alternatives:** The active codebase (`openvino_base_hpe.py`) now natively uses `os.sched_getaffinity()` to accurately detect cgroup-limited cores, and manages configuration purely through environment variables (`.env`).

## Plausible and Active Optimizations

While the old scripts are deprecated, the **configuration principles** they established are highly valid and actively used in the `ffmpeg_hpe` and `ffmpeg_hpe_cpu` experiment rigs.

### 1. Environment-Driven OpenVINO Tuning
Instead of hardcoding thread counts in Python, the optimal thread count should be passed to the Docker containers via `.env` files.

**For a compute-heavy configuration (e.g., 6 vCPUs):**
```env
OV_MODE=throughput
OV_STREAMS=1
OV_THREADS=6
OMP_NUM_THREADS=6
MKL_NUM_THREADS=6
OPENBLAS_NUM_THREADS=6
```
*Why this works:* Aligning `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, and `OPENBLAS_NUM_THREADS` exactly with `OV_THREADS` prevents thread contention between OpenVINO's backend and the underlying math libraries.

#### Variable Explanations

| Variable | Description |
|---|---|
| `OV_MODE` | Optimization hint. `latency` minimizes response time for a single frame; `throughput` maximizes overall FPS by processing multiple frames concurrently. |
| `OV_STREAMS` | Number of parallel execution queues. `1` focuses all power on single-frame latency; higher values divide cores to process multiple images simultaneously. |
| `OV_THREADS` | Maximum number of CPU threads the OpenVINO execution engine is allowed to spawn. Set this to match container CPU limits. |
| `OV_CPU_PINNING` | Set to `true` to bind inference threads to specific CPU cores. Reduces context switching and improves cache locality. |
| `OV_HYPER_THREADING` | Set to `false` to restrict OpenVINO to physical cores only. Usually yields better performance for vector-math heavy neural network inference by avoiding cache thrashing on logical siblings. |
| `OMP_NUM_THREADS` | OpenMP thread limit. Must align with `OV_THREADS` to prevent the underlying math library from spawning excess threads and causing CPU contention. |
| `MKL_NUM_THREADS` | Intel Math Kernel Library thread limit. Must align with `OV_THREADS` to prevent contention. |
| `OPENBLAS_NUM_THREADS` | OpenBLAS thread limit. Must align with `OV_THREADS` to prevent contention. |

### 2. Workload-Specific Modes
- **Latency Mode (`OV_MODE=latency`)**: Best for low-core-count VMs (e.g., 4 vCPUs). It minimizes inference time for a single frame, which is crucial for real-time responsiveness.
- **Throughput Mode (`OV_MODE=throughput`)**: Best for high-core-count servers where batching multiple frames simultaneously yields higher overall FPS, even if individual frame latency slightly increases.

### 3. Cgroup-Aware Auto-Sizing
If `OV_THREADS` is omitted from the environment, the HPE pipeline will fallback to:
```python
max(1, len(os.sched_getaffinity(0)) - 2)
```
This safely utilizes available CPU resources while leaving a 2-core margin for the OS, Docker daemon, and streaming server (Flask/RTSP), preventing system lockup.

## Summary
Do **not** attempt to revive the python-based `EPICCPUOptimizer`. Future CPU tuning should be done exclusively by modifying the `.env` and `docker-compose.yaml` files of the respective experiment rigs to adjust `cpus` limits and `OV_*` environment variables.
