# Live-Stream Robustness - Proposed Code Changes

**Date:** 2026-06-19
**Branch:** perf-tuning-base
**Status:** Draft - reviewed, pending implementation

## Background

OpenPose CPU cannot sustain the live 25 FPS H.264 stream. The failure is not
primarily that the streamer lacks CPU: when inference is slower than the source,
the HPE side stops draining the stream fast enough, OpenCV/FFmpeg eventually
times out, and the decoder reports corrupt packets / invalid NAL units.

For this paper rig, we should not slow the simulated live camera just to make
slow models process every frame. That would change the experiment semantics.
The correct fix is to keep the source live, decouple capture from inference,
drop stale frames deliberately, and report exactly how many frames were observed,
processed, and dropped.

The streamer still needs robustness fixes: it should handle health checks while
a long-lived stream is active, and its advertised stream format should match the
bytes FFmpeg actually writes.

---

## Review Decisions

I agree with the architecture, but not with the earlier draft verbatim. These
constraints must be part of the implementation:

1. **Live-stream mode uses a latest-frame queue.**
   The capture thread continuously drains OpenCV/FFmpeg into a bounded queue
   with `maxsize=1`. If inference is slow, the oldest unprocessed frame is
   dropped and the newest frame is kept.

2. **Do not require 8 vCPUs and do not slow the streamer.**
   More CPU can help, but it does not solve the semantic problem. A live camera
   keeps producing frames regardless of model speed.

3. **Preserve source-frame identity.**
   If frames are dropped, output frame numbers cannot silently pretend that
   processed frame 100 is source frame 100. Either JSON/CSV uses the source
   frame number, or a mapping CSV records processed index to source frame.

4. **Keep drop accounting paper-grade.**
   A run may be valid even when `processed_frames < source_frames_observed`, but
   every missing frame must be accounted for as a deliberate live-stream drop.
   Decoder collapse, packet corruption, and unexplained read failures are still
   validation failures.

5. **Use the correct video path inside each container.**
   The streamer sees videos under `/app/videos/...`. The HPE container sees the
   same host volume under `/videos/...`. Do not pass `/app/videos/...` as
   `VIDEO_PATH` to HPE.

6. **Standardize stream format.**
   The current server advertises `/stream.h264` and `video/mp2t` but emits
   `-f flv`. The fix should use one consistent contract, preferably MPEG-TS:
   endpoint `/stream.ts`, content type `video/MP2T`, FFmpeg `-f mpegts`.

---

## Fix 1: Threaded Capture And Drop Metrics

**File:** `base_hpe.py`

### 1a. Add imports

Add near the existing imports:

```python
import csv
import queue
import threading
```

### 1b. Add `LiveStreamMetrics`

Add after the `Padding` namedtuple:

```python
class LiveStreamMetrics:
    def __init__(self):
        self.source_frames_observed = 0
        self.processed_frames = 0
        self.dropped_frames = 0
        self.read_failures = 0
        self.capture_start_time = None
        self.capture_end_time = None
        self.last_frame_capture_time = None
        self.exit_reason = "unknown"
        self.pending_frames_dropped_at_stop = 0
        self.frame_map = []

    def record_processed(self, processed_index, source_frame_number, capture_ts, process_ts):
        self.processed_frames += 1
        self.frame_map.append({
            "processed_index": processed_index,
            "source_frame_number": source_frame_number,
            "capture_timestamp": capture_ts,
            "process_timestamp": process_ts,
        })

    def save_summary_csv(self, filepath):
        elapsed = 0
        if self.capture_start_time and self.capture_end_time:
            elapsed = self.capture_end_time - self.capture_start_time

        source_fps = self.source_frames_observed / elapsed if elapsed > 0 else 0
        processed_fps = self.processed_frames / elapsed if elapsed > 0 else 0
        drop_rate = self.dropped_frames / max(self.source_frames_observed, 1) * 100
        accounted = self.processed_frames + self.dropped_frames

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            writer.writerow(["source_frames_observed", self.source_frames_observed])
            writer.writerow(["processed_frames", self.processed_frames])
            writer.writerow(["dropped_frames", self.dropped_frames])
            writer.writerow(["pending_frames_dropped_at_stop", self.pending_frames_dropped_at_stop])
            writer.writerow(["accounted_frames", accounted])
            writer.writerow(["read_failures", self.read_failures])
            writer.writerow(["exit_reason", self.exit_reason])
            writer.writerow(["elapsed_seconds", round(elapsed, 3)])
            writer.writerow(["source_fps", round(source_fps, 2)])
            writer.writerow(["processed_fps", round(processed_fps, 2)])
            writer.writerow(["drop_rate_percent", round(drop_rate, 2)])

    def save_frame_map_csv(self, filepath):
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "processed_index",
                "source_frame_number",
                "capture_timestamp",
                "process_timestamp",
            ])
            writer.writeheader()
            writer.writerows(self.frame_map)
```

### 1c. Add a live capture loop

Add as a `BaseHPE` method after `_init_opencv_video_capture`:

```python
def _live_capture_loop(self, cap, frame_queue, stop_event, metrics):
    """Continuously drain a live stream and keep only the newest frame."""
    metrics.capture_start_time = time.time()
    consecutive_failures = 0
    max_consecutive_failures = 10

    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            metrics.read_failures += 1
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                metrics.exit_reason = "read_failures"
                break
            time.sleep(0.01)
            continue

        consecutive_failures = 0
        source_frame_number = metrics.source_frames_observed
        metrics.source_frames_observed += 1
        capture_ts = time.time()
        metrics.last_frame_capture_time = capture_ts

        if frame_queue.full():
            try:
                frame_queue.get_nowait()
                metrics.dropped_frames += 1
            except queue.Empty:
                pass

        try:
            frame_queue.put_nowait((frame, source_frame_number, capture_ts))
        except queue.Full:
            metrics.dropped_frames += 1

    if metrics.exit_reason == "unknown":
        metrics.exit_reason = "source_ended"
    metrics.capture_end_time = time.time()
    stop_event.set()
```

### 1d. Replace only the HTTP/RTSP OpenCV path

Inside `main_loop_with_timeout`, keep the existing file-video and webcam path.
Only use the threaded/drop mode when the input source is live:

```python
is_live_stream = (
    isinstance(self.input_src, str)
    and self.input_src.startswith(("http://", "https://", "rtsp://"))
)
```

For live streams:

```python
print("[INFO] Live-stream mode: threaded capture with latest-frame queue")
metrics = LiveStreamMetrics()
frame_queue = queue.Queue(maxsize=1)
stop_event = threading.Event()
processed_index = 0

capture_thread = threading.Thread(
    target=self._live_capture_loop,
    args=(self.cap, frame_queue, stop_event, metrics),
    daemon=True,
)
capture_thread.start()

while True:
    if timeout_seconds > 0 and time.time() - start_time > timeout_seconds:
        metrics.exit_reason = "timeout"
        break
    if max_frames > 0 and processed_index >= max_frames:
        metrics.exit_reason = "max_frames"
        break
    if stop_event.is_set() and frame_queue.empty():
        break

    try:
        frame, source_frame_number, capture_ts = frame_queue.get(timeout=5.0)
    except queue.Empty:
        if stop_event.is_set():
            break
        continue

    self.process_frame(frame, source_frame_number)
    metrics.record_processed(
        processed_index,
        source_frame_number,
        capture_ts,
        time.time(),
    )
    processed_index += 1

    if processed_index % 100 == 0:
        elapsed = time.time() - start_time
        fps = processed_index / elapsed if elapsed > 0 else 0
        print(
            f"Processed {processed_index} frames in {elapsed:.1f}s "
            f"(avg {fps:.1f} FPS, dropped {metrics.dropped_frames})"
        )

stop_event.set()
capture_thread.join(timeout=5)
metrics.capture_end_time = metrics.capture_end_time or time.time()
while not frame_queue.empty():
    try:
        frame_queue.get_nowait()
        metrics.dropped_frames += 1
        metrics.pending_frames_dropped_at_stop += 1
    except queue.Empty:
        break
metrics.save_summary_csv(os.path.join(
    self.output_dir,
    f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_live_metrics.csv",
))
metrics.save_frame_map_csv(os.path.join(
    self.output_dir,
    f"{self.start_time_of_experiment}_{self.model_type}_{self.input_file}_live_frame_map.csv",
))
frame_number = metrics.processed_frames
```

Important: `process_frame()` should receive `source_frame_number`, not
`processed_index`, so JSON/CSV frame numbers refer to the source timeline. The
frame-map CSV then records which source frames were actually processed.

---

## Fix 2: Streamer Robustness And Format Consistency

**File:** `rtsp-ipcam/direct_stream_server.py`

### 2a. Use a threaded HTTP server

Replace the import:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer
except ImportError:
    import socketserver

    class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True
```

Then replace:

```python
self.server = HTTPServer(("0.0.0.0", self.port), handler_class)
```

with:

```python
self.server = ThreadingHTTPServer(("0.0.0.0", self.port), handler_class)
```

This prevents a long-lived stream request from blocking health checks or other
short control requests.

### 2b. Add `/health`

At the start of `do_GET`:

```python
if self.path == "/health":
    self.send_response(200)
    self.send_header("Content-Type", "text/plain")
    self.end_headers()
    self.wfile.write(b"OK")
    return
```

The Docker healthcheck should then use:

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8089/health"]
```

### 2c. Standardize the stream format

Use MPEG-TS consistently:

```python
if self.path in ("/stream.ts", "/stream.h264"):
    self.send_response(200)
    self.send_header("Content-Type", "video/MP2T")
```

Apply the same path/content-type handling in `do_HEAD`; OpenCV/FFmpeg probing
can issue HEAD requests before opening the stream.

Change the FFmpeg output format:

```python
"-f", "mpegts",
"-"
```

The HPE input should move to `/stream.ts` once this is implemented:

```bash
HPE_INPUT=http://h264-streaming-server:8089/stream.ts
```

Keeping `/stream.h264` temporarily as an alias is acceptable for compatibility,
but the canonical endpoint should match the format.

---

## Fix 3: Pass The Correct HPE Video Path

`main.py` calls `utils.video_detection.detect_video_properties()` for HTTP
inputs. That function first tries the streamer's `/video_info` endpoint, which
`direct_stream_server.py` currently does not implement, then falls back to
`VIDEO_PATH` and runs `ffprobe` inside the HPE container. This fallback is valid
only if `VIDEO_PATH` uses the HPE container mount path.

The earlier draft proposed:

```yaml
- VIDEO_PATH=${VIDEO_FILE:-/videos/rangeOfMotion/vga_01_01.mp4}
```

That is unsafe because `VIDEO_FILE` belongs to the streamer container and may
be `/app/videos/...`. HPE needs the same file under `/videos/...`.

### 3a. `ffmpeg_hpe/run_experiment_bcc.sh`

After `VIDEO_FILE_RELATIVE` is resolved, export an HPE-specific path:

```bash
export VIDEO_FILE="$VIDEO_FILE_CONTAINER"
export HPE_VIDEO_PATH="/videos/$VIDEO_FILE_RELATIVE"
```

### 3b. `ffmpeg_hpe/docker-compose.yaml`

Add this to the `hpe` service environment:

```yaml
- VIDEO_PATH=${HPE_VIDEO_PATH:-/videos/rangeOfMotion/vga_01_01.mp4}
```

Do not reuse `${VIDEO_FILE}` for HPE unless it has already been normalized to
the HPE container mount path.

### 3c. Other ffmpeg HPE rigs

If `ffmpeg_hpe_cpu/docker-compose.cpu.yaml` is still active in the branch, apply
the same `HPE_VIDEO_PATH` contract there. Do not add this blindly to stale or
deleted rigs.

---

## Fix 4: Results Collection

`run_experiment_bcc.sh` must copy the new live-stream files from HPE output into
the timestamped results directory:

```text
hpe_output/*_live_metrics.csv
hpe_output/*_live_frame_map.csv
logs/hpe.log
logs/h264-streaming-server.log
traces/bcc/video_rx.csv
traces/bcc/port_info.txt
perf/perf_metrics.csv
gpu/gpu_metrics.csv
```

The live metrics are part of the result contract, not optional debug output.

---

## Fix 5: Validator Changes

The validator should support two modes:

### Non-live finite-video mode

Existing strict checks still apply:

```text
processed_frames == expected_video_frames
JSON frame count == processed_frames
JSON frame numbers are sequential with no gaps
```

### Live-stream mode

The run can pass with dropped frames, but only if the drops are explicit and the
stream did not collapse:

```text
live_metrics.csv exists and is parseable
live_frame_map.csv exists and is parseable
processed_frames == JSON frame count
processed_frames == rows in live_frame_map.csv
source frame numbers in live_frame_map.csv are monotonic
dropped_frames >= 0
processed_frames + dropped_frames == source_frames_observed
read_failures == 0 for timed/max-frame exits
exit_reason is one of: timeout, max_frames, source_ended
hpe.log contains no Packet corrupt / Invalid NAL unit size / stream timeout collapse
BCC final RX bytes match FFmpeg bytes read within 2%
CPU, memory, and GPU CSVs exist and are parseable
```

For a full finite-video live run that reaches `source_ended`, the validator
should also compare `source_frames_observed` with the expected frame count from
`VIDEO_PATH`/`ffprobe`. A timeout or `max_frames` run is allowed to stop before
observing the full source, but it must still account exactly for the frames it
did observe.

For source-ended finite streams, final read failures are acceptable only when
they are the clean EOF signal after the streamer reports normal FFmpeg
completion, there are no decoder corruption messages, and the final accounting
is otherwise exact.

---

## Acceptance Criteria

A slow-model run such as OpenPose CPU is considered paper-grade only when:

1. The HPE container exits with code `0`.
2. The streamer remains healthy for the run.
3. There are no OpenCV/FFmpeg packet corruption or invalid NAL errors.
4. BCC RX and FFmpeg bytes-read differ by no more than `2%`.
5. CPU and memory metrics are positive and plausible.
6. GPU metrics CSV exists and is parseable, even if utilization is zero.
7. Live-mode drop metrics exist and account for every observed source frame.
8. The report clearly labels processed FPS, source FPS, dropped frames, and
   drop rate.

This lets the paper compare models honestly: fast models can process almost all
live frames; slow models may process fewer frames, but the frame loss is
measured rather than hidden by stream failure.
