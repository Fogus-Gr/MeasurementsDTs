import numpy as np

class Matcher:
    def __init__(self, method="iou", iou_thresh=0.3, dist_thresh=0.05):
        self.method = method
        self.iou_thresh = iou_thresh
        self.dist_thresh = dist_thresh

    def match(self, gt_bodies, pred_bodies):
        if self.method == "iou":
            return self._match_iou(gt_bodies, pred_bodies)
        elif self.method == "keypoint":
            return self._match_keypoints(gt_bodies, pred_bodies)
        else:
            raise ValueError(f"Unknown matching method: {self.method}")

    def _match_iou(self, gt_bodies, pred_bodies):
        matches = []
        used_pred = set()
        for gt in gt_bodies:
            best_iou = 0
            best_pred = None
            for i, pred in enumerate(pred_bodies):
                if i in used_pred:
                    continue
                xA = max(gt.xmin, pred.xmin)
                yA = max(gt.ymin, pred.ymin)
                xB = min(gt.xmax, pred.xmax)
                yB = min(gt.ymax, pred.ymax)
                interArea = max(0, xB - xA) * max(0, yB - yA)
                boxAArea = (gt.xmax - gt.xmin) * (gt.ymax - gt.ymin)
                boxBArea = (pred.xmax - pred.xmin) * (pred.ymax - pred.ymin)
                iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
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
                dists = np.linalg.norm(gt.keypoints_norm - pred.keypoints_norm, axis=1)
                mean_dist = np.mean(dists)
                if mean_dist < best_dist:
                    best_dist = mean_dist
                    best_pred = i
            if best_dist < self.dist_thresh and best_pred is not None:
                matches.append((gt, pred_bodies[best_pred]))
                used_pred.add(best_pred)
        return matches
