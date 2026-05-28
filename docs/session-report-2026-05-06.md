# Benchmarking Platform Audit & Fix Report — 6 May 2026

Branch: `perf-tuning-base`  
All commits pushed to: `https://github.com/Fogus-Gr/MeasurementsDTs`

---

## 1. Branch & Codebase Audit

### Branch History Recovered

After VM loss, established that active work was on `cuda-dev` around **July 2025**, then `perf-tuning-base` from **September 2025** onward. Last confirmed working commit before VM loss:

```
7f0a1cc  Enhance video capture handling and OpenVINO configuration  (Sep 18 2025)
```

### Branch Comparison — `cuda-dev` vs `perf-tuning-base`

`perf-tuning-base` is a stripped-down production rewrite of `cuda-dev`.

| Aspect | `cuda-dev` | `perf-tuning-base` |
|---|---|---|
| HTTP stream handling | Full custom MJPEG byte-reader, frame-skip, metadata extraction, timeout | Removed — falls through to standard OpenCV path |
| Logging | Dual logging (file + structured JSONL) | None |
| CLI args | `--timeout`, `--max-frames` | Removed |
| `PoseMonitor` | Present | Removed |
| `video_detection.py` | Present | Removed |
| Dockerfiles | Single-stage | Two new multi-stage builds |
| COCO output field | `frame_number` | `image_id` |
| OpenVINO knobs | Env-var driven | Hardcoded (`threads=3`, `mode=throughput`) |

### All Branches Ranked by Last Commit (Sept 2025)

| # | Branch | Last Commit | Latest Message |
|---|---|---|---|
| 1 | `cuda-dev` | 2025-09-17 | Update docker-compose.yaml with improved GPU and environment configuration |
| 2 | `pyav-integration` | 2025-09-17 | Add PyAV integration enhancements |
| 3 | `latest-alphapose-integration` | 2025-09-17 | Add latest_alphapose integration with AlphaPose HPE setup |
| 4 | `refactor/video-detection-consolidation` | 2025-09-16 | Update timeout calculation in main.py for improved accuracy |
| 5 | `hpe-benchmark` | 2025-09-15 | Add hpe-benchmark Docker Compose setup |
| 6 | `feat/ov-epyc-4vcpu` | 2025-08-30 | Refactor video capture, enhance logging, and update OpenVINO configuration |
| 7 | `feat/openvino-opti-cpu` | 2025-08-28 | feat: Configure OpenVINO CPU performance and improve higherhrnet support |

---

### Reconstructed Timeline (Jun 2025 – May 2026)

Based on shell history (`full_shell_history.txt`), experiment result directory timestamps, and git log:

#### ~June 2025 — Initial Setup & CPU Profiling

Earliest timestamped artifacts are from `monitor_hpe/`:
- **Jun 19**: `results_perf_AMD_EPYC_7551P_..._20250619_143126` — first `perf` profiling on AMD EPYC
- **Jun 23**: 7 result directories (`_20250623_*`) — heavy CPU benchmarking day, multiple experiments with `perf` monitoring

Activities: exploring AMD EPYC 7551P (32-core) with `cpuid`, `lscpu`, `cpupower`, `lsmem`, `lshw` (history lines 114-124). Saved system info, installed `btop`/`htop` for monitoring.

#### ~July 11-15, 2025 — Dockerized HPE Experiments with ffmpeg_hpe

Busiest experiment period — 13 result directories:
- **Jul 14**: movenet GPU (`130340`), alphapose GPU (`132547`), openpose CPU (`211145`)
- **Jul 15**: alphapose/movenet/openpose CPU runs across VGA and HD resolutions, with and without MISO videos

Atuin briefly active on **Jul 11** (4 timestamped entries: `atuin sync`, `nvim ~/.bashrc`, `source ~/.bashrc`, `exit`), then disabled.

#### ~August 2025 — OpenVINO CPU Tuning & VPS Deployment

Git commits show:
- **Aug 28**: OpenVINO CPU tuning for 4-vCPU VPS (threads/hints/pinning) + WARP.md
- **Aug 29-31**: gitignore cleanup, AlphaPose CPU fixes for Apple M1

Shell history shows heavy `export OV_*` experimentation (lines 208-224): toggling `OV_MODE=latency/throughput`, `OV_STREAMS`, `OV_THREADS`, running MoveNet on CPU with different configs.

#### ~September 2025 — HTTP Streaming, Async Processing, More Models

- **Sep 11-12**: Added AlphaPose notebook, HTTP stream input support, async/threaded OpenVINO HPE, infrastructure + GitHub workflows
- **Sep 14-15**: Enhanced `run_async_openvino_hpe`, timeout/frame-count detection for HTTP streams, OpenVINO simple test script
- **Sep 17-18**: CUDA upgrade scripts, video capture handling, CPU performance optimization, Dockerfile for OpenCV+FFmpeg+CUDA

Shell history shows the `ae1` (EfficientHRNet) method being tested extensively (lines 602-632), plus `openpose` and `alphapose` on both CPU and GPU with `--max_frames` and `--timeout` flags.

#### ~Late 2025 — FFmpeg + CUDA Docker Build Saga

Massive effort building `ffmpeg-cuda:8.0-focal` (history lines 298-569):
- Multiple `Dockerfile_optimized_multistage_v4` build attempts
- Disk space issues (`df -h`, `docker system prune`, `docker builder prune`)
- Fighting with `libnpp`, `h264_nvenc`, `scale_npp` filters
- Cleaning old FFmpeg builds from `/usr/local/` (lines 314-340)
- Testing NVENC encoding with various quality presets (lines 553-569)

#### ~Early 2026 — NVIDIA Driver Upgrade & Kernel HWE

Painful driver upgrade (history lines 496-553):
- Installing `linux-generic-hwe-20.04` (kernel 5.15)
- Fighting `apt` broken packages, GRUB EFI issues, `dpkg --configure -a`
- Switching apt mirrors to fix download issues
- Installing `nvidia-driver-570` from `graphics-drivers/ppa`
- Multiple reboots, fixing CUDA repo pin conflicts
- Finally getting `nvidia-smi` and Docker GPU passthrough working

#### ~Early-Mid 2026 — Performance Governor & Network Monitoring

- Setting CPU to `performance` governor (history lines 575-638)
- Installing `hwloc`, `nethogs`, `iftop` for network monitoring
- Testing `lo` interface traffic (investigating RX/TX discrepancy for streaming)
- Pulling `madtune/opencv-cuda:4.10.0` Docker image

#### ~Mid 2026 — Final Optimization Round

- Extensive OpenVINO env var tuning (history lines 667-741)
- Running `alphapose` on GPU, `openpose` and `movenet` on CPU
- Network traffic analysis with `nethogs` and `iftop`
- Cleaning up old model files (`rm -rf models/ONNX/`)

#### May 7, 2026 — Server Rebooted, Atuin Reactivated

- Server came back up, `source ~/.bashrc`, atuin lines uncommented
- `git status`, `cat ~/.bashrc`

#### Summary Table

| Period | Main Activity |
|---|---|
| **Jun 2025** | Server setup, CPU profiling with `perf` on AMD EPYC |
| **Jul 2025** | Dockerized HPE experiments (movenet/alphapose/openpose, CPU+GPU) |
| **Aug 2025** | OpenVINO CPU tuning, VPS deployment, gitignore cleanup |
| **Sep 2025** | HTTP streaming support, async HPE, ae1 model, git commits |
| **Late 2025** | FFmpeg+CUDA Docker build, NVENC testing, disk space battles |
| **Early 2026** | NVIDIA driver 570 upgrade, kernel HWE, GRUB/EFI fixes |
| **Mid 2026** | CPU governor tuning, network monitoring, final optimization pass |
| **May 2026** | Server restart, atuin reactivated |

> **Note on git activity:** The last *branch-level* commit visible in git log before this session's fixes was Sep 18, 2025 (`7f0a1cc`). However, the shell history shows continuous infrastructure and optimization work (Docker builds, driver upgrades, env-var tuning) through mid-2026 that was never committed — likely because it was iterative experimentation rather than code changes. Commits by Vittorakis (`cacfe8a`, `8558aef`) and George Kal (`086c53a`) on `origin/perf-tuning-base` appeared later during the collaborative push phase.

---

## 2. Full Bug Audit — 21 Issues Found

All 8 non-main branches carried identical bugs. `main` and `evaluation` were unaffected (no benchmarking code present).

### Benchmarking Platform Issues

| # | File | Issue | Status |
|---|---|---|---|
| 1 | `ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py` | IP/port BPF filter disabled — counted all TCP traffic instead of video stream only | ✅ Fixed `256a21c` |
| 2 | `ffmpeg_hpe/plot_rx_bytes*.py` | Hardcoded absolute path to old VM — unusable on any other machine | ✅ Fixed `3e09d55` |
| 3 | `ffmpeg_hpe/plot_smi_output.py` | Column names didn't match `run_nvidia_dcgm.sh` output — crashed on every run | ✅ Fixed `3e09d55` |
| 4 | `ffmpeg_hpe/docker-compose.yaml` | Build context hardcoded to `/home/user/MeasurementsDTs` | ✅ Fixed `3e09d55` |
| 5 | `ffmpeg_hpe/run_experiment.sh` | Referenced `trace_container` (commented out) instead of `bcc-tracer` | ✅ Fixed `3e09d55` |
| 6 | `monitor_hpe/monitor_pid.sh` | `write_net_stats()` wrote each entry twice | ✅ Fixed `3e09d55` |
| 7 | `ffmpeg_hpe/entrypoint.sh` | GPU metrics cleanup after `exec` was unreachable | ✅ Fixed `3e09d55` |
| 8 | Both `monitor_pid.sh` files | `ps -o %cpu` reports lifetime average, not per-interval CPU% | ✅ Fixed `b6a9fd2` |
| 9 | `ffmpeg_hpe/run_experiment.sh` | `perf_monitor` output filename wrong (`aggregated_metrics.csv`) | ✅ Fixed `3c006cf` |
| 10 | `ffmpeg_hpe/run_experiment.sh` | BCC tracer output filename wrong (`trace.csv` → `hpe_video_rx.csv`) | ✅ Fixed `3c006cf` |
| 11 | `ffmpeg_hpe/run_experiment.sh` | HPE container output (keypoint CSVs/JSON) never copied to results dir | ✅ Fixed `3c006cf` |
| 12 | `ffmpeg_hpe/run_experiment.sh` | Startup timer captured after `docker compose up` — always ~0ms | ✅ Fixed `5f469ff` |
| 13 | `ffmpeg_hpe/run_experiment.sh` | `HPE_METHOD` empty when no arg — crashes `main.py` | ✅ Fixed `5f469ff` |
| 14 | `ffmpeg_hpe/run_experiment.sh` | PID file contained full `ps -ef` table — `monitor_pid.sh` failed to parse | ✅ Fixed `5f469ff` |
| 15 | `ffmpeg_hpe/run_experiment.sh` | No HPE exit code check — crash and clean exit looked identical | ✅ Fixed `5f469ff` |
| 16 | `ffmpeg_hpe/run_experiment.sh` | `HPE_MONITOR_START` set but never read | ✅ Fixed `5f469ff` |
| 17 | `ffmpeg_hpe/docker-compose.yaml` | `perf_monitor` missing `container_name` — Docker generated random name | ✅ Fixed `5f469ff` |
| 18 | `ffmpeg_hpe/docker-compose.yaml` | `VIDEO_FILE` no default — empty string passed to FFmpeg without `.env` | ✅ Fixed `5f469ff` |
| 19 | `ffmpeg_hpe/run_experiment.sh` | `docker exec` on already-exited HPE container — HPE output silently lost | ✅ Fixed `8d72546` |
| 20 | `ffmpeg_hpe/run_experiment.sh` | Results dir named `results_hpe_*` for no-arg runs despite executing movenet | ✅ Fixed `8d72546` |
| 21 | `ffmpeg_hpe/run_experiment_bcc.sh` | 8 accuracy bugs inherited from `run_experiment.sh` — never synced | ✅ Fixed `2908e26` |

### HPE Inference Code TODOs (open)

| File | Issue |
|---|---|
| `movenet_hpe.py` | Keypoint-level score filtering not applied to body score (marked `# TODO`) |
| `alphapose_hpe.py` | Bounding box derived from keypoints, not from YOLO detector output |
| `openvino_base_hpe.py` → `run_model()` | `results` variable may be unbound if `raw_result` is falsy |
| `export_pose_results.py` | Global accumulator never reset between runs — `reset_results()` exists but never called |
| `visualizer.py` | Keypoint colouring only verified correct for MoveNet (marked `# TODO`) |

---

## 3. All Fixes Applied — Commit by Commit

### `256a21c` — Re-enable IP/port filter in BCC RX tracer

**File:** `ffmpeg_hpe/bpftrace-tracer/bcc_rx_bytes.py`

The BPF IP/port filter was commented out for debugging and never restored. Without it, `bcc_rx_bytes.py` counted all TCP traffic on `eth0` — DNS, healthchecks, Docker overlay — not just video stream packets. Also removed `bpf_trace_printk("BPF called")` which fired on every packet through the interface.

**Impact on accuracy:** RX measurements were completely unreliable before this fix. The `entrypoint.sh` port auto-detection (10-retry loop via `ss -ntp`) was working correctly but the detected port was being silently ignored.

---

### `3e09d55` — 7 monitoring and plotting bugs

| Fix | File | What was wrong | What changed |
|---|---|---|---|
| Plot hardcoded paths | `plot_rx_bytes.py`, `plot_rx_bytes_trimmed_reset.py` | Hardcoded to old VM path | Now accepts CSV path as CLI arg; saves PNG next to input CSV |
| GPU plot column mismatch | `plot_smi_output.py` | Read `utilization.gpu`/`temperature.gpu` — script wrote `gpu_utilization`/`temperature` | Column names corrected |
| Docker build context | `ffmpeg_hpe/docker-compose.yaml` | `/home/user/MeasurementsDTs` | Changed to `..` |
| Wrong service name | `ffmpeg_hpe/run_experiment.sh` | `trace_container` (commented out in compose) | Changed to `bcc-tracer` |
| Double-write bug | `monitor_hpe/monitor_pid.sh` | `write_net_stats()` wrote directly to `NETSTATS_FILE` then again via flock/cat | Removed direct write; flock path only |
| Unreachable cleanup | `ffmpeg_hpe/entrypoint.sh` | `kill $METRICS_PID` after `exec "$@"` — unreachable | Moved to EXIT trap before `exec` |
| CPU% lifetime average | Both `monitor_pid.sh` | `ps -o %cpu` reports cumulative CPU since process start | Replaced with `pidstat 1 1` (later replaced again — see `b6a9fd2`) |

---

### `b6a9fd2` — Replace pidstat with `/proc/stat` delta for 500ms CPU sampling

**Files:** `ffmpeg_hpe/monitor_pid.sh`, `monitor_hpe/monitor_pid.sh`

`pidstat 1 1` blocks for 1 second per loop iteration, destroying the 500ms sampling cadence. Replaced with reading `utime+stime` from `/proc/$PID/stat` before and after each `sleep 0.5`, computing the delta against wall-clock time. Instant, no external tools required, exact 500ms loop period preserved.

**Impact on accuracy:** CPU% now reflects actual activity during each 500ms interval rather than a lifetime average.

---

### `3c006cf` — Fix `run_experiment.sh` result collection

**File:** `ffmpeg_hpe/run_experiment.sh`

| Fix | What was wrong | What changed |
|---|---|---|
| BCC tracer filename | Looked for `trace.csv` | Corrected to `hpe_video_rx.csv` — BCC RX data was never collected |
| perf_monitor filename | Looked for `aggregated_metrics.csv` | Now loops over `perf_metrics.csv`, `pid_metrics.csv`, `network_stats.csv` |
| HPE output never copied | Step 21 only listed files, never copied them | Added `docker cp` of all CSVs and JSON from HPE container |
| `set -e` safety | `docker exec` condition checks aborted script mid-collection | Guarded with `\|\| false` / `\|\| true` |

---

### `5f469ff` — Orchestration bugs and docker-compose gaps

**Files:** `ffmpeg_hpe/run_experiment.sh`, `ffmpeg_hpe/docker-compose.yaml`

| Fix | File | What was wrong | What changed |
|---|---|---|---|
| Startup timer order | `run_experiment.sh` | `hpe_start` captured after `docker compose up` — always ~0ms | Moved before launch |
| `HPE_METHOD` default | `run_experiment.sh` | Empty string when no arg — `main.py` crashed | Defaulted to `movenet` |
| PID file content | `run_experiment.sh` | `ps -ef` wrote full process table — `monitor_pid.sh` failed to parse | Replaced with `pgrep -f "python.*main.py"` |
| HPE exit code | `run_experiment.sh` | No check — crash and clean exit looked identical | Added exit code log to `hpe_exit.log` |
| `HPE_MONITOR_START` | `run_experiment.sh` | Set but never read | Removed |
| `perf_monitor` container_name | `docker-compose.yaml` | Missing — Docker generated random name | Added `container_name: perf_monitor` |
| `VIDEO_FILE` default | `docker-compose.yaml` | No fallback — empty string to FFmpeg without `.env` | Added `:-/app/videos/rangeOfMotion/vga_01_01.mp4` |

---

### `8d72546` — HPE output collection and results dir naming

**File:** `ffmpeg_hpe/run_experiment.sh`

- `docker exec find` on HPE container after it had already exited — always failed silently. The HPE container mounts `./results:/output` so files are already on the host. Replaced with direct `cp ./results/*.csv` and `cp ./results/*.json`.
- `container_type` defaulted to `"hpe"` while `HPE_METHOD` defaulted to `"movenet"` — no-arg runs saved under `results_hpe_*` but actually ran movenet. Both now default to `movenet`.

---

### `2908e26` — Sync `run_experiment_bcc.sh` with all accuracy fixes

**File:** `ffmpeg_hpe/run_experiment_bcc.sh`

`run_experiment_bcc.sh` is the measurement validation script written to investigate the RX/TX discrepancy. It had never received any of the fixes applied to `run_experiment.sh`. All 8 accuracy-critical fixes were ported across while preserving the BCC-specific instrumentation.

| Fix ported | Impact |
|---|---|
| `start_time` never defined | Duration at end of script was a bash arithmetic error |
| `HPE_METHOD`/`container_type` default | Empty string crashed `main.py` on no-arg runs |
| Startup timer before `docker compose up` | Was always ~0ms |
| PID file via `pgrep` | `monitor_pid.sh` received no valid PID — tracked nothing |
| perf_monitor correct filenames | `aggregated_metrics.csv` never existed — perf data was never collected |
| HPE output: CSV + JSON from host path | Only CSVs copied; JSON missing; `docker exec` on exited container |
| HPE exit code check | Failed runs indistinguishable from successful ones |
| Remove `HPE_MONITOR_START` | Dead variable |

**Preserved unchanged:** 8s BCC compilation wait, 10-retry port detection loop, `port_info.txt`, enhanced `capture_diagnostics()` with `ss -tulnp`, results directory naming with core count + device type + video filename.

---

## 4. Key Architecture Clarification — TX vs RX Tool Split

Documented in both `README.md` and `AGENTS.md`.

| Tool | Container | Direction | Mechanism | Reliable? |
|---|---|---|---|---|
| `bpftrace sys_enter_sendto` in `monitor_pid.sh` | `perf_monitor` | **TX** (HPE → outside) | Syscall tracepoint — fires in HPE process context, PID filter valid | ✅ Yes |
| `bcc_rx_bytes.py` | `bcc-tracer` | **RX** (stream → HPE) | BPF socket filter on `eth0`, filtered by streamer IP + port | ✅ Yes (after `256a21c`) |
| `bpftrace netif_receive_skb` in `monitor_pid.sh` | `perf_monitor` | RX (attempted) | Fires in softirq/kernel context — PID never matches HPE | ❌ Always ~0 |

**Rule:** for RX data use `traces/bcc/hpe_video_rx.csv`. For TX data use `network_stats.csv` from `perf_monitor`. Never use the RX column from `network_stats.csv`.

**Why the split is necessary:** `sendto()` is a syscall made by the HPE process — the kernel knows the PID. Incoming packets are processed by the kernel network stack in softirq context before being associated with any process — PID filtering is impossible. `bcc-tracer` works around this by filtering by IP+port instead, running in a container that shares HPE's network namespace (`network_mode: service:hpe`).

---

## 5. Documentation Added

| Commit | File | What was added |
|---|---|---|
| `7493830` | `README.md` | Newcomer orientation, HPE pipeline call-chain diagram, benchmarking platform flow, branch structure table, experiment rigs comparison table, known issues table |
| `f15037b` | `AGENTS.md` | Full known issues table with fix status and commit refs, session history section |
| `bf13168` | `README.md` + `AGENTS.md` | TX/RX tool split explanation — why bpftrace handles TX and bcc-tracer handles RX, which CSVs to trust |

---

## 6. What Remains Open

| # | File | Issue | Notes |
|---|---|---|---|
| — | Both `monitor_pid.sh` | `netif_receive_skb` bpftrace RX always ~0 | By design — use `bcc-tracer` for RX |
| — | `monitor_hpe/plot_graph.py` | Calls `plt.show()` — blocks in headless containers | One-line fix when needed |
| — | `ffmpeg_hpe/plot_graph.py` | Empty file (0 bytes) | Delete or implement |
| — | `rtsp-ipcam/docker-compose.yml` | Volume mount hardcoded to `/home/user/MeasurementsDTs/videos/...` | **Removed** — folder deleted; streaming now handled by `jrottenberg/ffmpeg:4.4-nvidia` + `mediamtx` in `ffmpeg_hpe/docker-compose.yaml` |
| — | `run_experiment_bcc.sh` | `HPE_INPUT` still uses raw IP (not DNS hostname) | Intentional workaround — low risk |
| — | TX/RX zeros in `pid_metrics.csv` | Network columns always `0,0` | By design — network data is in `network_stats.csv` |

---

## 7. Experiment Rigs — Current State

| Folder | Entry point | Ready to run? | Notes |
|---|---|---|---|
| `ffmpeg_hpe/` | `run_experiment.sh` | ✅ Yes | All critical bugs fixed |
| `ffmpeg_hpe/` | `run_experiment_bcc.sh` | ✅ Yes | All accuracy fixes synced; use for RX validation |
| `monitor_hpe/` | `run_experiment.sh` | ✅ Yes | No network metrics (by design) |
| `recent-dash/` | `run_experiment.sh` | ⚠️ Partial | Separate research thread; not HPE-focused |
