'''
PCK = (Number of keypoints in the threshold) / (Number of total keypoints)

For LABELED_NOT_VISIBLE (out_of_border):
If model predicts something => treat like a normal keypoint => compare distance to threshold
If model does NOT predict (score = 0) => ignore it => remove from denominator
'''

import numpy as np
import matplotlib.pyplot as plt
from utils.constants import LABELED_VISIBLE, LABELED_NOT_VISIBLE

class PCKEvaluator:
    def __init__(self, threshold_type="torso", alpha=0.2):
        self.threshold_type = threshold_type
        self.alpha = alpha

    def _get_norm_dist(self, gt_kpts):
        if self.threshold_type == "torso":
            return np.linalg.norm(gt_kpts[5] - gt_kpts[12]) # Shoulder L - Hips R
        elif self.threshold_type == "head":
            return np.linalg.norm(gt_kpts[3] - gt_kpts[4])  # Ear L - Ear R
        else:
            raise ValueError("Invalid threshold_type")

    def evaluate(self, gt_body, pred_body):
        gt_kpts = gt_body.keypoints
        pred_kpts = pred_body.keypoints
        gt_v = gt_body.keypoints_score

        is_visible = (gt_v == LABELED_VISIBLE)
        out_of_border = (gt_v == LABELED_NOT_VISIBLE)

        norm_dist = self._get_norm_dist(gt_kpts)
        threshold = self.alpha * norm_dist

        dists = np.linalg.norm(gt_kpts - pred_kpts, axis=1)

        correctness = np.zeros_like(dists, dtype=bool)
        
        # Handle visible points: check distance
        correctness[is_visible] = dists[is_visible] <= threshold
        
        # Handle out-of-border points:
        # - If predicted (score != 0), check if prediction is reasonable
        # - If not predicted (score == 0), exclude from calculation
        out_of_border_predicted = out_of_border & (pred_body.keypoints_score != 0)
                
        # Treat predicted out-of-border keypoints like visible ones
        correctness[out_of_border_predicted] = dists[out_of_border_predicted] <= threshold
        
        # Create mask for keypoints that should be included in denominator
        # Include: visible points + out-of-border points that were predicted
        included_in_denominator = is_visible | out_of_border_predicted
        
        if np.any(included_in_denominator):
            pck = np.mean(correctness[included_in_denominator])
        else:
            pck = 0.0

        return pck, correctness, included_in_denominator
    
"""
Draws PCK vs Threshold curve.
Args:
    pck_values: list or np.array of mean PCK for each threshold
    thresholds: list or np.array of thresholds
    title: plot title
    save_path: optional, save the figure to this path
"""
def draw_curve(pck_values, thresholds, title="PCK Curve", save_path=None):
    plt.figure(figsize=(6, 4))

    methods = pck_values[0].keys()  # e.g., ['MoveNet', 'AnotherMethod']
    for method in methods:
        method_pck = [d[method] for d in pck_values]
        plt.plot(thresholds, method_pck, marker='o', label=method)

    plt.xlabel("Threshold (alpha * norm_dist)")
    plt.ylabel("Mean PCK")
    plt.title(title)
    plt.grid(True)
    plt.ylim(0, 1.05)
    plt.xlim(min(thresholds), max(thresholds))
    plt.legend()

    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=150)
        print(f"Curve saved to {save_path}")
    plt.show()
