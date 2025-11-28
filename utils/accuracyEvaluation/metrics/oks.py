import numpy as np
from utils.constants import LABELED_VISIBLE, LABELED_NOT_VISIBLE

class OKSEvaluator:
    def __init__(self, confidence_threshold):
        if not isinstance(confidence_threshold, (int, float)):
            raise ValueError("confidence_threshold must be numeric")

        if confidence_threshold < 0 or confidence_threshold > 1:
            raise ValueError("confidence_threshold must be in [0,1]")
        
        self.confidence_threshold = confidence_threshold

        # COCO person keypoint constants (17 keypoints)
        self.k = np.array([.026, .025, .025, .035, .035, .079, .079, .072, .072, .062, .062, .107, .107, .087, .087, .089, .089])
        self.k_squared = self.k ** 2

    # Segmentation Mask approximation => s = bounding_box^(1/2)
    # returns s^2
    def _get_scale_squared(self, gt_kpts):
        x_coords = gt_kpts[:, 0]
        y_coords = gt_kpts[:, 1]

        # TODO - maybe using invalid points? - check
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
        out_of_border   = (gt_v == LABELED_NOT_VISIBLE)

        # apply confidence threshold to predicted kpts
        pred_scores[pred_scores < self.confidence_threshold] = 0.0

        # replace suppressed predictions with GT coords (infinite distance otherwise)
        pred_kpts[pred_scores == 0] = gt_kpts[pred_scores == 0] 

        # Handle visible points
        s_squared = self._get_scale_squared(gt_kpts)
        ks_per_keypoint = self._get_IoU(gt_kpts, pred_kpts, s_squared)

        # Handle out-of-border points:
        # - If predicted (score != 0), check if prediction is reasonable (like visible ones)
        # - If not predicted (score == 0), exclude from calculation

         # Out-of-border but predicted (score != 0)
        out_of_border_predicted = out_of_border & (pred_scores != 0)

        # OKS denominator should include:
        # - visible points
        # - occluded but predicted points
        included = is_visible | out_of_border_predicted

        if np.any(included):
            OKS = np.mean(ks_per_keypoint[included])
        else:
            OKS = 0.0

        return OKS, ks_per_keypoint, included