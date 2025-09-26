import numpy as np

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

    # pck = (Number of keypoints in the threshold) / (Number of total keypoints)
    def evaluate(self, gt_kpts, pred_kpts):
        norm_dist = self._get_norm_dist(gt_kpts)
        threshold = self.alpha * norm_dist

        dists = np.linalg.norm(gt_kpts - pred_kpts, axis=1)
        valid = ~np.isnan(dists)
        
        correctness = np.zeros_like(dists, dtype=bool)
        correctness[valid] = dists[valid] <= threshold

        pck = np.mean(correctness[valid]) if np.any(valid) else 0.0

        return pck, correctness
