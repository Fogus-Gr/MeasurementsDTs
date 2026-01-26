from .base_evaluator import BaseEvaluator
from utils.accuracyEvaluation.metrics.pck import PCKEvaluator, draw_curve
from utils.constants import LABELED_VISIBLE
import numpy as np

class AUCEvaluator(BaseEvaluator):
    def __init__(self, start_threshold = 0, stop_threshold  = 0.5, step_threshold  = 0.01, **kwargs):
        super().__init__(**kwargs)
        
        self.pck_eval = None

        self.set_threshold(start_threshold, stop_threshold, step_threshold)

    def initialize(self):
        super().initialize()

        self.pck_eval = PCKEvaluator(threshold_type="torso", alpha=self.start_threshold)

        return self


    def evaluate_frame(self, bodies):
        gt = bodies['ground_truth']
        pck_results = {}

        for method_name, prediction_bodies in bodies.items():
            if method_name == 'ground_truth':
                continue

            if not gt:
                continue

            matches = self.matcher.match(gt, prediction_bodies)

            # Keep track of which GT bodies were matched so we can find the missed ones
            matched_gt_bodies = set()

            TP_count = 0
            GT_visible_count = 0

            # --- PART 1: Process Matches ---
            for gt_body, pred_body in matches:
                matched_gt_bodies.add(gt_body)

                _, correctness, included_in_denominator = self.pck_eval.evaluate(gt_body, pred_body)
                pred_body.correctness = correctness
                pred_body.included_in_denominator = included_in_denominator
                TP_count += np.sum(correctness[included_in_denominator])
                GT_visible_count += np.sum(included_in_denominator)

            # --- PART 2: Process Missed GT (FN) ---
            for body in gt:
                if body not in matched_gt_bodies:                   
                    visible_kpts = np.sum(body.keypoints_score == LABELED_VISIBLE)
                    GT_visible_count += visible_kpts
                
            pck_results[method_name] = TP_count / GT_visible_count if GT_visible_count > 0 else 0.0

        return pck_results
    
    def print_results(self, frame_number, pck_results):
        pck_str = ""
        if pck_results:
            pck_str = "=> "
            pck_str += ", ".join([f"{method}: {pck:.2f}" for method, pck in pck_results.items()])
        print(f"Frame {frame_number} {pck_str}")

    def AUC(self):
        pck_values = []

        for t in self.thresholds:
            print(f"PCK_threshold: {t}")
            self.pck_eval.set_alpha(t)

            mean_dict = self.run_evaluation()
            pck_values.append(mean_dict)
            print(f"PCK = {mean_dict}")

        print("Final stats:")
        print(self.thresholds)
        print(pck_values)
        
        auc_scores = {}

        methods = pck_values[0].keys()
        for method in methods:
            pck_numeric = np.array([d[method] for d in pck_values])

            if len(self.thresholds) == 1:   # Single threshold
                auc = pck_numeric[0]
            else:
                x_range = self.stop_threshold - self.start_threshold
                auc_raw = np.trapz(pck_numeric, self.thresholds)
                auc = auc_raw / x_range

            # Formula: PCK = sum(pck_i, pck_i+1)/2 * step_size
            # PCK_normal = PCK / range
            print(f"AUC ({method}) = {auc}")
            auc_scores[method] = auc

        draw_curve(pck_values, self.thresholds)

        return auc_scores, pck_values, self.thresholds