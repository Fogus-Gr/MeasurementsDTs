# HPE File Differences: perf-tuning-base vs origin/main & origin/evaluation

**Date**: 2026-06-01  
**Branches compared**: `perf-tuning-base` (current) vs `origin/main` and `origin/evaluation`  
**Note**: `origin/main` and `origin/evaluation` have identical implementations for HPE files

---

## Summary

The `perf-tuning-base` branch contains significant performance tuning and benchmarking features that are not present in `origin/main` or `origin/evaluation`. These changes focus on:

- OpenVINO CPU performance tuning (threads, streams, pinning, hyper-threading)
- HTTP stream support with video property detection
- Timeout and frame limiting for controlled benchmarking
- GPU-accelerated video decoding (PyNvCodec)
- Structured logging for benchmarking experiments
- FPS tracking and display

---

## File-by-File Differences

### main.py

**Added CLI arguments:**
- `--detbatch`: Detection batch size for AlphaPose (default: 5)
- `--timeout`: Timeout in seconds for processing (0=unlimited, default: 0)
- `--max_frames`: Maximum number of frames to process (0=unlimited, default: 0)

**Added features:**
- Structured logging via `log_structured_data()` for session start/end, video properties, configuration changes
- HTTP stream detection with automatic video property detection (FPS, duration, frame count)
- FPS conversion for HTTP streams (converts frame count based on streamer target FPS of 25)
- Timeout support via `main_loop_with_timeout()` for HTTP streams and video files
- Logging filter to hide aspect ratio warnings (`_HideAspectWarn`)

**Modified behavior:**
- Main loop now branches based on input type (HTTP stream, webcam, video file)
- Auto-sets `max_frames` based on detected video properties when not explicitly provided
- Logs detailed configuration changes and detection results

---

### base_hpe.py

**Added methods:**
- `main_loop_with_timeout(timeout, max_frames)`: Processes frames with timeout and frame limit
- Progress updates every 100 frames with elapsed time and average FPS

**Modified `process_frame()`:**
- Changed parameter from `image_id` to `frame_number`
- Added PyTorch tensor handling for GPU frames (PyNvCodec outputs RGB, converts to BGR)
- Added FPS tracking using `processing_times` deque (max 200 entries)
- Calculates and displays FPS on console (single line that updates)
- Draws FPS text on the frame using OpenCV
- Modified render call to use `score_thresh` instead of `show_scores`

**Added attributes:**
- `processing_times`: Deque for tracking inference times
- `max_processing_times_len`: Maximum length of processing times deque (200)

---

### openvino_base_hpe.py

**Added OpenVINO CPU tuning (via ENV vars):**
- `OV_THREADS`: Number of CPU threads (default: auto-detects based on sched_getaffinity)
- `OV_MODE`: Performance mode - "latency" or "throughput" (default: "latency")
- `OV_STREAMS`: Number of inference streams (default: None)
- `OV_CPU_PINNING`: Enable CPU core pinning (default: False)
- `OV_HYPER_THREADING`: Enable hyper-threading (default: False)

**Added configuration method:**
- `_configure_core(core)`: Sets OpenVINO performance properties based on ENV vars
- Prints effective settings after configuration

**Modified `load_model()`:**
- Added OpenPose-specific configuration with `use_pooled_heatmaps: False` (this was a bug - see note below)
- Separates config for OpenPose vs other models (HRNet, AE1-3, HigherHRNet)
- Calls `_configure_core()` before creating model adapter

**Modified `run_model()`:**
- Returns both poses and scores as tuple instead of just poses
- Added null check for `raw_result`

**Modified `postprocess()`:**
- Changed parameter from `poses` to `predictions`
- Handles predictions tuple (poses, scores) or single predictions
- Improved keypoint scaling with in-place operations
- Added `dtype=float` to keypoint normalization

**Added `main_loop()` override:**
- Handles streaming URLs with proper video capture initialization
- Added directory input support (processes all images in directory)
- Added PyNvCodec GPU decoding path
- Added OpenCV video/webcam/stream fallback
- Calls JSON/CSV saving after processing

**Added video capture methods:**
- `_init_opencv_video_capture(input_src)`: Initializes OpenCV capture with FFmpeg backend for HTTP streams
- `_ensure_video_capture()`: Lazy initialization for streaming URLs

**Note on OpenPose bug:**
The current branch had `use_pooled_heatmaps: False` in the OpenPose config, which disabled NMS and caused multiple detections per person. This was fixed by reverting `open_pose.py` to `origin/main`, which dynamically adds the pooled_heatmaps layer to the model.

---

### movenet_hpe.py

**Modified imports:**
- Changed from `from utils.body import Body` to `from base_hpe import BaseHPE, Body`

**Added method:**
- `_init_opencv_video_capture(input_src)`: HTTP stream support with FFmpeg backend
  - Handles webcam input (integer or string digit)
  - Uses FFmpeg backend for HTTP streams with buffer size 1
  - Gets video properties (width, height, FPS)
  - Defaults to 25 FPS if detection fails

**Minor formatting:**
- Whitespace cleanup in `run_model()`

---

### alphapose_hpe.py

**Added GPU-accelerated detection path:**
- Direct GPU tensor handling with torchvision transforms
- Manual normalization on GPU (mean/std)
- Fallback to manual resizing if GPU transform fails

**Added GPU cropping/resizing:**
- Uses `torchvision.transforms.functional.crop()` for GPU cropping
- Uses `torchvision.transforms.functional.resize()` for GPU resizing
- Applies normalization manually on GPU using mean/std tensors

**Modified detection logic:**
- Handles GPU tensors directly with `images_detection()`
- Filters for human class (class index 0) and current batch
- Generates dummy IDs for detections
- Implements GPU-accelerated person cropping and resizing

**Added parameters:**
- `detbatch`: Detection batch size (passed from main.py)

**Modified pose estimation:**
- Added duplicate check for `inps is None`
- Added error handling for tensor device movement
- Improved keypoint normalization

---

## Recommendations

### What to keep from perf-tuning-base

1. **OpenVINO CPU tuning**: The ENV-based configuration (OV_THREADS, OV_MODE, OV_STREAMS, etc.) is valuable for performance benchmarking and optimization on cloud instances.

2. **HTTP stream support**: The video property detection and FPS conversion for HTTP streams is useful for benchmarking streaming scenarios.

3. **Timeout and frame limiting**: Essential for controlled benchmarking experiments, especially for long-running streams.

4. **FPS tracking and display**: The real-time FPS calculation and display on frame is useful for performance monitoring.

5. **Structured logging**: The `log_structured_data()` calls provide better experiment tracking and reproducibility.

6. **PyNvCodec GPU decoding**: The GPU-accelelerated video decoding path is valuable for GPU benchmarking.

7. **Directory input support**: Processing all images in a directory is useful for batch evaluation.

### What to consider bringing from origin/main

1. **OpenPose pooled_heatmaps**: Already fixed by reverting `open_pose.py` to origin/main. This is critical for correct OpenPose behavior.

2. **Simpler main loop**: The origin/main has a simpler main loop that just calls `hpe.main_loop()`. The current branch's timeout logic adds complexity but is useful for benchmarking.

### Potential issues to address

1. **OpenPose config in openvino_base_hpe.py**: The OpenPose-specific config with `use_pooled_heatmaps: False` is now incorrect since we reverted `open_pose.py` to origin/main. This should be removed or updated to match the origin/main approach.

2. **Code duplication**: The video capture initialization logic is duplicated in both `movenet_hpe.py` and `openvino_base_hpe.py`. Consider moving to a shared base class method.

3. **Complexity**: The current branch adds significant complexity for benchmarking features. Consider whether all features are needed for the primary use case.

### Suggested changes

1. **Remove or update OpenPose config**: Since `open_pose.py` now uses the origin/main implementation with dynamic pooled_heatmaps, the OpenPose-specific config in `openvino_base_hpe.py` should be removed or updated to not set `use_pooled_heatmaps: False`.

2. **Consolidate video capture logic**: Move `_init_opencv_video_capture()` and `_ensure_video_capture()` to `base_hpe.py` to avoid duplication.

3. **Consider feature flags**: Add feature flags to enable/disable benchmarking features (timeout, FPS display, structured logging) for simpler use cases.

4. **Update documentation**: Document the ENV variables for OpenVINO tuning and the new CLI arguments.

---

## Conclusion

The `perf-tuning-base` branch adds valuable performance tuning and benchmarking features that are not present in `origin/main` or `origin/evaluation`. The main concern is the OpenPose configuration mismatch, which has been addressed by reverting `open_pose.py`. 

The branch is well-suited for performance benchmarking and optimization work, but may be overly complex for simple inference use cases. Consider adding feature flags or a simplified mode for basic inference.

---

## Recommendations
**Keep from perf-tuning-base:**

- OpenVINO CPU tuning (OV_THREADS, OV_MODE, OV_STREAMS, etc.) - valuable for benchmarking
- HTTP stream support with video property detection - useful for streaming benchmarks
- Timeout and frame limiting - essential for controlled experiments
- FPS tracking and display - useful for performance monitoring
- Structured logging - better experiment tracking
- PyNvCodec GPU decoding - valuable for GPU benchmarking
- Directory input support - useful for batch evaluation

**Fix needed:**

- Remove or update OpenPose config in `openvino_base_hpe.py` line 235 - the `use_pooled_heatmaps: False` is now incorrect since we reverted `open_pose.py` to origin/main which uses dynamic pooled_heatmaps

**Consider:**

- Consolidate duplicated video capture logic from `movenet_hpe.py` and `openvino_base_hpe.py` into `base_hpe.py`
- Add feature flags to enable/disable benchmarking features for simpler use cases
- Update documentation for ENV variables and new CLI arguments

**No need to bring from origin/main/evaluation:**

- Already have the critical fix (open_pose.py reverted)
- The branches have identical HPE implementations
- perf-tuning-base has additional benchmarking features that are valuable for this branch's purpose
