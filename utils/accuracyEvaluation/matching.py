"""
Confidence threshold should be already be applied => conf == 0 -> not counted as valid

Note:
for method == "keypoint", gt.keypoints_norm is used which are keypoints / np.array([img_w, img_h])
=> dist_thresh represents a Normalized Euclidean Distance (=> 5% of the image dimensions)
"""

import numpy as np
from utils.constants import LABELED_VISIBLE

class Matcher:
    def __init__(self, method="iou", iou_thresh=0.3, dist_thresh=0.05, min_common_kpts=4):
        self.method = method
        self.iou_thresh = iou_thresh
        self.dist_thresh = dist_thresh
        self.min_common_kpts = min_common_kpts  # New parameter

    def match(self, gt_bodies, pred_bodies):
        if self.method == "iou":
            return self._match_iou(gt_bodies, pred_bodies)
        elif self.method == "keypoint":
            return self._match_keypoints(gt_bodies, pred_bodies)
        else:
            raise ValueError(f"Unknown matching method: {self.method}")
        
    def _find_common_existant_kpts(self, gt_scores, pd_scores):
        gt_valid_mask = gt_scores == LABELED_VISIBLE
        pred_valid_mask = pd_scores > 0
                
        # 1. Find common visible keypoints
        common_mask = gt_valid_mask & pred_valid_mask
        num_common = np.sum(common_mask)

        # 2. Enforce Minimum Keypoints Check
        if num_common < self.min_common_kpts:
            return None
        
        return common_mask

    def _match_iou(self, gt_bodies, pred_bodies):
        matches = []
        used_pred = set()
        for gt in gt_bodies:
            best_iou = 0
            best_pred = None
            for i, pred in enumerate(pred_bodies):
                if i in used_pred:
                    continue

                # If they don't share enough keypoints, skip this specific pairing
                common_mask = self._find_common_existant_kpts(gt.keypoints_score, pred.keypoints_score)
                if common_mask is None:
                    continue

                xA = max(gt.xmin, pred.xmin)
                yA = max(gt.ymin, pred.ymin)
                xB = min(gt.xmax, pred.xmax)
                yB = min(gt.ymax, pred.ymax)
                interArea = max(0, xB - xA) * max(0, yB - yA)
                boxAArea = (gt.xmax - gt.xmin) * (gt.ymax - gt.ymin)
                boxBArea = (pred.xmax - pred.xmin) * (pred.ymax - pred.ymin)
                
                # Prevent division by zero
                union = boxAArea + boxBArea - interArea
                if union <= 0: continue

                iou = interArea / union
                if iou > best_iou:
                    best_iou = iou
                    best_pred = i

            if best_iou > self.iou_thresh and best_pred is not None:
                matches.append((gt, pred_bodies[best_pred]))
                used_pred.add(best_pred)
        return matches

    def _match_keypoints(self, gt_bodies, pred_bodies):
        matches = []
        used_pred = set()
        for gt in gt_bodies:
            best_dist = float("inf")
            best_pred = None
            for i, pred in enumerate(pred_bodies):
                if i in used_pred:
                    continue

                common_mask = self._find_common_existant_kpts(gt.keypoints_score, pred.keypoints_score)
                if common_mask is None:
                    continue

                # 3. Calculate distance ONLY on common keypoints
                dists = np.linalg.norm(gt.keypoints_norm[common_mask] - pred.keypoints_norm[common_mask], axis=1)
                mean_dist = np.mean(dists)

                if mean_dist < best_dist:
                    best_dist = mean_dist
                    best_pred = i
            
            if best_dist < self.dist_thresh and best_pred is not None:
                matches.append((gt, pred_bodies[best_pred]))
                used_pred.add(best_pred)
        return matches
