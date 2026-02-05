import numpy as np
from utils.constants import LABELED_VISIBLE

class OKSEvaluator:
    def __init__(self):
        # COCO person keypoint constants (17 keypoints)
        self.k = np.array([.026, .025, .025, .035, .035, .079, .079, .072, .072, .062, .062, .107, .107, .087, .087, .089, .089])
        self.k_squared = self.k ** 2

    # Segmentation Mask approximation => s = bounding_box^(1/2)
    # returns s^2
    def _get_scale_squared(self, gt_kpts):
        # Check for points that are NOT (0,0)
        # Even if visibility is 0, if the coord is real, we want to use it.
        # But if the coord is (0,0), it ruins the min/max calculation.
        has_coords = np.any(gt_kpts > 0, axis=1) 
        
        # Fallback if NO points have coordinates (empty GT)
        if not np.any(has_coords):
             return 1.0

        valid_kpts = gt_kpts[has_coords]

        x_coords = valid_kpts[:, 0]
        y_coords = valid_kpts[:, 1]

        width  = x_coords.max() - x_coords.min()
        height = y_coords.max() - y_coords.min()

        s_squared = width * height

        return max(s_squared, 1e-6)
    
    # iou = exp(-||d||^2 /2 s^2 k^2)
    def _get_IoU(self, gt_kpts, pred_kpts, s_squared):
        d = np.linalg.norm(gt_kpts - pred_kpts, axis=1)

        oks_per_keypoint = np.exp(-(d**2) / (2 * s_squared * self.k_squared))

        return oks_per_keypoint

    def evaluate(self, gt_body, pred_body):
        gt_kpts = gt_body.keypoints
        gt_v    = gt_body.keypoints_score
        pred_kpts   = pred_body.keypoints
        pred_scores = pred_body.keypoints_score

        is_visible      = (gt_v == LABELED_VISIBLE)
        not_predicted   = (pred_scores == 0)

        # Handle visible points
        s_squared = self._get_scale_squared(gt_kpts)
        ks_per_keypoint = self._get_IoU(gt_kpts, pred_kpts, s_squared)

        # Handle out-of-border points: exclude from calculation
        # Handle visible but not predicted: score = 0 <- Since COCO doesn't do that and actually calculates we left it out, even it will be ~0
        #false_negatives = is_visible & not_predicted
        #ks_per_keypoint[false_negatives] = 0

        if np.any(is_visible):
            OKS = np.mean(ks_per_keypoint[is_visible])
        else:
            OKS = 0.0

        return OKS, ks_per_keypoint, is_visible