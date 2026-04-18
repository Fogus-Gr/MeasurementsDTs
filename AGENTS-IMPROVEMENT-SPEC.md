# AGENTS-IMPROVEMENT-SPEC.md (evaluation branch)

Concrete improvements identified after auditing the `evaluation` branch.
Items are ordered by impact. Each entry states the problem, exact location,
and required change.

---

## Audit Summary

### What is good
- Clean evaluator hierarchy: `BaseEvaluator` → `AUCEvaluator` / `APAREvaluator`.
  Adding a new metric follows an obvious pattern.
- `Body` correctly separated into `utils/body.py` — no longer tangled with
  `BaseHPE`.
- `constants.py` centralises COCO visibility flags; used consistently across
  metrics and evaluators.
- `KeypointsDataset` pre-indexes by frame number — O(1) lookup per frame.
- `set_threshold` validates its inputs and raises `ValueError` (not `exit()`).
- Golden tests in `test_auc_integration.py` and `test_apar_integration.py`
  guard against silent regressions in the metric pipeline.
- `2DprojectionPanopticRecordings.py` is a useful offline tool for generating
  GT data from Panoptic Studio recordings.

### What is missing
- No `AGENTS.md` specific to this branch (created in this session).
- `2DprojectionPanopticRecordings.py` has no CLI arguments for `data_path` or
  `selected_cam` — unusable without manual edits.
- No test for `matching.py` confidence-sort behaviour (known divergence from
  COCO spec is undocumented in tests).
- `evaluate.py` has no `--render` guard: passing `--render` without a display
  will crash with a Qt/OpenCV error in headless environments.
- No `requirements.txt` entry for `pytest` or `matplotlib` (needed for tests
  and `draw_curve`).

### What is wrong / risky

1. **`apar_evaluator.py → evaluate_frame` returns a stale scalar** — the
   method returns `oks_score` from the last loop iteration, not a meaningful
   per-frame aggregate. `run_evaluation` in `BaseEvaluator` stores this in
   `evaluation_per_method` and takes a mean over it, producing a meaningless
   number. `APAREvaluator.APAR()` ignores the return value of
   `run_evaluation()` entirely, so this is currently harmless — but it is a
   latent correctness bug and a maintenance trap.

2. **`matching.py` does not sort predictions by confidence** — the module
   docstring acknowledges this divergence from the COCO spec. For AP/AR this
   means the greedy match can pair a low-confidence prediction with a GT body
   before a higher-confidence one gets a chance, inflating FP counts and
   deflating AP.

3. **`keypointsDataset.py` calls `exit(1)` on unknown `fpsType`** — this
   terminates the process instead of raising an exception, making it
   untestable and swallowing the error in any caller that wraps evaluation.

4. **`base_evaluator.py → initialize` calls `exit(1)` on image input** —
   same problem as above.

5. **`evaluate.py → run_default_test` is dead code in production** — the
   function is only triggered when `len(sys.argv) == 1`, hardcodes absolute
   paths (`/mnt/data/...` style via `PROJECT_ROOT`), and is not tested. It
   will silently fail for any user whose paths differ.

6. **`openvino_base_hpe.py → run_model` unbound variable** (inherited from
   `main`) — `results` is only assigned inside `if raw_result:` but read
   unconditionally. Raises `UnboundLocalError` on empty inference.

7. **`export_pose_results.py` global accumulator never reset** (inherited from
   `main`) — module-level lists persist across runs in the same process.

---

## Improvement Specifications

---

### SPEC-1 — Fix `apar_evaluator.py → evaluate_frame` return value

**File:** `utils/accuracyEvaluation/apar_evaluator.py`  
**Method:** `evaluate_frame`

**Problem:** Returns `oks_score` (a scalar from the last loop iteration).
`BaseEvaluator.run_evaluation` accumulates this into `evaluation_per_method`
and computes a mean — a meaningless number for AP/AR.

**Required change:**  
Return a dict of per-method mean OKS for the frame (consistent with how
`AUCEvaluator.evaluate_frame` returns per-method PCK):

```python
def evaluate_frame(self, bodies):
    gt = bodies['ground_truth']
    oks_results = {}

    self.total_gt_count += len(gt)

    for method_name, prediction_bodies in bodies.items():
        if method_name == 'ground_truth':
            continue

        if method_name not in self.all_detections:
            self.all_detections[method_name] = []

        if not gt:
            for pred in prediction_bodies:
                self.all_detections[method_name].append(
                    {'score': pred.score, 'oks': 0.0, 'is_matched': False}
                )
            oks_results[method_name] = 0.0
            continue

        matches = self.matcher.match(gt, prediction_bodies)
        matched_pred_bodies = set()
        frame_oks = []

        for gt_body, pred_body in matches:
            matched_pred_bodies.add(pred_body)
            oks_score, _, _ = self.oks_eval.evaluate(gt_body, pred_body)
            self.all_detections[method_name].append(
                {'score': pred_body.score, 'oks': oks_score, 'is_matched': True}
            )
            pred_body.oks = oks_score
            pred_body.matched = True
            frame_oks.append(oks_score)

        for pred_body in prediction_bodies:
            if pred_body not in matched_pred_bodies:
                self.all_detections[method_name].append(
                    {'score': pred_body.score, 'oks': 0.0, 'is_matched': False}
                )

        oks_results[method_name] = float(np.mean(frame_oks)) if frame_oks else 0.0

    return oks_results
```

---

### SPEC-2 — Sort predictions by confidence before matching

**File:** `utils/accuracyEvaluation/matching.py`  
**Methods:** `_match_iou`, `_match_keypoints`

**Problem:** Greedy matching without confidence sorting diverges from the COCO
spec and can pair low-confidence predictions with GT bodies ahead of
higher-confidence ones, deflating AP.

**Required change:**  
Sort `pred_bodies` by descending score at the start of each match method:

```python
def _match_iou(self, gt_bodies, pred_bodies):
    pred_bodies = sorted(pred_bodies, key=lambda b: b.score, reverse=True)
    # ... rest unchanged

def _match_keypoints(self, gt_bodies, pred_bodies):
    pred_bodies = sorted(pred_bodies, key=lambda b: b.score, reverse=True)
    # ... rest unchanged
```

Add a test in `unit_tests/test_matching.py` that verifies a high-confidence
correct prediction is preferred over a low-confidence one when both overlap
the same GT.

---

### SPEC-3 — Replace `exit(1)` calls with exceptions

**Files:** `utils/accuracyEvaluation/keypointsDataset.py`,
`utils/accuracyEvaluation/base_evaluator.py`

**Problem:** `exit(1)` terminates the process, bypasses exception handling,
and makes the affected code paths untestable.

**`keypointsDataset.py`:**
```python
# Before
print("Exiting... Not handling this ground truth fps")
exit(1)

# After
raise ValueError(f"Unsupported fpsType: '{fpsType}'. Only 'hd_29_97' is supported.")
```

**`base_evaluator.py → initialize`:**
```python
# Before
print("Exiting... Not handling single image")
exit(1)

# After
raise NotImplementedError("Single image input is not supported by the evaluator.")
```

---

### SPEC-4 — Make `2DprojectionPanopticRecordings.py` configurable via CLI

**File:** `utils/accuracyEvaluation/2DprojectionPanopticRecordings.py`

**Problem:** `data_path` and `selected_cam` are hardcoded at the top of the
file. Any user must edit the source to run it.

**Required change:**  
Add `argparse` arguments for the hardcoded values:

```python
parser.add_argument("--data_path", type=str, required=True,
                    help="Path to Panoptic Studio sequence directory")
parser.add_argument("--cam_panel", type=int, default=0)
parser.add_argument("--cam_node",  type=int, default=0)
parser.add_argument("--mode", choices=["single", "multiple"], default="single")
```

Remove the hardcoded `data_path`, `calib_file`, `input_3d_path`, and
`selected_cam` assignments and derive them from `args`.

---

### SPEC-5 — Guard `--render` in headless environments

**File:** `evaluate.py`, `utils/accuracyEvaluation/base_evaluator.py`

**Problem:** `--render` calls `cv2.imshow` and `cv2.waitKey`, which crash with
a Qt/OpenCV error when no display is available (CI, SSH, devcontainer).

**Required change:**  
In `base_evaluator.py → plot_keypoints`, wrap the `cv2.imshow` call:

```python
import os

def plot_keypoints(self, frame, bodies):
    # ... render logic ...
    if os.environ.get('DISPLAY') or os.name == 'nt':
        resized = cv2.resize(frame, (2*640, 2*480))
        cv2.imshow("Frame", resized)
        if cv2.waitKey(0) & 0xFF == ord('q'):
            print("Quitting loop.")
            exit(0)
    else:
        print("[WARN] No display available. Skipping imshow.")
```

---

### SPEC-6 — Remove / isolate `run_default_test` in `evaluate.py`

**File:** `evaluate.py`

**Problem:** `run_default_test` is triggered silently when no CLI args are
given. It hardcodes paths relative to `PROJECT_ROOT` that only work on the
original developer's machine, and it is not covered by any test.

**Required change:**  
Remove `run_default_test` entirely. If a quick smoke-test is needed, add it
as a proper test in `unit_tests/test_auc_integration.py` using the existing
`unit_tests/video2sec/` data. Update `main()` to print help and exit when no
arguments are provided:

```python
def main():
    parser = parse_arguments()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    ...
```

---

### SPEC-7 — Fix inherited P0 bugs from `main` branch

These two bugs exist on `main` and were not fixed before branching.

**SPEC-7a — Unbound variable in `openvino_base_hpe.py → run_model`**

```python
# Before
raw_result = self.model.infer_sync(inputs)
if raw_result:
    results = self.model.postprocess(raw_result, preprocessing_meta)
if results:                          # UnboundLocalError if raw_result falsy
    (poses, scores) = results
return poses

# After
raw_result = self.model.infer_sync(inputs)
if not raw_result:
    return []
results = self.model.postprocess(raw_result, preprocessing_meta)
if not results:
    return []
(poses, scores) = results
return poses
```

**SPEC-7b — Global accumulator never reset in `export_pose_results.py`**

Call `reset_results()` at the start of `BaseHPE.main_loop()`:

```python
from utils.export_pose_results import reset_results

def main_loop(self):
    reset_results()
    frame_number = 0
    ...
```

---

### SPEC-8 — Add `pytest` and `matplotlib` to `requirements.txt`

**File:** `requirements.txt`

**Problem:** `pytest` is needed to run `unit_tests/`. `matplotlib` is needed
by `utils/accuracyEvaluation/metrics/pck.py → draw_curve`. Neither is listed.

**Required change:**
```
pytest>=7.0
matplotlib==3.7.5
```

---

## Priority Order

| Priority | Spec | Reason |
|---|---|---|
| P0 | SPEC-7a | Runtime crash on empty OpenVINO inference |
| P0 | SPEC-7b | Silent data corruption across HPE runs |
| P1 | SPEC-1 | `evaluate_frame` returns wrong value; latent correctness bug |
| P1 | SPEC-2 | AP/AR diverges from COCO spec; results are not comparable |
| P1 | SPEC-3 | `exit(1)` makes error paths untestable; breaks any caller |
| P2 | SPEC-4 | `2DprojectionPanopticRecordings.py` unusable without source edits |
| P2 | SPEC-5 | `--render` crashes in headless CI/devcontainer |
| P2 | SPEC-6 | Silent default behaviour in `evaluate.py` is confusing and fragile |
| P3 | SPEC-8 | Missing dev dependencies block running tests out of the box |
