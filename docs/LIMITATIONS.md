# Architectural Limitations

This document outlines the current structural and architectural limitations of the HPE inference and benchmarking platform. These limitations directly impact pipeline throughput, hardware utilization, and memory efficiency.

> [!CAUTION]
> These limitations represent the primary bottlenecks to real-time, high-FPS inference performance.

## 1. GPU-CPU Memory Transfer Overhead (PCIe Bottleneck)
- **The Issue:** The current pipeline routinely transfers data back and forth between the GPU and CPU. For instance, in OpenVINO models, PyTorch tensors from the hardware decoder (PyNvCodec) are transferred to the CPU (`.cpu().numpy()`) for preprocessing. Additionally, AlphaPose still transfers image/directory inputs to the CPU for the YOLO detector (`orig_img_tensor.cpu().numpy()`), although it has implemented GPU-native preprocessing for video streams.
- **Impact:** PCIe transfer latency dominates processing time where present. It leads to 50-80% performance loss and wastes 20-40 GB/s of memory bandwidth, leaving the GPU idle during CPU-bound operations.

## 2. Lack of Batch Parallelization
- **The Issue:** In multi-person detection scenarios (especially in `alphapose_hpe.py`), each detected person undergoes individual crop, resize, and processing operations sequentially rather than in parallel batches.
- **Impact:** This severely underutilizes GPU compute units. Sequential memory allocation and kernel launches add substantial overhead per detection, limiting the scale of crowd inference.

## 3. Suboptimal CPU Threading
- **The Issue:** OpenCV operations are predominantly single-threaded by default, leading to thread contention between OpenVINO inference operations and OpenCV preprocessing operations.
- **Impact:** Multi-core systems are underutilized (often seeing 15-25% CPU utilization loss). The preprocessing pipeline becomes a significant bottleneck, causing the hardware video decoder to stall while waiting for the CPU.

## 4. CUDA Memory Fragmentation
- **The Issue:** The pipeline lacks a unified GPU memory pooling system. Tensors are allocated and deallocated constantly during the main frame processing loop.
- **Impact:** Frequent CUDA allocations (`malloc`/`free`) add 1-5ms of overhead per frame and cause severe GPU memory fragmentation.

## 5. String-based Data Accumulation and Export
- **The Issue:** Outputting predictions into JSON and CSV uses inefficient string concatenation and Python's standard `json.dumps()` in the processing loop (`utils/evaluator.py`). 
- **Impact:** Serialization becomes an I/O bottleneck that forces the processing pipeline to pause, hurting steady stream frame rates.

## 6. Unnecessary FFmpeg Transcoding in H.264 Streaming Server
- **The Issue:** The `h264-streaming-server` service in the `ffmpeg_hpe/` experiment rig uses a full re-encode pipeline in `direct_stream_server.py` (line 76–94):
  ```
  ffmpeg -re -i <video> -c:v libx264 -vf scale=1280:720 -b:v 8M -g 48 -keyint_min 48 -preset veryfast -tune zerolatency -f flv -
  ```
  This command decodes the source video, re-encodes it with `libx264`, applies a scaling filter, and muxes into FLV — all of which are unnecessary when the source file is already H.264 encoded (as the `rangeOfMotion/*.mp4` and `hd_*.mp4` files are). Additionally, the HTTP response advertises `Content-Type: video/mp2t` (MPEG-TS) while the FFmpeg output format is `-f flv` (Flash Video), creating a format mismatch.
- **Impact:**
  - **CPU waste:** `libx264` encoding is the most CPU-intensive operation in FFmpeg. On a 1-vCPU streamer container, this consumes nearly 100% of available CPU just to re-create data that already exists in the source file.
  - **Altered bitstream:** Re-encoding changes the video bitstream, meaning RX byte measurements no longer reflect what a real IP camera would transmit. This undermines the experiment's goal of measuring realistic network ingestion.
  - **Added latency:** The encode pipeline adds buffering delay on top of the `-re` realtime pacing, which can exacerbate the stream drain timeout issue documented in `docs/live-stream-fixes-proposed.md`.
  - **Format confusion:** The `video/mp2t` content-type vs `-f flv` mismatch can cause OpenCV/FFmpeg client-side probing to misidentify the container format, leading to spurious decoder warnings.
- **Proposed Fix (zero-transcode passthrough):**
  ```
  ffmpeg -re -i <video> -c:v copy -an -f mpegts -
  ```
  With matching HTTP headers: `Content-Type: video/MP2T`, endpoint `/stream.ts`.
  This remuxes the existing H.264 elementary stream into MPEG-TS without any decode/encode cycle. It requires the source video to already be at the desired resolution. If scaling is needed, pre-process the source file once offline rather than re-encoding on every experiment run.
- **Proposed Fix (minimal change to current command):**
  If the source resolution does not match the target (e.g., VGA source needs 720p output), keep re-encoding but fix the format mismatch and reduce CPU waste:
  ```
  ffmpeg -re -i <video> -c:v libx264 -vf scale=1280:720 -preset ultrafast -tune zerolatency -g 48 -f mpegts -
  ```
  Key changes: drop the unnecessary `-b:v 8M` (let CRF quality control handle bitrate instead of forcing CBR), use `-preset ultrafast` instead of `veryfast` (30-40% less CPU), switch to `-f mpegts` to match the advertised content-type, and drop `-keyint_min 48` (redundant when `-g 48` is set).
- **See also:** `docs/live-stream-fixes-proposed.md` §2c for the broader streamer format standardization proposal.

| Approach | Command | When to use |
|---|---|---|
| **Zero-transcode (best)** | `ffmpeg -re -i <video> -c:v copy -an -f mpegts -` | Source video is already at the desired resolution |
| **Minimal-change (fallback)** | `ffmpeg -re -i <video> -c:v libx264 -vf scale=1280:720 -preset ultrafast -tune zerolatency -g 48 -f mpegts -` | Source needs rescaling (e.g., VGA→720p) |

## 7. Code Duplication in Input Handling
- **The Issue:** The FFmpeg video capture initialization and HTTP stream property detection logic is identically duplicated across multiple files (`movenet_hpe.py` and `openvino_base_hpe.py`).
- **Impact:** This creates technical debt and makes maintaining the stream-reading code (such as adjusting `OPENCV_FFMPEG_CAPTURE_OPTIONS`) harder, as changes must be synced across multiple files.

## 8. Coordinate Space Mismatch Risks
- **The Issue:** The OpenVINO model API natively returns predicted coordinates in the exact image space of the frame passed to its `preprocess()` method.
- **Impact:** If `BaseHPE` applies padding/resizing before calling the model API, and then attempts to scale the resulting keypoints *again* during postprocessing, the coordinates will be mathematically corrupted (resulting in giant bounding boxes or out-of-bounds keypoints). Developers must be extremely careful to track which coordinate space the raw predictions belong to before applying scaling.

## 9. Monitoring Context Fragmentation
- **The Issue:** The legacy `monitor_pid.sh` captures network metrics via process-context tracepoints (`sys_enter_sendto`), while ingress video traffic operates in kernel softirq context.
- **Impact:** The resulting `pid_metrics.csv` file intentionally records zeros (`0,0`) for network TX and RX columns. Developers attempting to read network metrics from `pid_metrics.csv` will find it empty. All network TX data is instead written to `network_stats.csv`, and RX data to `bcc-tracer` logs. This fragmentation causes analytical confusion.
