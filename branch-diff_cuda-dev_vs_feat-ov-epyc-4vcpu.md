# Branch Diff Report: cuda-dev vs feat/ov-epyc-4vcpu

Note: These branches have no common ancestor (unrelated histories). This report compares the tip trees directly (two-dot diff: `git diff cuda-dev feat/ov-epyc-4vcpu`) and summarizes unique commits on each side via symmetric log.

## Summary

- Comparison: `cuda-dev` (left) vs `feat/ov-epyc-4vcpu` (right)
- Files changed: 18
- Insertions: 92,931
- Deletions: 79
- Adds/Mods: 10 added, 8 modified, 0 deleted, 0 renamed
- Major delta driver: Added OpenVINO model XMLs/bin (large text/binary files)

## High-Impact Areas

- Models: 7 files under `models/...` including large XMLs and one BIN
- OpenVINO HPE code: `openvino_base_hpe.py` (+97/−47), `base_hpe.py` (+33)
- App entry: `main.py` (+13/−3)
- AlphaPose utils: minor adjustments in `simple_transform.py`, `roi_align.py`
- Docker/FFmpeg: `ffmpeg_hpe/docker-compose.yaml` (+8), new `Optimization_guide.md`
- Docs/Config: new `WARP.md`, `.gitignore` tweaks

## Commits Overview (symmetric difference)

Only on feat/ov-epyc-4vcpu (5):

1. 797089e Refactor video capture, enhance logging, and update OpenVINO configuration
2. 2b94e42 update gitignore to exclude  all *.bin
3. f6e447a docs: Add WARP.md for repository guidance and update gitignore
4. 5721305 OpenVINO CPU tuning for 4-vCPU VPS (threads/hints/pinning) + bugfix
5. 70d72bd feat: Configure OpenVINO CPU performance and improve higherhrnet support (original 1b082d0)

Only on cuda-dev (many; first 30 shown):

1. 1b082d0 feat: Configure OpenVINO CPU performance and improve higherhrnet support
2. cc43177 feat: Add PyNvCodec for hardware-accelerated video decoding
3. 990dd2b Refactor AlphaPose input and add image preprocessing
4. db0748a feat: Expose detection batch size as CLI argument
5. 2852a2e Add HPE Dockerfile with CUDA and OpenVINO support
6. 76808c1 Refactor Docker configurations and monitoring script: remove unnecessary PID setting in docker-compose, enhance Dockerfile with improved comments and cleanup, and update monitoring script for better error handling and performance metrics collection.
7. 496b982 Update .gitignore to include additional .DS_Store entry for better file management
8. a9e8251 updated gitignore
9. 9285361 Add recent-dash and rtsp-ipcam components: include Docker configurations, scripts, and README files for H.264 streaming server setup and usage.
10. d19a3fe addding recent-dash and rtsp-ipcam to the repository
11. e9c717a Update requirements.txt: add new dependencies and update existing ones for improved functionality
12. 938f81e Implement code changes to enhance functionality and improve performance
13. 0405b31 Remove Dockerfile_alphapose and add system_info.sh for system diagnostics
14. 57936c2 last changes
15. f64988e updated gitignore
16. c87366f Update docker-compose.yaml: adjust resource limits and reservations for improved performance
17. d9ad0a1 Update Dockerfile_base: add tcpdump installation, uncomment OpenVINO_DEVICE variable, and adjust comments for clarity
18. abb0d59 Add Dockerfile and requirements for BCC tracer; implement RX bytes plotting scripts
19. f01fb8a Refactor entrypoint.sh: remove conditional handling for nc-proxy command execution
20. 359857f Update Dockerfile_base: add ffmpeg installation, refine OpenVINO setup, and enhance model download process
21. 3760689 Enhance run_experiment_bcc.sh: improve environment variable handling for VIDEO_FILE, add error messaging, and refine results directory naming with CPU thread and device type
22. 50bd638 Update environment configuration and add BCC tracing script: modify VIDEO_FILE path, enhance docker-compose settings, and introduce run_experiment_bcc.sh for improved diagnostics and monitoring
23. 40806ee Enhance video capture handling: set timeout properties for cv2.VideoCapture and improve retry logic
24. fc7147d Refactor entrypoint.sh: add conditional handling for nc-proxy command execution
25. 1e078d9 Update run_experiment.sh: add cleanup for old CSV files in the ./csv directory before starting a new experiment
26. ea4a4a2 Refactor trace_video_traffic.sh and run_experiment.sh: enhance bpftrace script for RX bytes tracking and comment out unused CSV copying logic
27. ba969ce Enhance video traffic tracer and experiment script: add tcpdump summary, improve cleanup, and adjust container log handling
28. a41d3e7 Update output volume path for HPE service and adjust command to specify output directory
29. 8a2932f Fix condition to include CSV saving option in BaseHPE initialization
30. 995ac89 Increase detector and pose batch sizes in AlphaPoseHPE; add debug diagnostics to run_experiment.sh

…and many more on `cuda-dev`.

## File Change Summary (two-dot)

Added (10):
- `.aider.chat.history.md`
- `.aider.input.history`
- `.aider.tags.cache.v4/cache.db` (binary)
- `WARP.md`
- `ffmpeg_hpe/Optimization_guide.md`
- `models/OpenVINO/pretrained_models/public/human-pose-estimation-0005/FP32/human-pose-estimation-0005.xml` (+30,803)
- `models/OpenVINO/pretrained_models/public/human-pose-estimation-0006/FP32/human-pose-estimation-0006.bin` (binary)
- `models/OpenVINO/pretrained_models/public/human-pose-estimation-0006/FP32/human-pose-estimation-0006.xml` (+30,803)
- `models/OpenVINO/pretrained_models/public/human-pose-estimation-0007/FP32/human-pose-estimation-0007.xml` (+30,803)
- `openvino_base_hpe.py.bak` (+175)

Modified (8):
- `.gitignore` (+3/−12)
- `base_hpe.py` (+33)
- `ffmpeg_hpe/docker-compose.yaml` (+8)
- `main.py` (+13/−3)
- `models/AlphaPose/alphapose/utils/presets/simple_transform.py` (+5/−2)
- `models/AlphaPose/alphapose/utils/roi_align/roi_align.py` (+15/−4)
- `models/OpenVINO/model_api/models/open_pose.py` (+19/−11)
- `openvino_base_hpe.py` (+97/−47)

## Commentary

- Scope: The right branch (`feat/ov-epyc-4vcpu`) introduces targeted OpenVINO CPU tuning, logging, and capture refactors, plus docs/gitignore updates. The left branch (`cuda-dev`) includes a much broader set of changes across Docker tooling, monitoring scripts, and model support.
- Large artifacts: Most insertions come from adding OpenVINO model XMLs and a BIN file. Consider using Git LFS or excluding large model files from diffs to keep reviews focused on code.
- Model pipeline: `openvino_base_hpe.py` and `base_hpe.py` are the main code deltas; review these for CPU thread/hints/pinning changes and any API adjustments affecting inference paths.
- Integration: Minor edits in `main.py` suggest CLI/plumbing updates; verify args and defaults remain compatible.
- AlphaPose utils: Small math/transform tweaks; ensure no regressions in preprocessing and ROI alignment.
- DevOps: `docker-compose.yaml` gains small changes; confirm resource settings align with 4‑vCPU expectations.

## Suggested Review Path

1. Ignore large model files (XML/BIN) during code review.
2. Focus on `openvino_base_hpe.py` and `base_hpe.py` for performance and behavior changes.
3. Verify `main.py` flags/env interactions (especially CPU tuning parameters).
4. Skim AlphaPose utility diffs for correctness.
5. Confirm Docker config aligns with deployment target (4‑vCPU VPS).

## Reproduce Locally

Commands used:

```
# Unique commits on each side (even without merge base)
git log --oneline --no-decorate --left-right --cherry-pick --no-merges cuda-dev...feat/ov-epyc-4vcpu

# Two-dot tree diff since branches are unrelated
git diff --shortstat --find-renames=50% cuda-dev feat/ov-epyc-4vcpu
git diff --stat --find-renames=50% cuda-dev feat/ov-epyc-4vcpu
git diff --name-status --find-renames=50% cuda-dev feat/ov-epyc-4vcpu
git diff --numstat --find-renames=50% cuda-dev feat/ov-epyc-4vcpu
```

## Per-File Commentary

### .gitignore
- Intent: Generalize ignores for model binaries by adding `*.bin`; add `.aider*`; remove many hardcoded model BIN paths.
- Impact: Reduces churn and maintenance; prevents accidental commits of all `*.bin` files.
- Risks: Might ignore legitimate small `.bin` artifacts if any are meant to be tracked; ensure needed binaries (if any) are pulled by scripts.
- Review checklist: Confirm model-download flow; consider Git LFS for large IR files; keep `.aider*` if team agrees.

### base_hpe.py
- Intent: Add `_init_opencv_video_capture` helper to robustly open sources and infer frame size; unify fallback when PyNvCodec fails.
- Impact: Sets `self.cap`, `self.img_w`, `self.img_h`; improves behavior when metadata lacks dimensions.
- Risks: The inline comment says “inside class OpenVINOBaseHPE” but method lives in `BaseHPE` (slightly misleading). Ensure no duplicate method elsewhere.
- Review checklist: Verify rewind logic after probing first frame; ensure all subclasses rely on `BaseHPE._init_opencv_video_capture` consistently.

### ffmpeg_hpe/docker-compose.yaml
- Intent: Document CPU tuning env vars (OV_MODE/OV_STREAMS/OV_THREADS and BLAS threads); currently commented.
- Impact: Makes CPU tuning discoverable for 4‑vCPU targets.
- Risks: None while commented; when enabled, ensure consistency with app defaults.
- Review checklist: If enabling, align values with `openvino_base_hpe.py` defaults; avoid over‑subscription.

### main.py
- Intent: Limit OpenCV threads (`cv2.setNumThreads(1)`); suppress noisy aspect‑ratio warnings; adjust method map (comment out AlphaPose; simplify OpenPose args).
- Impact: More predictable CPU usage; cleaner logs; OpenPose no longer passes `detbatch` (not needed for OV models).
- Risks: Removing `alphapose` from map disables that method via CLI; confirm that’s intended. Global log filter may hide legitimate messages containing the same substring.
- Review checklist: Validate CLI still exposes desired methods; confirm `OpenVINOBaseHPE` handles kwargs without `detbatch`.

### models/OpenVINO/model_api/models/open_pose.py
- Intent: Avoid dynamically adding `pooled_heatmaps` NMS node; make pooled heatmaps optional; set correct blob names (`Mconv7_stage2_L1/L2`).
- Impact: Better compatibility with OpenVINO runtime; option to run without pooled heatmaps; fixes output mapping.
- Risks: If downstream expects pooled heatmaps, must set `use_pooled_heatmaps=True` and ensure model actually outputs it.
- Review checklist: Sanity‑check postprocess path when `use_pooled_heatmaps=False`; verify decoder works with raw heatmaps.

### openvino_base_hpe.py
- Intent: Introduce environment‑driven CPU tuning (OV_MODE/OV_THREADS/OV_STREAMS); switch to `openvino.properties` API; sanitize plugin config; compute safe aspect ratio; provide per‑model config (disable pooled heatmaps for OpenPose; set `upsample_ratio` as int).
- Impact: More robust on 4‑vCPU VPS; clearer, explicit configuration; safer preprocess/postprocess scaling; debug print of effective OV properties.
- Risks: Requires OpenVINO version with `openvino.properties`; `get_user_config` sanitation may need updates if downstream relies on those keys; debug prints may be noisy in production.
- Review checklist: Confirm OV version compatibility; validate effective threads/streams at runtime; consider gating debug prints behind a verbosity flag; verify `higherhrnet`/AE configs produce correct shapes.

### models/AlphaPose/alphapose/utils/presets/simple_transform.py
- Intent: Prefer torchvision RoIAlign when CUDA extension is unavailable or CPU is used; minor indentation fix in return.
- Impact: Enables CPU path without custom CUDA extension when torchvision is present.
- Risks: Requires corresponding support in `RoIAlign` wrapper to accept `use_torchvision`; otherwise mismatch.
- Review checklist: Ensure `roi_align.RoIAlign` signature supports `use_torchvision`; test CPU inference path for AlphaPose.

### models/AlphaPose/alphapose/utils/roi_align/roi_align.py
- Intent: Make CUDA extension import optional; add clearer error/warning messages; guard backward on CPU.
- Impact: Fails fast with helpful messages when CUDA ext is missing; documents need for torchvision fallback.
- Risks: Still `NotImplementedError` on CPU path here unless torchvision‑based RoIAlign is wired in elsewhere.
- Review checklist: Confirm end‑to‑end CPU fallback exists via torchvision if desired; otherwise leave AlphaPose as GPU‑only.

### WARP.md
- Intent: Add developer documentation for Warp; overview, setup, and usage guidance.
- Impact: Documentation only.
- Risks: None.
- Review checklist: Ensure instructions match current dependency versions; add links to model downloads.

### openvino_base_hpe.py.bak
- Intent: Likely a backup checkpoint.
- Impact: Adds noise; risk of confusion.
- Risks: Editors or tooling might pick up the `.bak` file inadvertently.
- Review checklist: Remove this file or add a specific ignore for `*.bak` if needed.

### models/OpenVINO/pretrained_models/public/... (XML/BIN)
- Intent: Add OpenVINO IR files for models 0005/0006/0007.
- Impact: Large diffs; repository size growth.
- Risks: Binary bloat and slow clones; accidental commits for updated weights.
- Review checklist: Move to Git LFS or download scripts; keep `.gitignore` patterns broad (e.g., `*.bin`).
