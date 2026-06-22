# Known Issues and Bugs

This document details the status of known issues, bugs, and TODOs documented in the repository (specifically in `README.md` and `AGENTS.md`) compared against the current state of the codebase.

> [!WARNING]
> Most of the historically documented issues remain unresolved in the code.

## 🔴 Unresolved Issues


### 2. Headless Plotting Block
**Location:** `monitor_hpe/plot_graph.py` (Line 46)
- The script continues to call `plt.show()`, which blocks indefinitely in headless containers, preventing automated graphing pipelines from completing.


### 4. MoveNet Keypoint-Level Score Filtering
**Location:** `movenet_hpe.py` (Line 96)
- Keypoint-level score filtering is not yet applied to the overall body score. The `# TODO - use seperate keypoint scores` comment is still present and unresolved.

### 5. AlphaPose Bounding Box and Parallelism
**Location:** `alphapose_hpe.py` (Line 306) and `original.py` (Line 123)
- The bounding box is derived from the keypoints rather than the YOLO detector's output.
- Batch parallelism for directory inputs is still not implemented.

### 6. Results Accumulator Never Reset
**Location:** `utils/evaluator.py` (Line 77)
- The global accumulator is never reset between runs. The function `reset_results()` exists but is never invoked.
- *Note:* The documentation refers to this file as `export_pose_results.py`, but it has been renamed in the repository to `evaluator.py`.

### 7. Keypoint Coloring Verification
**Location:** `utils/visualizer.py` (Line 26)
- The keypoint coloring logic is only verified as correct for MoveNet. It may color incorrectly for other models.

### 8. Network RX Bytes Architectural Limitation
**Location:** `monitor_hpe/monitor_pid.sh` and `ffmpeg_hpe/monitor_pid.sh`
- **Note:** The `netif_receive_skb` bpftrace PID filter firing in `softirq` context and reporting ~0 RX bytes is a **permanent OS limitation**, not a bug to be fixed. The Linux kernel processes incoming packets before they are associated with a PID. 
- **Action:** Do not attempt to fix this script. For accurate RX measurements, rely exclusively on `bcc_rx_bytes.py` (which filters by IP/port instead of PID).


### 9. Code Duplication in Input Handling
**Location:** `movenet_hpe.py` and `openvino_base_hpe.py`
- The HTTP stream support and FFmpeg video capture initialization logic (`_init_opencv_video_capture()`) is identically duplicated across both backends instead of residing in the shared `BaseHPE`.

## 🟢 Resolved or Invalidated Issues

### 1. `openvino_base_hpe.py` `results` Variable 
**Status:** Resolved/Invalid
- Previous docs mentioned that the `results` variable in `run_model()` may be unbound if `raw_result` is falsy. This is no longer the case. The code correctly initializes `results = None` before the conditional block, making it safe.

### 2. Network RX Measurement 
**Status:** Resolved (Alternative Mechanism Adopted)
- The legacy `monitor_pid.sh` script fails to measure RX traffic due to the `netif_receive_skb` bpftrace PID filter firing in the `softirq` context. 
- **Resolution:** This was resolved by adopting `bcc_rx_bytes.py` within the `ffmpeg_hpe/bpftrace-tracer/` container, which uses a socket filter specifically tied to the streamer IP and ports rather than relying on PID context.

### 3. Benchmarking Platform Infrastructure Bugs
**Status:** Resolved
The following infrastructure bugs from the benchmarking platform have been successfully fixed and verified in the `perf-tuning-base` branch:
- **`bcc_rx_bytes.py`:** IP/port BPF filter was disabled for debugging, counting all TCP traffic. Fixed.
- **`plot_rx_bytes*.py`:** Hardcoded absolute paths broke the script on new machines. Fixed to accept CSV path as CLI arg.
- **`plot_smi_output.py`:** Column names (`utilization.gpu` / `temperature.gpu`) didn't match `run_nvidia_dcgm.sh` output. Fixed.
- **`docker-compose.yaml`:** Build context was hardcoded to a specific user's directory. Fixed to `..`.
- **`run_experiment.sh` service reference:** Referenced `trace_container` instead of `bcc-tracer`. Fixed.
- **`monitor_pid.sh` double write:** `write_net_stats()` wrote entries twice. Fixed.
- **`entrypoint.sh` cleanup:** GPU metrics cleanup was unreachable after `exec`. Fixed by moving to an EXIT trap.
- **CPU% measurement:** `ps -o %cpu` reported lifetime average. Fixed by replacing with `/proc/$PID/stat` delta at 500ms cadence.
- **Output filenames in `run_experiment.sh`:** Fixed incorrect filenames for `perf_monitor` and BCC tracer output.
- **HPE output copy:** Keypoint CSV/JSON outputs were not being copied to the results directory. Fixed.
- **Headless Plotting:** A headless-safe CPU/memory plot helper was implemented for `perf_metrics.csv` and `pid_metrics.csv`.
- **Host-PID conflict:** Host-PID monitor consumed a container-namespace PID, yielding bad CPU metrics. Fixed by writing the host PID directly from `docker inspect`.

### 4. OpenPose and HigherHRNet Coordinate Projection
**Status:** Resolved
- OpenPose and HigherHRNet drew out-of-bounds keypoints because their decoded poses were being doubly-scaled (once by the OpenVINO API and again by the repository-level scaling).
- **Resolution:** Fixed by passing the original frame to the OpenVINO model API and preventing repository-level rescaling for these models (`66bee06` and `a82c8af`).

### 5. Duplicate Model Loading
**Status:** Resolved
- `main.py` eagerly called `hpe.load_model()`, while the main loops for MoveNet and AlphaPose executed an independent guard, causing them to load twice.
- **Resolution:** Removed the eager load call from `main.py`, deferring to the exact once-loading loop guard (`85592ab`).
