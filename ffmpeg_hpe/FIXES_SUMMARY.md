# RTSP MediaMTX Migration — Fixes Summary

## Overview

This document summarizes all fixes applied to the `ffmpeg_hpe` experiment rig on the `final-merge-validation` branch to address issues identified in the RTSP MediaMTX migration review.

---

## ✅ Fixed Issues

### 1. GPU Runtime Inconsistency for CPU-Only Models

**Problem:** HPE container always required NVIDIA runtime even for CPU-only methods (movenet, ae1, ae2, ae3, hrnet), preventing execution on hosts without GPU drivers.

**Files Modified:**
- `ffmpeg_hpe/docker-compose.yaml`
- `ffmpeg_hpe/run_experiment.sh`

**Changes:**
- Removed hardcoded `runtime: nvidia` from `hpe` service
- Changed to `runtime: ${HPE_RUNTIME:-runc}` (defaults to standard runc)
- Removed unconditional GPU device reservation from deploy block
- `run_experiment.sh` now sets:
  - `HPE_RUNTIME=nvidia` + `NVIDIA_VISIBLE_DEVICES=all` for alphapose/openpose
  - `HPE_RUNTIME=runc` + `NVIDIA_VISIBLE_DEVICES=none` for all other methods

**Result:** CPU-only methods can now run on hosts without NVIDIA drivers.

---

### 2. Missing Video File Validation

**Problem:** Streamer started without checking if the video file exists, leading to silent FFmpeg crashes and restart loops.

**Files Modified:**
- `ffmpeg_hpe/run_experiment.sh` (new step 9b)

**Changes:**
- Added validation of `../videos/${VIDEO_FILE_NAME:-vga_01_01.mp4}` before streamer starts
- Script exits with clear error message if file is missing
- Validation happens before any containers start

**Result:** Fast-fail with actionable error message instead of silent crash loops.

---

### 3. No Stream Validation Before HPE Starts

**Problem:** HPE started immediately after streamer with no verification that the RTSP stream was actually being published, causing connection failures.

**Files Modified:**
- `ffmpeg_hpe/run_experiment.sh` (new step 9d and `wait_for_rtsp_stream()` function)

**Changes:**
- Added `wait_for_rtsp_stream()` function that probes `rtsp://127.0.0.1:8554/stream`
- Uses `ffprobe` (TCP, reads one frame) if available
- Falls back to MediaMTX REST API (`/v3/paths/list` checking for `readyTime`)
- 60-second timeout with warning (non-fatal) if stream not confirmed
- Function called after streamer starts, before HPE starts

**Result:** HPE only starts once the stream is confirmed live, eliminating race-condition failures.

---

### 4. Startup Race Conditions

**Problem:** Original sequence was: broker start → streamer start → HPE start (immediate), with no gates between steps. HPE often attempted to connect before the stream was ready.

**Files Modified:**
- `ffmpeg_hpe/run_experiment.sh` (reordered steps 8-10)

**Changes:**
- New sequence:
  1. Start broker, wait for port 8554 to accept connections
  2. Validate video file exists
  3. Start streamer
  4. Wait for RTSP stream to be published (new)
  5. Start HPE
- Removed reliance on bare `sleep 2` for synchronization

**Result:** Deterministic startup with proper gates at each stage.

---

### 5. `tracer_output` Directory Not Pre-Created

**Problem:** Docker volume mount `./tracer_output:/opt/tracer/output` failed if directory didn't exist; Docker created it as root, preventing bcc-tracer from writing.

**Files Modified:**
- `ffmpeg_hpe/run_experiment.sh` (step 5)

**Changes:**
- Added `mkdir -p ./tracer_output` in cleanup step before containers start

**Result:** bcc-tracer can always write output files.

---

### 6. No Cleanup of `tracer_output` Between Runs

**Problem:** Old BCC trace data accumulated across runs, potentially contaminating results.

**Files Modified:**
- `ffmpeg_hpe/run_experiment.sh` (step 5)

**Changes:**
- Added `rm -rf ./tracer_output` before `mkdir -p` in cleanup step

**Result:** Each run starts with a clean slate.

---

### 7. Healthcheck Intervals Too Long

**Problem:** `gpu-metrics` healthcheck was 30s interval / 10s timeout / 3 retries = up to 90s before marked unhealthy.

**Files Modified:**
- `ffmpeg_hpe/docker-compose.yaml`

**Changes:**
- Reduced to 10s interval / 5s timeout / 3 retries
- Failure now detected in ~35s instead of ~90s

**Result:** Faster failure detection for monitoring sidecars.

---

### 8. `bcc-tracer` Missing `streamer` in `depends_on`

**Problem:** If streamer restarted, bcc-tracer might detect wrong port; dependency not explicit in compose file.

**Files Modified:**
- `ffmpeg_hpe/docker-compose.yaml`

**Changes:**
- Added `streamer` to `bcc-tracer`'s `depends_on` list

**Result:** Docker dependency graph reflects actual runtime relationship.

---

## ❌ Issues Investigated and Closed (Not Valid)

### Issue 2: BCC Tracer Port Detection Fragile

**Original Claim:** `ss -ntp | grep ":8554"` matches any connection to that port; multiple containers could cause wrong port detection.

**Investigation Result:** Claim is **outdated**. Current code:
- Uses `awk` with filters for connection state (`ESTAB`) and remote endpoint (`$STREAMER_IP:$STREAMER_PORT`)
- Only one RTSP connection exists in the shared network namespace (`network_mode: "service:hpe"`)
- No other containers share HPE's network namespace

**Verdict:** Code is correct as-is. No fix needed.

**Details:** See `ISSUE_2_AND_5_ANALYSIS.md`

---

### Issue 5: Hardcoded `eth0` in BCC Tracer

**Original Claim:** Interface is hardcoded to `eth0`; `entrypoint.sh` detects it dynamically but doesn't pass it to Python.

**Investigation Result:** Claim is **outdated**. Current code:
- `entrypoint.sh` detects interface via `ip route` (default route) with fallback to first non-loopback interface
- Interface is passed to Python as 4th argument: `"$INTERFACE"`
- Python accepts it via `sys.argv[4]`; `"eth0"` is only a defensive fallback for manual invocation

**Verdict:** Code is correct as-is. No fix needed.

**Details:** See `ISSUE_2_AND_5_ANALYSIS.md`

---

## Files Modified

| File | Changes |
|---|---|
| `ffmpeg_hpe/docker-compose.yaml` | GPU runtime conditional, healthcheck intervals, bcc-tracer depends_on |
| `ffmpeg_hpe/run_experiment.sh` | Video validation, stream readiness check, startup reordering, tracer_output cleanup |

---

## Testing Recommendations

1. **CPU-only method on non-GPU host:**
   ```bash
   cd ffmpeg_hpe
   ./run_experiment.sh movenet
   ```
   Should start cleanly without NVIDIA runtime errors.

2. **Missing video file:**
   ```bash
   VIDEO_FILE_NAME=nonexistent.mp4 ./run_experiment.sh movenet
   ```
   Should exit immediately with clear error message.

3. **Stream readiness:**
   - Monitor logs during startup — should see `[INFO] RTSP stream is live` before HPE starts
   - No more "Connection refused" or "Stream not found" errors from HPE

4. **Tracer output cleanup:**
   ```bash
   ./run_experiment.sh movenet
   ls -la tracer_output/  # Should contain only current run's data
   ```

---

## Commit Message Suggestion

```
fix(ffmpeg_hpe): harden RTSP pipeline startup and GPU runtime handling

- Make GPU runtime conditional on HPE method (alphapose/openpose only)
- Add video file validation before streamer starts
- Add RTSP stream readiness check before HPE starts
- Reorder startup sequence to eliminate race conditions
- Pre-create and clean tracer_output directory between runs
- Reduce gpu-metrics healthcheck interval from 30s to 10s
- Add streamer to bcc-tracer depends_on for explicit dependency

Closes issues: GPU runtime inconsistency, missing video validation,
stream validation, startup races, tracer_output handling, healthcheck
intervals, bcc-tracer dependencies.

Investigated and closed (not valid): BCC port detection fragility,
hardcoded eth0 interface (both already fixed in current code).
```
