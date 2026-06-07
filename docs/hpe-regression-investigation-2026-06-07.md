# HPE Regression Investigation - 2026-06-07

## Summary

This note records the investigation into pose rendering regressions observed on
`unit_tests/images/testImage.jpg` on branch `perf-tuning-base`.

The original report compared AlphaPose output against OpenPose output. AlphaPose
rendered five skiers correctly, while OpenPose missed/misaligned people and drew
bounding boxes over neighboring skiers.

The investigation expanded to all registered HPE methods:

- `openpose`
- `alphapose`
- `movenet`
- `hrnet`
- `ae1`
- `ae2`
- `ae3`

## Reproduction Command

```powershell
.\.venv\Scripts\python.exe main.py --method openpose --input .\unit_tests\images\testImage.jpg --device CPU --save_image
```

## Root Causes

### OpenPose Coordinate Projection

OpenPose was transformed twice:

- `BaseHPE.process_frame()` padded/resized the source image to the configured model size.
- `OpenVINOBaseHPE.run_model()` passed that already-resized frame into the OpenVINO model API.
- The OpenVINO OpenPose wrapper performed its own preprocessing and returned decoded coordinates in the image space it received.
- `OpenVINOBaseHPE.postprocess()` then scaled those coordinates again back toward the original image size.

That combination caused misprojected skeletons and bounding boxes.

Fix:

- Pass the original frame to the OpenVINO model API for `openpose`.
- Do not apply the extra repository-level coordinate scale for `openpose` decoded poses.

Commit:

```text
66bee06 Fix OpenPose coordinate projection
```

### HigherHRNet Coordinate Projection

HigherHRNet had the same model-API-space problem, but the visual symptom was
more severe: one decoded pose had visible keypoints outside the image bounds,
including large negative x-coordinates. This produced a giant yellow box and a
long diagonal skeleton line across the frame.

Before the fix:

```text
hrnet count=4 max_visible_bbox_area=317483.7 out_of_bounds_visible_points=3
hrnet[3] bbox=(-333.6,0)-(557.9,356.1)
```

Fix:

- Pass the original frame to the OpenVINO model API for `higherhrnet`.
- Do not apply the extra repository-level coordinate scale for `higherhrnet` decoded poses.
- Keep the previous pre-resized path for `efficienthrnet1`, `efficienthrnet2`, and `efficienthrnet3` because their smoke outputs remained coordinate-sane.

After the fix:

```text
hrnet count=5 max_visible_bbox_area=31202.9 out_of_bounds_visible_points=0
ae3   count=5 max_visible_bbox_area=28488.9 out_of_bounds_visible_points=0
```

Commit:

```text
a82c8af Fix HigherHRNet coordinate projection
```

### Duplicate Model Loading

`main.py` called `hpe.load_model()` before dispatching to the main loop. Later,
`BaseHPE.main_loop()` and `OpenVINOBaseHPE.main_loop()` also added loop-level
load guards:

```python
if not hasattr(self, 'model') or self.model is None:
    self.load_model()
```

That guard works for OpenVINO models because they set `self.model`, but MoveNet
uses `self.pd_exec_net` and AlphaPose uses `self.pose_model`. As a result,
MoveNet and AlphaPose loaded twice.

Fix:

- Remove the eager `hpe.load_model()` call from `main.py`.
- Let the processing loop perform exactly one load through the existing guard.

Validation confirmed MoveNet and AlphaPose now print only one model load.

Commit:

```text
85592ab Avoid duplicate HPE model loading
```

## Smoke Check Results

All smoke checks used CPU and the same input image.

```powershell
.\.venv\Scripts\python.exe main.py --method <method> --input .\unit_tests\images\testImage.jpg --device CPU --save_image --json --output_dir .\out\smoke_<method>
```

Initial all-model check:

| Method | Status | Detections | Time | Notes |
|---|---:|---:|---:|---|
| `openpose` | Passed after fix | 5 | 71.0ms | No out-of-bounds keypoints. |
| `alphapose` | Passed | 5 | 10415.7ms | Visual output correct. |
| `movenet` | Passed | 5 | 26.0ms | No coordinate regression. |
| `ae1` | Passed | 3 | 74.9ms | Fewer detections, coordinates sane. |
| `ae2` | Passed | 4 | 99.0ms | Fewer detections, coordinates sane. |
| `ae3` | Passed | 5 | 186.0ms | No coordinate regression. |
| `hrnet` | Failed before fix | 4 | 841.5ms | Out-of-bounds keypoints, giant bbox. |

Coordinate sanity summary before the HigherHRNet fix:

```text
openpose  count=5 max_visible_bbox_area=28505.8  out_of_bounds_visible_points=0
hrnet     count=4 max_visible_bbox_area=317483.7 out_of_bounds_visible_points=3
ae1       count=3 max_visible_bbox_area=26906.2  out_of_bounds_visible_points=0
ae2       count=4 max_visible_bbox_area=28871.5  out_of_bounds_visible_points=0
ae3       count=5 max_visible_bbox_area=28488.9  out_of_bounds_visible_points=0
alphapose count=5 max_visible_bbox_area=29548.5  out_of_bounds_visible_points=0
movenet   count=5 max_visible_bbox_area=26190.6  out_of_bounds_visible_points=0
```

Focused validation after fixes:

```text
openpose: command completed, output written to out/verify_openpose_after_load_fix/COCOformat.json
hrnet:    count=5, out_of_bounds_visible_points=0
ae3:      count=5, out_of_bounds_visible_points=0
movenet:  loaded once, output written to out/verify_movenet_single_load/COCOformat.json
alphapose: loaded once, output written to out/verify_alphapose_single_load/COCOformat.json
```

## Git History Findings

### OpenPose

The broken pattern was introduced across multiple historical commits.

| Commit | Branch/Lineage | Finding | Confidence |
|---|---|---|---|
| `4e904a1` `Rough first version of working openpose model` | `main` lineage | Routed OpenPose through OpenVINO model API while still using repository-level preprocessing. | Medium |
| `27ce7ef` `Use one class for all OpenVINO methods except Movenet` | `main` lineage | Shared `OpenVINOBaseHPE` preserved external coordinate scaling after model API postprocess. | High |
| `b72b2ad` `Resize/Padd input images based on the base model used` | `main` lineage | Added model-specific pad/resize sizing, including OpenPose `(456, 256)`. | High |
| `70d72bd` `feat: Configure OpenVINO CPU performance and improve higherhrnet support (original 1b082d0)` | `feat/ov-epyc-4vcpu` into `perf-tuning-base` | Reintroduced the same pre-resize plus model-API postprocess plus external scale pattern in the current branch. | High |

`a90d5dd` changed OpenVINO configuration and model paths, but it was not the
original source of the OpenPose coordinate regression. The problematic pattern
already existed before that commit.

### HigherHRNet

| Commit | Branch/Lineage | Finding | Confidence |
|---|---|---|---|
| `f291c93` `Add HigherHRNet hpe` | `main` lineage | Introduced HigherHRNet through OpenVINO model API with center padding while still using repository-level scaling. | Medium |
| `70d72bd` / original `1b082d0` | `feat/ov-epyc-4vcpu` / `origin/feat/openvino-opti-cpu` | Current branch version had the same preprocessing-space mismatch. | High |

### Duplicate Loading

| Commit | Branch/Lineage | Finding | Confidence |
|---|---|---|---|
| `e65be49` initial commit | `main` lineage | `main.py` eagerly called `hpe.load_model()`. | High |
| `aa6ac2c5` `Add async and threaded support to OpenVINO HPE` | `origin/hpe-benchmark` lineage, now in `perf-tuning-base` | Added loop-level load guards that checked only `self.model`, causing MoveNet and AlphaPose to load twice. | High |

## Branch Containment Notes

Current branch:

```text
perf-tuning-base
```

Relevant containment findings:

```text
70d72bd is contained in feat/ov-epyc-4vcpu, perf-tuning-base, and related remote branches.
1b082d0 is contained in origin/feat/openvino-opti-cpu, origin/cuda-dev, origin/latest-alphapose-integration, and origin/pyav-integration.
b72b2ad and 27ce7ef are contained in main and related historical branches.
aa6ac2c5 is contained in perf-tuning-base and hpe-benchmark-related branches.
```

## Files Changed By Fixes

```text
openvino_base_hpe.py
main.py
```

## Follow-Up Watch Items

- `ae1` and `ae2` produce fewer detections than AlphaPose/OpenPose on the sample image, but their coordinates are in bounds. This looks like model sensitivity rather than a coordinate regression.
- The OpenVINO model API returns coordinates in the image space passed to `model.preprocess()`. Future changes should avoid applying a second coordinate transform unless the model receives a repository-preprocessed frame intentionally.
- If the AE models are later changed to consume original frames too, their repository-level coordinate scaling should be revisited together with the input-space change.
