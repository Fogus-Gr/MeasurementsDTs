from .base_evaluator import BaseEvaluator
from utils.accuracyEvaluation.metrics.pck import PCKEvaluator, draw_curve
import numpy as np

class AUCEvaluator(BaseEvaluator):
    def __init__(self, pck_alpha_threshold = 0.2, start_threshold = 0, stop_threshold  = 0.5, step_threshold  = 0.01, **kwargs):
        super().__init__(**kwargs)

        self.pck_alpha_threshold = pck_alpha_threshold
        self.start_threshold = start_threshold
        self.stop_threshold = stop_threshold
        self.step_threshold = step_threshold
        
        self.thresholds = np.arange(self.start_threshold, 
                                   self.stop_threshold + 1e-10,  # Small epsilon
                                   self.step_threshold)
        
        self.pck_eval = None

    def initialize(self):
        super().initialize()

        self.pck_eval = PCKEvaluator(threshold_type="torso", alpha=self.pck_alpha_threshold)

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
            pck_values = []

            for gt_body, pred_body in matches:
                pck, correctness, _ = self.pck_eval.evaluate(gt_body, pred_body)
                pred_body.correctness = correctness
                pck_values.append(pck)
                
            pck_results[method_name] = np.mean(pck_values) if pck_values else 0.0

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
        
        methods = pck_values[0].keys()
        for method in methods:
            pck_numeric = np.array([d[method] for d in pck_values])
            auc = (1 / (self.stop_threshold - self.start_threshold)) * np.sum(pck_numeric) * self.step_threshold
            print(f"AUC ({method}) = {auc}")

        draw_curve(pck_values, self.thresholds)

        return