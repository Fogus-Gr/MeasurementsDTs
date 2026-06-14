# FFmpeg HPE Experiment Rig Architecture

This document details the architecture, configuration flow, and resource management of the `ffmpeg_hpe` experiment rig.

---

## 1. Pipeline Evolution

The current `run_experiment.sh` is a unified orchestration script that replaced the legacy BCC-specific scripts to provide a more robust and automated benchmarking environment.

| Feature | Legacy (`run_experiment_bcc.sh`) | Modern (`run_experiment.sh`) |
| :--- | :--- | :--- |
| **Pipeline** | HTTP (port 8089) | RTSP / MediaMTX (port 8554) |
| **BCC Tracing** | Manual/Separate | Natively Integrated |
| **Resource Allocation** | Static (Hardcoded) | Dynamic (`nproc` based) |
| **GPU/CPU Support** | Mixed/Manual | Auto-detected Runtime Selection |
| **Reliability** | Primitive | Smart Readiness Probes (ffprobe/API) |

### Key Modern Improvements
*   **Unified BCC Tracing:** Automatically collects `hpe_video_rx.csv` and `hpe_video_tx.csv`.
*   **MediaMTX Integration:** Uses a robust RTSP broker instead of basic HTTP streaming.
*   **Dynamic Scaling:** Automatically reserves 2 vCPUs for telemetry and allocates the remainder to inference.
*   **Diagnostic Capture:** Includes `capture_diagnostics()` to dump logs and network state on failure.

---

## 2. Configuration Hierarchy & Flow

The `.env` file acts as the source of default "static" truth, but it exists in a delicate hierarchy with `run_experiment.sh` and `docker-compose.yaml`.

### 2.1 The Precedence Rule
In this rig, **`run_experiment.sh` is the king of environment variables.** 

Even though Docker Compose automatically loads `.env` by default, the script explicitly exports several of the same variables (like `HPE_METHOD`, `HPE_DEVICE`, `NVIDIA_VISIBLE_DEVICES`, and `OV_THREADS`).

**Result:** Any logic inside `run_experiment.sh` or any variable you export in your shell before running the script will override the values in the `.env` file.

### 2.2 The Configuration Flow (Sequence)
The interaction follows this specific sequence to ensure dynamic system state always overrides static defaults:

1.  **Static Defaults (`.env`)**: Defines the "base" configuration (e.g., `VIDEO_FILE_NAME=vga_01_01.mp4`, `HPE_METHOD=alphapose`).
2.  **Script Logic (`run_experiment.sh`)**:
    *   **Argument Parsing**: It reads the command-line argument (e.g., `./run_experiment.sh movenet`).
    *   **Overwrites**: It overwrites the `.env` default for `HPE_METHOD` with the provided argument.
    *   **Smart Detection**: It performs hardware detection to decide if `HPE_DEVICE` should be `CPU` or `GPU`, potentially ignoring the `.env` value to prevent errors on CPU-only hosts.
    *   **Dynamic Calculation**: It calculates resources that aren't present in `.env`, such as `HPE_CPU_LIMIT` and `OV_THREADS`.
3.  **Substitution (`docker-compose.yaml`)**:
    *   The compose file uses the `${VARIABLE:-default}` syntax.
    *   It takes the variables exported by the script (or the shell) and injects them into the containers.
    *   **Fallback**: If a variable wasn't exported by the script and isn't in `.env`, it falls back to the hardcoded default in the `.yaml` (e.g., `${HPE_MEMORY_LIMIT:-4G}`).

### 2.3 Synergy Table

| Variable | Source in `.env` | Logic in `run_experiment.sh` | Final Impact |
| :--- | :--- | :--- | :--- |
| `VIDEO_FILE_NAME` | `vga_01_01.mp4` | Validated for existence on host. | Passed to streamer service. |
| `HPE_METHOD` | `alphapose` | Overwritten by CLI argument. | Passed to `--method` in main.py. |
| `HPE_DEVICE` | `GPU` | Forced to `CPU` for lightweight models. | Passed to `--device` in main.py. |
| `OV_THREADS` | *Not present* | Calculated as `$(nproc) - 2`. | Configures OpenVINO Runtime. |

---

## 3. Dynamic Resource Allocation Strategy

The rig ensures that telemetry (`bcc-tracer`, `perf_monitor`) does not contaminate inference measurements by strictly isolating CPU resources.

### 3.1 vCPU Allocation Math
```bash
TOTAL_VCPUS = $(nproc)
SIDECAR_RESERVATION = 2
HPE_VCPUS = TOTAL_VCPUS - SIDECAR_RESERVATION (Min: 2)
```

### 3.2 Per-Method Resource Tuning

| Method Category | OV_THREADS | CPU Limit | Memory Limit |
| :--- | :--- | :--- | :--- |
| **GPU (alphapose, openpose)** | Capped at 4 | `HPE_VCPUS` | 8 GB |
| **Lightweight (movenet, ae1-3)**| `HPE_VCPUS` | `HPE_VCPUS` | 1 GB per vCPU (Min 4G) |
| **Heavy (hrnet)** | `HPE_VCPUS` | `HPE_VCPUS` | 1.5 GB per vCPU (Min 6G) |

---

## 4. OpenVINO Threading Implementation

The `OV_THREADS` variable set by the script is consumed through a multi-step Python chain to ensure the inference engine is perfectly tuned.

### 4.1 The Implementation Chain
1.  **`run_experiment.sh`**: Detects hardware and exports `OV_THREADS`.
2.  **`docker-compose.yaml`**: Injects the variable into the `hpe` container.
3.  **`openvino_base_hpe.py`**: 
    *   Reads `os.getenv("OV_THREADS")`.
    *   Maps it to `openvino.properties.inference_num_threads`.
    *   Explicitly cleans up legacy keys (`CPU_THREADS_NUM`, etc.) to prevent conflicts.
4.  **`openvino_adapter.py`**:
    *   Loads the model using the configured Core.
    *   Queries `CPU_THREADS_NUM` from the compiled model.
    *   Logs the **effective** thread count to stdout for verification.

### 4.2 Log Verification
Check the startup logs for the following block to verify the configuration is active:
```text
[OpenVINO Configuration]
  Requested settings: threads=6, mode=latency, streams=None
  Effective settings:
    CPU threads: 6
    CPU pinning: True
```

---

## 5. Deep Dive: Threading Code Implementation

`openvino_base_hpe.py` contains the logic that explicitly consumes the `OV_THREADS` environment variable and maps it to the OpenVINO Runtime configuration.

### 5.1 Environment Variable Extraction
In `openvino_base_hpe.py`, the `__init__` method captures the environment variables exported by `run_experiment.sh`:

```python
# openvino_base_hpe.py (lines 80-88)
env_threads = os.getenv("OV_THREADS")
env_mode = os.getenv("OV_MODE")
env_streams = os.getenv("OV_STREAMS")
env_cpu_pinning = os.getenv("OV_CPU_PINNING")
env_hyper_threading = os.getenv("OV_HYPER_THREADING")

self.ov_threads = int(ov_threads if ov_threads is not None else (env_threads or 1))
self.ov_mode = (ov_mode or env_mode or "latency").lower()
```

### 5.2 OpenVINO Property Configuration
The `_configure_core` method translates `OV_THREADS` into the engine's internal `inference_num_threads` property:

```python
# openvino_base_hpe.py (lines 142-147)
cpu_props = {
    props.hint.performance_mode: perf,
    props.inference_num_threads: int(self.ov_threads),  # <--- HERE
    props.hint.enable_cpu_pinning: self.ov_cpu_pinning,
    props.hint.enable_hyper_threading: self.ov_hyper_threading,
}
core.set_property("CPU", cpu_props)
```

### 5.3 The Role of `openvino_adapter.py`
The `OpenvinoAdapter` in `models/OpenVINO/model_api/adapters/openvino_adapter.py` acts as a **validator and reporter**.
*   **Verification:** After the model is loaded, it calls `log_runtime_settings()` (line 80), which queries the engine for the *actual* threads being used:
    ```python
    if device == 'CPU':
        nthreads = self.compiled_model.get_property('CPU_THREADS_NUM')
        log.info('\t\tNumber of threads: {}'.format(nthreads if int(nthreads) else 'AUTO'))
    ```

### 5.4 Summary of the "Chain"
1.  **`run_experiment.sh`**: Detects hardware and sets `export OV_THREADS=X`.
2.  **`docker-compose.yaml`**: Passes `OV_THREADS` into the container environment.
3.  **`openvino_base_hpe.py`**: Reads the environment and configures the OpenVINO Core.
4.  **`openvino_adapter.py`**: Loads the model and prints confirmation.

---

## 6. Directory Structure Reference

*   **`ffmpeg_hpe/.env`**: Base configuration file.
*   **`ffmpeg_hpe/run_experiment.sh`**: Primary entry point and orchestrator.
*   **`ffmpeg_hpe/docker-compose.yaml`**: Container definition and variable substitution.
*   **`openvino_base_hpe.py`**: High-level OpenVINO configuration logic.
*   **`models/OpenVINO/model_api/adapters/openvino_adapter.py`**: Low-level OpenVINO Runtime interface.
