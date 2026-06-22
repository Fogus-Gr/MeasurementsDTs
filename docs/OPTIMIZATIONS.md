# Optimizations Guide

This document consolidates optimization strategies across the different experiment rigs and HPE pipelines.

*(Note: For CPU and OpenVINO tuning, see the [CPU_TUNING_GUIDE.md](CPU_TUNING_GUIDE.md).)*

---

## 1. HPE Pipeline & GPU Optimizations

Currently, the custom `optimizations/` folder previously developed for CPU auto-tuning has been moved to the `archive/` directory. The following optimization strategies are the most critical paths forward for improving the codebase.

### Eliminate Remaining CPU Round-Trips (GPU-Native Pipeline)
**Target:** 60-80% faster processing on AlphaPose/GPU models
- **Action:** While `alphapose_hpe.py` has successfully adopted `torchvision.transforms.functional` for GPU-native resizing and cropping of video streams, this needs to be extended to image/directory inputs (which still use `.cpu().numpy()` for the YOLO detector) and the OpenVINO inference wrapper.
- **Goal:** Keep the data entirely on the GPU for all input types. The flow should consistently be: `PyNvCodec (GPU) → GPU Tensor Ops → PyTorch Inference (GPU)` across the board.

### Implement GPU Memory Pooling
**Target:** 80-90% reduction in allocation overhead
- **Action:** Implement a thread-safe GPU memory pool. Pre-allocate tensors of fixed sizes (e.g., standard model input dimensions like 256x192) and reuse them for every frame instead of creating new tensors and dropping them to the garbage collector.
- **Goal:** Prevent GPU memory fragmentation and reduce the 1-5ms CUDA allocation overhead per frame.

### Batched Person Cropping
**Target:** 3-5x speedup for crowded scenes
- **Action:** Refactor `alphapose_hpe.py` and the main loop to batch multiple bounding boxes into a single tensor stack. Run crop and resize operations on the entire batch simultaneously.
- **Goal:** Maximize GPU kernel usage and minimize repeated memory allocations.

### Binary or Asynchronous I/O Export
**Target:** 70% reduction in serialization overhead
- **Action:** Offload the accumulation of COCO format CSVs and JSONs to an asynchronous background thread, or switch to a faster binary serialized format instead of string-concatenated JSON buffers.
- **Goal:** Ensure the inference loop never blocks waiting for disk or memory write operations.

---

## 2. AlphaPose HTTP Streaming Optimizations
*Applicable to testing AlphaPose with HTTP video streams.*

### Ensuring Network RX Bytes Match Original Video Size

To make your experiment and proof scientifically sound, and to ensure the received (RX) video bytes are as close as possible to the original file size, follow these guidelines:

1. **Use `-c:v copy` in FFmpeg:** You are already doing this. It ensures the stream is a byte-for-byte copy of the original video data (no re-encoding, no bitrate change).
2. **Stream the Entire Video:** Make sure the streaming server sends the **whole file** from start to finish, without skipping or looping. Avoid interruptions or early termination.
3. **Minimize Frame Drops in AlphaPose:** **Disable frame dropping logic** in your pipeline (comment out or remove any `skip_next` or similar logic in `run_model`). Ensure AlphaPose processes every frame it receives.
4. **Use HTTP or MPEG-TS, Not MJPEG:** HTTP with MPEG-TS and H.264 (`-f mpegts -c:v copy`) is closest to the original MP4 in terms of data. MJPEG or re-encoded streams will be much larger or smaller.
5. **Network Overhead:** Expect a small increase (a few percent) due to HTTP and MPEG-TS protocol headers. This is normal and unavoidable, but the payload (video data) will match the original.
6. **Verify with Checksums (Optional):** You can compare the MD5 or SHA256 of the original file and the received stream (if saved) to prove byte-level identity.
7. **Check RX Bytes:** The RX bytes reported by Docker or your tracer should be **very close to the original file size** (plus a small protocol overhead).

**Example FFmpeg Command:**
```bash
ffmpeg -re -i videos/rangeOfMotion/hd_00_00.mp4 -c:v copy -f mpegts http://<HPE_HOST>:8089/stream.h264
```

**AlphaPose Input:**
```bash
python3 main.py --method alphapose --input http://<HPE_HOST>:8089/stream.h264 --csv --output_dir results/
```

**Summary of RX verification:**
- **Do not re-encode.**
- **Do not drop frames.**
- **Stream the entire file.**
- **Use `-c:v copy` and MPEG-TS.**
- **Expect RX bytes ≈ original file size + small overhead.**

### Code Modifications for AlphaPose Streaming Optimization

#### Stream-Specific Code Modifications (`alphapose_hpe.py`)
Add HTTP stream handling in the `load_model()` method:
```python
# ...existing code...
if self.input_type == "video" and self.input_src.startswith('http'):
    print(f"[INFO] HTTP stream detected at {self.input_src}")
    self.datalen = 10000  # Set default for HTTP stream
    qsize = 128  # Reduce queue size for streaming
# ...existing code...
```

#### Queue and Batch Size Tuning (`alphapose_hpe.py`)
In the `__init__` method, adjust batch sizes for HTTP streams:
```python
# ...existing code...
if kwargs.get('input_src', '').startswith('http'):
    self.detbatch = 1  # Keep detection batch small
    self.posebatch = 8  # Reduce pose batch size for smoother streaming
# ...existing code...
```

#### Add Frame Dropping Logic for Streams (`alphapose_hpe.py`)
In `run_model()`, add adaptive frame dropping:
```python
def run_model(self, padded):
    frame_start = time.time()
    # ...existing code...
    processing_time = time.time() - frame_start
    if processing_time > 0.1 and hasattr(self, 'frame_count'):
        self.skip_next = (self.frame_count % 2 == 0)
        if self.skip_next:
            return []
    # ...existing code...
```

#### Network Transfer Optimization (`direct_stream_server.py`)
Adjust FFmpeg parameters for better streaming:
```python
ffmpeg_cmd = [
    'ffmpeg', '-re', '-i', video_path,
    '-c:v', 'libx264', '-preset', 'ultrafast',
    '-tune', 'zerolatency',  # Reduce latency
    '-g', '15',              # Shorter GOP for faster seeking
    '-bufsize', '5000k',     # Smaller buffer
    '-f', 'mpegts',
    f'http://{host}:{port}/{endpoint}'
]
```

#### Stream Reconnection Logic (`base_hpe.py`)
Add reconnection logic in the main loop:
```python
retry_count = 0
while retry_count < 3:
    try:
        # ...existing video reading code...
        if not ret:
            print(f"Stream connection lost, retrying ({retry_count+1}/3)...")
            retry_count += 1
            time.sleep(1)
            self.cap = cv2.VideoCapture(self.input_src)
            continue
    except Exception as e:
        print(f"Stream error: {e}, retrying...")
        retry_count += 1
        time.sleep(1)
        continue
```

#### Performance Monitoring (`alphapose_hpe.py` or `base_hpe.py`)
Add this to track actual processing performance:
```python
if not hasattr(self, 'fps_tracker'):
    self.fps_tracker = {'times': [], 'frames': 0}

self.fps_tracker['frames'] += 1
self.fps_tracker['times'].append(time.time())

if self.fps_tracker['frames'] % 30 == 0:
    if len(self.fps_tracker['times']) > 1:
        elapsed = self.fps_tracker['times'][-1] - self.fps_tracker['times'][0]
        fps = len(self.fps_tracker['times']) / elapsed
        print(f"Processing rate: {fps:.2f} FPS")
    self.fps_tracker = {'times': [], 'frames': 0}
```
