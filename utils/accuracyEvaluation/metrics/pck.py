'''
PCK = (Number of keypoints in the threshold) / (Number of total keypoints)

For NOT_LABELED (out_of_border):
ignore it => remove from denominator
'''

import numpy as np
import matplotlib.pyplot as plt
from utils.constants import NOT_LABELED

class PCKEvaluator:
    def __init__(self, threshold_type="torso", alpha=0.2):
        self.threshold_type = threshold_type
        self.set_alpha(alpha)
        
    def set_alpha(self, alpha: float):
        if not isinstance(alpha, (int, float)):
            raise ValueError("confidence_threshold (alpha) must be numeric")

        if alpha < 0 or alpha > 1:
            raise ValueError("confidence_threshold (alpha) must be in [0,1]")
        
        self.alpha = alpha

    def _get_norm_dist(self, gt_kpts):
        dist = 0.0 

        if self.threshold_type == "torso":
            dist = np.linalg.norm(gt_kpts[5] - gt_kpts[12]) # Shoulder L - Hips R
        elif self.threshold_type == "head":
            dist = np.linalg.norm(gt_kpts[3] - gt_kpts[4])  # Ear L - Ear R
        else:
            raise ValueError("Invalid threshold_type")
        
        return max(dist, 1.0) # Ensure we never return 0
        
    def compute_thresholds(self, gt_body):
        """
        Computes the pixel radius for the threshold circle for every keypoint.
        Returns a numpy array of shape (N,).
        """
        norm_dist = self._get_norm_dist(gt_body.keypoints)
        radius_pixels = self.alpha * norm_dist
        
        # For PCK, the radius is uniform for all keypoints.
        return np.full(len(gt_body.keypoints), radius_pixels)

    def evaluate(self, gt_body, pred_body):
        gt_kpts = gt_body.keypoints
        pred_kpts = pred_body.keypoints
        gt_v = gt_body.keypoints_score
        pred_scores = pred_body.keypoints_score

        # 1. Standardize Visibility
        # GT Visible (v>0) are the ones we MUST recall.
        is_visible = (gt_v != NOT_LABELED)
        
        # 2. Calculate Thresholds
        gt_body.thresh_radius = self.compute_thresholds(gt_body)

        thresholds = gt_body.thresh_radius
        dists = np.linalg.norm(gt_kpts - pred_kpts, axis=1)

        # 3. Calculate Correctness
        correctness = np.zeros_like(dists, dtype=bool)
        
        # Check A: Distance is within threshold
        spatially_correct = dists <= thresholds
        
        # Check B: Prediction actually exists (Score > 0 or Conf Thresh)
        is_predicted = pred_scores > 0 
        
        # Combine: Must be Visible + Spatially Close + Predicted
        correctness[is_visible] = spatially_correct[is_visible] & is_predicted[is_visible]
        
        # --- Denominator ---
        # Denominator = All Visible GT
        included_in_denominator = is_visible
        
        if np.sum(included_in_denominator) > 0:
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
