# AGENTS-IMPROVEMENT-SPEC.md

Concrete improvements identified after auditing the codebase against AGENTS.md.
Items are ordered by impact. Each entry states the problem, the exact location,
and the required change.

---

## Audit Summary

### What is good
- Clear class hierarchy: `BaseHPE` → concrete backends. Easy to extend.
- Input routing (image / directory / video / webcam / IP stream) is centralised
  in one place (`base_hpe.py`).
- `.gitignore` correctly excludes large model binaries and build artefacts.
- `dev_tools/stream_video_server.py` has a docstring warning against production
  use.
- Commit history is clean and follows imperative style.
- `export_pose_results.py` has a `reset_results()` function, though it is never
  called (see Bug #1 below).

### What is missing
- No `AGENTS.md` (created in this session).
- No automated tests — `unit_tests/` contains only sample media, no test code.
- No linter / formatter configuration (`pyproject.toml`, `.flake8`, etc.).
- No CI pipeline (no `.github/workflows/`).
- `devcontainer.json` uses the 10 GB universal image and installs nothing;
  the environment is not usable out of the box.
- No `CHANGELOG` or release tagging convention.

### What is wrong / risky
1. **Unbound variable in `openvino_base_hpe.py → run_model`** — `results` is
   only assigned inside `if raw_result:`, but is read unconditionally on the
   next line. Raises `UnboundLocalError` when inference returns an empty result.
2. **Global accumulator state is never reset between runs** — `export_pose_results.py`
   module-level lists (`coco_results`, `csv_rows`, etc.) persist for the
   process lifetime. Running two HPE instances in the same process (e.g. in
   tests) would corrupt output. `reset_results()` exists but is never called.
3. **`AlphaPoseHPE.postprocess` uses only valid keypoints for `keypoints_norm`**
   — it stores `normalized_kps` (filtered by `valid_scores`) but the `Body`
   constructor expects all 17 keypoints for consistent downstream indexing.
4. **`MoveNetHPE.__init__` calls `super().__init__` before setting `self.xml_path`
   and `self.device`** — `BaseHPE.__init__` does not use those attributes, so
   this is currently safe, but it is fragile ordering that will break if
   `BaseHPE` ever reads them during init.
5. **`visualizer.py` keypoint colouring is broken for non-MoveNet models** —
   acknowledged in a `# TODO` comment but not tracked anywhere actionable.
6. **`requirements.txt` is a `conda install` file, not a `pip` file** — it
   lacks `flask` (needed by `dev_tools/`) and `openvino` (needed at runtime).
   A developer following the README will hit import errors.

---

## Improvement Specifications

---

### SPEC-1 — Fix `UnboundLocalError` in `openvino_base_hpe.py`

**File:** `openvino_base_hpe.py`  
**Lines:** `run_model` method (~line 70–80)

**Problem:**
```python
raw_result = self.model.infer_sync(inputs)

if raw_result:
    results = self.model.postprocess(raw_result, preprocessing_meta)

if results:          # ← UnboundLocalError if raw_result was falsy
    (poses, scores) = results
```

**Required change:**
```python
raw_result = self.model.infer_sync(inputs)

if not raw_result:
    return []

results = self.model.postprocess(raw_result, preprocessing_meta)

if not results:
    return []

(poses, scores) = results
return poses
```

Remove the nested `if` guards and use early returns. The method must always
return a value usable by `postprocess`.

---

### SPEC-2 — Reset global accumulator state on each run

**File:** `utils/export_pose_results.py`  
**File:** `base_hpe.py` (`main_loop`)

**Problem:** Module-level lists accumulate across the process lifetime.
`reset_results()` exists but is never called.

**Required change:**  
Call `reset_results()` at the start of `BaseHPE.main_loop()`, before any
frame is processed:

```python
# base_hpe.py — top of main_loop
from utils.export_pose_results import reset_results

def main_loop(self):
    reset_results()   # ← add this
    frame_number = 0
    ...
```

Also add the import at the top of `base_hpe.py` alongside the existing
`export_pose_results` imports.

---

### SPEC-3 — Fix `AlphaPoseHPE.postprocess` keypoint array shape

**File:** `alphapose_hpe.py`  
**Method:** `postprocess`

**Problem:** `keypoints_norm` is set to `normalized_kps` which contains only
the *valid* (score-filtered) keypoints, not all 17. `Body.keypoints` is also
only the valid subset. Downstream code in `visualizer.py` and
`export_pose_results.py` indexes keypoints by COCO joint index (0–16), so
missing joints cause index errors or silently wrong output.

**Required change:**  
Store all 17 keypoints in `Body`, using the full `normalized_kps` array (all
rows), and let the score array (`scores`) gate visibility at render/export time
— consistent with how `OpenVINOBaseHPE.postprocess` works:

```python
body = Body(
    score=np.mean(scores[valid_scores]),
    xmin=int(xmin * self.padding.padded_w),
    ymin=int(ymin * self.padding.padded_h),
    xmax=int(xmax * self.padding.padded_w),
    ymax=int(ymax * self.padding.padded_h),
    keypoints_score=scores,                          # all 17 scores
    keypoints=(normalized_kps * np.array([           # all 17 keypoints
        self.padding.padded_w, self.padding.padded_h
    ])).astype(float),
    keypoints_norm=normalized_kps                    # all 17 normalised
)
```

Remove the `valid_scores` filtering from the `Body` constructor call; keep it
only for the bounding-box calculation and the `if np.any(valid_scores)` guard.

---

### SPEC-4 — Fix `requirements.txt` to be pip-installable and complete

**File:** `requirements.txt`

**Problem:** The file is used with `conda install --file`, which does not
support version specifiers like `==`. It also omits `flask` and `openvino`,
which are runtime dependencies.

**Required change:**  
Split into two files:

1. **`requirements.txt`** — pip-installable, used for `pip install -r`:
   ```
   opencv-python==4.10.0.84
   numpy==1.24.4
   scipy==1.10.1
   matplotlib==3.7.5
   tqdm==4.67.0
   PyYAML==6.0.2
   cython==3.0.11
   flask>=2.3
   openvino==2024.2.0
   ```

2. **`requirements-conda.txt`** — conda-compatible (no version pins with `==`):
   ```
   pytorch==2.4.1
   torchvision==0.19.1
   ```

Update `README.md` installation steps to reference both files and clarify
which installer to use for each.

---

### SPEC-5 — Add automated smoke tests

**Directory:** `unit_tests/`

**Problem:** No test code exists. Regressions in postprocessing, export, or
input routing are only caught manually.

**Required change:**  
Create `unit_tests/test_export.py` covering `export_pose_results.py` (the
module with the most logic and the most risk from global state):

```python
# unit_tests/test_export.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.export_pose_results import (
    append_COCO_format_json, append_COCO_format_csv,
    save_COCO_format_json, save_COCO_format_csv,
    reset_results, coco_results
)

# Test: reset clears state
# Test: append_COCO_format_json produces correct COCO structure
# Test: keypoint visibility flags (0/1/2) are set correctly
# Test: Tx interval accumulation fills missing intervals with 0
# Test: save functions write valid JSON/CSV to a temp file
```

Use only the standard library (`unittest`, `tempfile`, `json`, `csv`) — no
pytest dependency required.

Create `unit_tests/test_base_hpe_routing.py` to verify that `BaseHPE.__init__`
correctly sets `input_type` for image, directory, and video paths without
requiring a real model.

---

### SPEC-6 — Improve `devcontainer.json`

**File:** `.devcontainer/devcontainer.json`

**Problem:** Uses the 10 GB universal image. Installs nothing. A developer
opening the environment cannot run the project without manual setup steps.

**Required change:**  
Switch to a Python 3.8 base image and add a `postCreateCommand` that installs
pip dependencies (conda is not available in devcontainers by default):

```json
{
  "name": "MeasurementsDTs",
  "image": "mcr.microsoft.com/devcontainers/python:3.8",
  "postCreateCommand": "pip install -r requirements.txt",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-python.pylint"]
    }
  }
}
```

Note: PyTorch and AlphaPose Cython extensions still require manual setup
(CUDA driver dependency). Document this in a `postCreateCommand` comment or
a `SETUP.md` note.

---

### SPEC-7 — Track and resolve existing `# TODO` comments

**Files:** `movenet_hpe.py`, `alphapose_hpe.py`, `visualizer.py`,
`openvino_base_hpe.py`

**Problem:** Four `# TODO` comments mark known defects but are not tracked
anywhere. They will be forgotten.

**Required change:**  
For each TODO, either fix it or open a GitHub issue and replace the comment
with a reference:

| File | TODO | Action |
|---|---|---|
| `movenet_hpe.py` line ~54 | Separate keypoint score filtering | Fix: apply per-keypoint score threshold in `postprocess` |
| `alphapose_hpe.py` line ~100 | Batch parallelism for directories | Open issue; add `# TODO(#<n>)` reference |
| `alphapose_hpe.py` line ~130 | Bounding box from detector, not keypoints | Open issue; add `# TODO(#<n>)` reference |
| `visualizer.py` line ~30 | Keypoint colouring only correct for MoveNet | Fix: use a model-agnostic left/right/centre colouring scheme based on COCO joint index |

---

### SPEC-8 — Add linter configuration

**File:** `pyproject.toml` (new)

**Problem:** No linter is configured. Code style is inconsistent (mixed
indentation in `main.py` `parse_arguments`, unused imports possible).

**Required change:**  
Create `pyproject.toml` with a minimal `flake8`/`ruff` config:

```toml
[tool.ruff]
target-version = "py38"
line-length = 100
select = ["E", "F", "W"]
ignore = ["E501"]   # long lines are common in model config dicts

[tool.ruff.per-file-ignores]
"models/*" = ["F401", "E402"]   # third-party model code
```

Add `ruff` to `requirements.txt` as a dev dependency.

---

## Priority Order

| Priority | Spec | Reason |
|---|---|---|
| P0 | SPEC-1 | Runtime crash on empty inference result |
| P0 | SPEC-2 | Silent data corruption in multi-run scenarios |
| P1 | SPEC-3 | Wrong keypoint indexing corrupts JSON/CSV output |
| P1 | SPEC-4 | Broken install path blocks new contributors |
| P2 | SPEC-5 | No regression safety net |
| P2 | SPEC-7 | Known defects with no tracking |
| P3 | SPEC-6 | Dev environment not usable out of the box |
| P3 | SPEC-8 | Code quality hygiene |
