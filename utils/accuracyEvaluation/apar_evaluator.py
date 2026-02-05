from .base_evaluator import BaseEvaluator
from utils.accuracyEvaluation.metrics.oks import OKSEvaluator
import numpy as np

class APAREvaluator(BaseEvaluator):
    def __init__(self, start_threshold = 0.5, stop_threshold  = 0.95, step_threshold  = 0.05, **kwargs): 
        super().__init__(**kwargs, confidence_threshold = 0.0)
        
        self.oks_eval = None
        self.set_threshold(start_threshold, stop_threshold, step_threshold)

        # Structure: {'MethodName': [{'score': 0.9, 'oks': 0.85}, ...]}
        self.all_detections = {} 
        self.total_gt_count = 0 

    def initialize(self):
        super().initialize()

        self.oks_eval = OKSEvaluator()

        return self


    def evaluate_frame(self, bodies):
        gt = bodies['ground_truth']
        oks_results = {}

        # 1. Count Ground Truths (Needed for Recall calculation later)
        # We count every GT body, even if it wasn't matched.
        self.total_gt_count += len(gt)

        for method_name, prediction_bodies in bodies.items():
            if method_name == 'ground_truth':
                continue

            # Ensure the list exists in our storage
            if method_name not in self.all_detections:
                self.all_detections[method_name] = []

            # Handle empty GT case (All predictions are False Positives)
            if not gt:
                for pred in prediction_bodies:
                     self.all_detections[method_name].append({
                        'score': pred.score,
                        'oks': 0.0, # No GT to match against
                        'is_matched': False # This can be seen in OKS also, since OKS = 0 -> unmatched, OKS~0 -> super bad prediction
                    })
                continue

            # 2. Run Matching
            matches = self.matcher.match(gt, prediction_bodies)

            # Keep track of which GT bodies were matched so we can find the missed ones
            matched_gt_bodies = set()
            matched_pred_bodies = set()

            # --- PART 1: Process Matches (Potential True Positives)---
            for gt_body, pred_body in matches:
                matched_gt_bodies.add(gt_body)
                matched_pred_bodies.add(pred_body)

                # oks is per-instance not per-keypoint metric
                oks_score, _, _ = self.oks_eval.evaluate(gt_body, pred_body)

                # Before adding to all_detections update pred_body.score, to be the mean for only visible(gt_truth) keypoints
                # pred_body.score = np.mean(pred_body.keypoints_score[gt_body.keypoints_score == 2])
                # The above can be considered cheating, so we can simple take into account of the mean only keypoints_score > 0.1 for example

                self.all_detections[method_name].append({
                    'score': pred_body.score,   # Model confidence
                    'oks': oks_score,           # Geometric accuracy
                    'is_matched': True          # It found a partner
                })

                pred_body.oks = oks_score
                pred_body.matched = True

            # --- PART 2: Process Unmatched Predictions (False Positives) ---
            # These are predictions that the Matcher couldn't pair with any GT
            # (e.g., they were too far away or the GT was already taken)
            for pred_body in prediction_bodies:
                if pred_body not in matched_pred_bodies:
                    self.all_detections[method_name].append({
                        'score': pred_body.score,
                        'oks': 0.0,             # Effectively 0 since it didn't match
                        'is_matched': False
                    })
            
            # Note: We do NOT need to explicitly loop over "Missed GT" here.
            # Missed GTs are accounted for by 'self.total_gt_count' acting as the
            # denominator in the Recall calculation later.

            oks_results[method_name] = oks_score

        return oks_results
    
    def print_results(self, frame_number, oks_results):
        oks_str = ""
        if oks_results:
            oks_str = "=> "
            oks_str += ", ".join([f"{method}: {oks:.2f}" for method, oks in oks_results.items()])
        print(f"Frame {frame_number} {oks_str}")

        
    def count_TP_FP_FN(self, threshold, detections):
        """
        Loops through all confidences for a single threshold value:
           Case       - is_matched - oks >= t - Result
        correct pose  -     True   -   True   -   TP
        bad localized -     True   -   False  -   FP
        ghost person  -     False  -     -    -   FP  
        """
        scores = np.array([d['score'] for d in detections])
        unique_scores = np.sort(np.unique(scores))[::-1]

        results = {}

        for conf_threshold in unique_scores:
            # Keep only detections above this confidence
            filtered_detections = [d for d in detections if d['score'] >= conf_threshold]

            TP_count = FP_count = 0   
            for det in filtered_detections:
                if det['is_matched'] and det['oks'] >= threshold:  # det['is_matched'] can be removed since OKS > 0 means is_matched = True
                    TP_count += 1
                else:
                    FP_count += 1

            FN_count = self.total_gt_count - TP_count

            precision = TP_count / (TP_count + FP_count) if TP_count + FP_count > 0 else 0.0
            recall    = TP_count / self.total_gt_count   if self.total_gt_count > 0 else 0.0   # TP_count / (TP_count + FN_count)

            results[conf_threshold] = {
                'TP': TP_count,
                'FP': FP_count,
                'FN': FN_count,
                'precision': precision,
                'recall': recall
            }

        return results

    def compute_ap(self, recall_list, precision_list):
        """
        Computes Area Under the Precision-Recall Curve (AP) using 
        COCO 101-Point Interpolation.
        """
        if not recall_list:
            return 0.0

        # 1. Sort by Recall
        # (We need the curve to go from low recall to high recall for integration)
        sorted_pairs = sorted(zip(recall_list, precision_list), key=lambda x: x[0])
        recalls, precisions = zip(*sorted_pairs)
        
        # Convert to numpy for easy manipulation
        mrec = np.concatenate(([0.0], recalls, [1.0]))
        mpre = np.concatenate(([0.0], precisions, [0.0]))

        # 2. Compute the Precision Envelope (Smoothing)
        # Make precision monotonically decreasing. 
        # For any recall r, the precision is the max precision for any r' >= r.
        for i in range(len(mpre) - 2, -1, -1):
            mpre[i] = max(mpre[i], mpre[i + 1])

        # 4. COCO 101-Point Sampling
        # Instead of calculating the geometric area, we average precision
        # at 101 fixed recall thresholds: 0.00, 0.01, ..., 1.00
        recall_thresholds = np.linspace(0.0, 1.0, 101)
        
        # np.searchsorted finds the indices in 'mrec' where the thresholds fit.
        # This effectively looks up the smoothed precision for every 0.01 step.
        inds = np.searchsorted(mrec, recall_thresholds, side='left')
        
        # 3. Integrate (Sum of rectangular areas)
        # We calculate area only where recall changes
        # this is PASCAL VOC (2010+) method
        '''i = np.where(mrec[1:] != mrec[:-1])[0]
        ap = np.sum((mrec[i + 1] - mrec[i]) * mpre[i + 1])
        return = ap'''

        # Average the values
        return np.mean(mpre[inds])


    def APAR(self):
        # Run once to get all OKS values
        self.run_evaluation()

        final_metrics = {}
        results_per_threshold = {}

        for method, detections in self.all_detections.items():
            # Sort by confidence
            detections = sorted(detections, key=lambda x: x['score'], reverse=True)

            results_per_threshold[method] = {}
            ap_per_threshold = []
            ar_per_threshold = []

            for t in self.thresholds:
                # Calculate
                t_results = self.count_TP_FP_FN(t, detections)

                precisions = [metrics['precision'] for metrics in t_results.values()]
                recalls = [metrics['recall'] for metrics in t_results.values()]

                ap = self.compute_ap(recalls, precisions)
                max_recall = max(recalls) if recalls else 0.0

                # Save
                results_per_threshold[method][t] = t_results
                ap_per_threshold.append(ap)
                ar_per_threshold.append(max_recall)

            # --- Average them out (mAP and mAR) ---
            final_metrics[method] = {
                'mAP': np.mean(ap_per_threshold),                       # Averaged over thresholds .50:.05:.95
                'mAR': np.mean(ar_per_threshold),                       # Averaged over thresholds .50:.05:.95
                'results_per_threshold': results_per_threshold[method], # Optional: for debugging
                'ap_per_threshold': ap_per_threshold                    # Optional: for debugging
            }

        return final_metrics
