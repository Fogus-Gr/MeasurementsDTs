"""
Integration tests for APAREvaluator mirroring the AUCEvaluator structure
"""
import unittest
import os
import json
import tempfile
import numpy as np
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAPAREvaluatorIntegration(unittest.TestCase):
    """Integration tests for AP/AR Evaluator"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data paths (using the same 2s video data as AUC)"""
        cls.test_dir = os.path.join(os.path.dirname(__file__), '..', 'unit_tests')
        
        # Expected test files (Reusing the ones from your AUC tests)
        cls.video_path = os.path.join(cls.test_dir, 'video2sec', '160422_ultimatum_hd_00_00_2s.mp4')
        cls.gt_path = os.path.join(cls.test_dir, 'video2sec', 'all_body2DScenes_499_540.json')
        cls.pred_path = os.path.join(cls.test_dir, 'video2sec', 'pd_movenet.json')
        
        # Check if test data exists
        cls.has_test_data = all(
            os.path.exists(p) for p in [cls.video_path, cls.gt_path, cls.pred_path]
        )
        
        if not cls.has_test_data:
            print(f"   Test data not found. Skipping integration tests.")

    def setUp(self):
        if not self.has_test_data:
            self.skipTest("Test data not available")
        
        from utils.accuracyEvaluation.apar_evaluator import APAREvaluator
        self.APAREvaluator = APAREvaluator

    # ------------------------------------------------------------------------
    # Tier 1 - Smoke Tests
    # ------------------------------------------------------------------------
    def test_01_smoke_test_initialization(self):
        """Smoke Test: Basic initialization"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=os.path.join(self.test_dir, "output.jpg"),
            verbose=False
        )
        
        self.assertIsNotNone(evaluator)
        try:
            evaluator.initialize()
            self.assertIsNotNone(evaluator.ground_truth)
            self.assertGreater(len(evaluator.predictions), 0)

            # Ensure OKS evaluator is loaded
            self.assertIsNotNone(evaluator.oks_eval)
        except Exception as e:
            self.fail(f"initialize() crashed: {e}")


    def test_02_smoke_test_single_frame_evaluation(self):
        """Smoke Test: Run logic on a single frame"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            frame_number_offset=499,
            singleFrameFromVideo=10,
            render_out=False,
            verbose=False
        )
        evaluator.initialize()
        
        try:
            # Note: APAR usually collects data in run_evaluation and calculates at the end
            results = evaluator.run_evaluation()
            
            # Check if internal storage has data
            # Basic sanity check on result
            self.assertIn("MoveNet", results)
            if "MoveNet" in results:
                self.assertIn("MoveNet", evaluator.all_detections)
                self.assertGreater(len(evaluator.all_detections["MoveNet"]), 0)
                self.assertGreater(evaluator.total_gt_count, 0)
        except Exception as e:
            self.fail(f"run_evaluation() crashed: {e}")

    def test_02_smoke_test_all_frames_evaluation(self):
        """Smoke Test: All frames"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            frame_number_offset=499,
            singleFrameFromVideo=-1,  # All frames
            render_out=False,
            verbose=False
        )

        evaluator.initialize()
        
        try:
            result = evaluator.run_evaluation()
            
            # Basic sanity check
            self.assertIn("MoveNet", result)
            if "MoveNet" in result:
                oks = result["MoveNet"]
                self.assertGreaterEqual(oks, 0.0)
                self.assertLessEqual(oks, 1.0)
        except Exception as e:
            self.fail(f"run_evaluation() crashed: {e}")

        
    def test_02_smoke_test_all_frames_APAR(self):
        """Smoke Test: Full APAR pipeline on all frames (no rendering)"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=os.path.join(self.test_dir, "auc_output.jpg"),
            start_threshold=0.5,
            stop_threshold=0.7,
            step_threshold=0.1,
            frame_number_offset=499,
            singleFrameFromVideo=-1,
            render_out=False,
            verbose=False
        )

        evaluator.initialize()

        
        results = evaluator.APAR()

        # Check that it ran through all thresholds
        self.assertEqual(3, len(results["MoveNet"]["ap_per_threshold"]))
        self.assertIn(0.5, results["MoveNet"]["results_per_threshold"])
        self.assertIn(0.6, results["MoveNet"]["results_per_threshold"])
        self.assertIn(0.7, results["MoveNet"]["results_per_threshold"])

    # ------------------------------------------------------------------------
    # Tier 2 - Functional Tests (Logic & Math)
    # ------------------------------------------------------------------------

    def test_03_threshold_calculation_regular(self):
        """Test that thresholds are calculated correctly with floating-point safety"""
        test_cases = [
            (0.1, 0.3, 0.1, [0.1, 0.2, 0.3]),
            (0.0, 0.5, 0.1, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]),
            (0.0, 1.0, 0.25, [0.0, 0.25, 0.5, 0.75, 1.0]),
        ]
        
        for start, stop, step, expected in test_cases:
            evaluator = self.APAREvaluator(
                ground_truth_file=self.gt_path,
                predictions_file_list={"MoveNet": self.pred_path},
                input_src=self.video_path,
                start_threshold=start,
                stop_threshold=stop,
                step_threshold=step,
                render_out=False,
                verbose=False
            )
      
            np.testing.assert_array_almost_equal(evaluator.thresholds, expected, 
                                            err_msg=f"Failed for start={start}, stop={stop}, step={step}")
            
    def test_03_threshold_single_value(self):
        """Edge Case Test: Handling single value"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            render_out=False,
            verbose=False
        )

        evaluator.set_threshold(0.25, 0.25, 0.1)

        self.assertEqual(len(evaluator.thresholds), 1)
        self.assertAlmostEqual(evaluator.thresholds[0], 0.25)


    def test_03_threshold_invalid_step(self):
        """Edge Case Test: Handling invalid thresholds step"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            render_out=False,
            verbose=False
        )

        for invalid_step in [0, -0.1]:
            with self.assertRaises(ValueError):
                evaluator.set_threshold(0.0, 0.5, invalid_step)

    
    def test_03_threshold_invalid(self):
        """Edge Case Test: Handling invalid thresholds"""
        for invalid_threshold in [-0.5, 1.3]:
            with self.assertRaises(ValueError):
                evaluator = self.APAREvaluator(
                    start_threshold=invalid_threshold,
                    stop_threshold=0.8,
                    ground_truth_file=self.gt_path,
                    predictions_file_list={"MoveNet": self.pred_path},
                    input_src=self.video_path,
                    render_out=False,
                    verbose=False
                )

            with self.assertRaises(ValueError):
                evaluator = self.APAREvaluator(
                    start_threshold=0.1,
                    stop_threshold=invalid_threshold,
                    ground_truth_file=self.gt_path,
                    predictions_file_list={"MoveNet": self.pred_path},
                    input_src=self.video_path,
                    render_out=False,
                    verbose=False
                )

    
    def test_03_threshold_start_greater_than_stop(self):
        """Edge Case Test: Handling invalid thresholds"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            render_out=False,
            verbose=False
        )

        with self.assertRaises(ValueError):
            evaluator.set_threshold(0.5, 0.1, 0.1)

    def test_03_threshold_generation_coco_standard(self):
        """Functional Test: Verify standard COCO thresholds (0.50:0.05:0.95)"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            start_threshold=0.5,
            stop_threshold=0.95,
            step_threshold=0.05,
            render_out=False,
            verbose=False
        )
        
        expected = np.array([0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95])
        np.testing.assert_array_almost_equal(evaluator.thresholds, expected)

    def test_04_apar_structure_output(self):
        """Functional Test: Ensure APAR() returns correct dictionary structure"""
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            frame_number_offset=499,
            singleFrameFromVideo=10,
            render_out=False,
            verbose=False
        )
        evaluator.initialize()
        results = evaluator.APAR()
        
        # Check Keys
        self.assertIn("MoveNet", results)
        self.assertIn("mAP", results["MoveNet"]) # its mAP - TODO 
        self.assertIn("mAR", results["MoveNet"])
        self.assertEqual(10, len(results["MoveNet"]["ap_per_threshold"]))
        
        # Check Values are in range [0, 1]
        self.assertTrue(0.0 <= results["MoveNet"]["mAP"] <= 1.0)

    def test_05_apar_curve_properties(self):
        """Test mathematical properties of AP-AR curve"""
        from utils.accuracyEvaluation.apar_evaluator import APAREvaluator

        evaluator = APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            start_threshold=0.5,
            stop_threshold=0.9,
            step_threshold=0.1,  # 5 thresholds: 0.5, 0.6, 0.7, 0.8, 0.9
            frame_number_offset=499,
            singleFrameFromVideo=10,
            render_out=False,
            verbose=False
        )
        
        evaluator.initialize()
        results = evaluator.APAR()
    
        # Property: Monotonicity
        for i in range(1, len(results["MoveNet"]["ap_per_threshold"])):
            self.assertGreaterEqual(
                results["MoveNet"]["ap_per_threshold"][i-1] , 
                results["MoveNet"]["ap_per_threshold"][i],
                f"APAR increased from t={evaluator.thresholds[i-1]} to t={evaluator.thresholds[i]}"
            )

    # ------------------------------------------------------------------------
    # Tier 3 - Edge Cases
    # ------------------------------------------------------------------------

    def test_06_edge_case_empty_predictions(self):
        """Edge Case: File exists but contains empty list []"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            empty_pred_path = f.name

        try:
            evaluator = self.APAREvaluator(
                ground_truth_file=self.gt_path,
                predictions_file_list={"EmptyModel": empty_pred_path},
                input_src=self.video_path,
                singleFrameFromVideo=10, # Run on one frame
                render_out=False,
                verbose=False
            )
            evaluator.initialize()
            results = evaluator.APAR()

            # Should be exactly 0.0
            self.assertEqual(results["EmptyModel"]["mAP"], 0.0)
            self.assertEqual(results["EmptyModel"]["mAR"], 0.0)

        finally:
            os.unlink(empty_pred_path)

    def test_06_edge_case_no_gt(self):
        """Edge Case: Frame has predictions but no GT (All FP)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            empty_gt_path = f.name

        try:
            evaluator = self.APAREvaluator(
                ground_truth_file=empty_gt_path,
                predictions_file_list={"MoveNet": self.pred_path},
                input_src=self.video_path,
                singleFrameFromVideo=10, # Run on one frame
                render_out=False,
                verbose=False
            )
            
            with self.assertRaises(ValueError):
                evaluator.initialize()

        finally:
            os.unlink(empty_gt_path)

    # ------------------------------------------------------------------------
    # Tier 4 - Golden Tests
    # ------------------------------------------------------------------------
    def test_07_golden_apar_synthetic(self):
        """
        Golden Test: Test using synthetic oks scores.
        - 4 GTs
        - 5 Predictions (mixed TP/FP/LowOKS)
        - Single Threshold: 0.4
        """       
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            start_threshold=0.4, # Single threshold
            stop_threshold=0.4,
            step_threshold=0.1
        )
        
        # Prevents run_evaluation from running inside APAR()
        with patch.object(evaluator, 'run_evaluation') as mock_run:
            evaluator.total_gt_count = 4
            evaluator.all_detections = {
                "SyntheticModel": [
                    {'score': 0.22, 'oks': 0.00, 'is_matched': False},
                    {'score': 0.75, 'oks': 0.30, 'is_matched': True},  # (Localization error < 0.4)
                    {'score': 0.88, 'oks': 0.93, 'is_matched': True},
                    {'score': 0.92, 'oks': 0.83, 'is_matched': True},
                    {'score': 0.75, 'oks': 0.53, 'is_matched': True},
                ]
            }
            
            # Run the math
            final_metrics = evaluator.APAR()
            
            # --- Assertions ---
            threshold_key = evaluator.thresholds[0]  # 0.4
            mAP = final_metrics["SyntheticModel"]["mAP"]
            mAR = final_metrics["SyntheticModel"]["mAR"]

            results_per_threshold = final_metrics["SyntheticModel"]["results_per_threshold"]
           
            mock_run.assert_called_once() # Sanity: run_evaluation was skipped

            oks_results = results_per_threshold[threshold_key]
            expected = {
                0.92: {'TP': 1, 'FP': 0, 'FN': 3, 'precision': 1.0,  'recall': 0.25},
                0.88: {'TP': 2, 'FP': 0, 'FN': 2, 'precision': 1.0,  'recall': 0.50},
                0.75: {'TP': 3, 'FP': 1, 'FN': 1, 'precision': 0.75, 'recall': 0.75},
                0.22: {'TP': 3, 'FP': 2, 'FN': 1, 'precision': 0.60, 'recall': 0.75},
            }

            for conf, exp in expected.items():
                self.assertIn(conf, oks_results)

                res = oks_results[conf]

                self.assertEqual(res['TP'], exp['TP'])
                self.assertEqual(res['FP'], exp['FP'])
                self.assertEqual(res['FN'], exp['FN'])

                self.assertAlmostEqual(res['precision'], exp['precision'], places=5)
                self.assertAlmostEqual(res['recall'], exp['recall'], places=5)

            self.assertAlmostEqual(mAR, 0.75, places=5)   # Check AR (max recall)
            self.assertAlmostEqual(mAP, 0.690594, places=5) # Check AP (manually computed) COCO mAP
            self.assertIn(threshold_key, results_per_threshold)


    def test_08_golden_apar_single_frame(self):
        """
        Golden test: Compare against known good OKS value for frame 10 (golden tests from oks 1&2)
        Two persons: 
          - Pair A (PD_0 -> GT_1): OKS=0.83452, Conf=0.7191 (Rank 1)
          - Pair B (PD_1 -> GT_0): OKS=0.60677, Conf=0.5137 (Rank 2)
        """
        evaluator = self.APAREvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            start_threshold=0.5,
            stop_threshold=0.95,
            step_threshold=0.05,
            frame_number_offset=499,
            singleFrameFromVideo=10,
            render_out=False,
            verbose=False
        )
        evaluator.initialize()
        results = evaluator.APAR()["MoveNet"]

        # 1. Check Global Metrics (mAP / mAR)
        # # Expected mAP: 0.50198... due to COCO 101-point interpolation bias
        expected_map = (3 * 1.0 + 4 * (51/101)) / 10
        assert np.isclose(results['mAP'], expected_map, atol=1e-5), f"mAP mismatch: Got {results['mAP']}, expected {expected_map}"
        assert np.isclose(results['mAR'], 0.5, atol=1e-4)

        # 2. Check Detailed Results per Threshold
        details = results['results_per_threshold']
        
        # Iterate over all standard COCO thresholds
        # We use round() to avoid floating point iterator issues (e.g. 0.50000001)
        oks_thresholds = [round(t, 2) for t in np.arange(0.5, 1.0, 0.05)]
        
        for threshold in oks_thresholds:
            # Get the result dictionary for this threshold
            # Format: {conf_score: {'TP':..., 'FP':...}, ...}
            current_thresh_results = details.get(threshold)
            assert current_thresh_results is not None, f"Missing threshold {threshold}"

            # Sort entries by confidence descending (High Conf -> Low Conf)
            # This ensures 'row 0' is always PD_0 and 'row 1' is PD_1
            sorted_preds = sorted(
                current_thresh_results.items(), 
                key=lambda item: item[0], 
                reverse=True
            )
            
            # Extract metrics for Rank 1 (PD_0) and Rank 2 (PD_1)
            # format: (confidence_key, metrics_dict)
            r1_conf, r1_metrics = sorted_preds[0] 
            r2_conf, r2_metrics = sorted_preds[1]

            # Verify Confidences are roughly what we expect
            assert np.isclose(r1_conf, 0.715, atol=1e-3)
            assert np.isclose(r2_conf, 0.513, atol=1e-3)

            # --- GROUP A: T=0.50 to 0.60 ---
            # Both OKS (0.83, 0.60) pass. Both are TP.
            if threshold <= 0.60:
                # Rank 1: TP=1, FP=0, FN=1 (1 found, 1 missed so far)
                assert r1_metrics['TP'] == 1 and r1_metrics['FP'] == 0
                assert r1_metrics['precision'] == 1.0 and r1_metrics['recall'] == 0.5
                
                # Rank 2: Cumulative TP=2.
                assert r2_metrics['TP'] == 2 and r2_metrics['FP'] == 0
                assert r2_metrics['precision'] == 1.0 and r2_metrics['recall'] == 1.0

            # --- GROUP B: T=0.65 to 0.80 ---
            # PD_0 passes (0.83 > T). PD_1 fails (0.60 < T).
            elif threshold <= 0.80:
                # Rank 1: Still TP (Match)
                assert r1_metrics['TP'] == 1 and r1_metrics['FP'] == 0
                assert r1_metrics['precision'] == 1.0 and r1_metrics['recall'] == 0.5
                
                # Rank 2: Now FP (Miss)
                # Cumulative: TP=1, FP=1. FN=1 (Total GT=2, we only found 1 correctly)
                assert r2_metrics['TP'] == 1 and r2_metrics['FP'] == 1
                assert r2_metrics['precision'] == 0.5 and r2_metrics['recall'] == 0.5

            # --- GROUP C: T=0.85 to 0.95 ---
            # Both fail. Both FP.
            else:
                # Rank 1: Now FP
                # TP=0, FP=1. FN=2 (Missed everyone)
                assert r1_metrics['TP'] == 0 and r1_metrics['FP'] == 1
                assert r1_metrics['precision'] == 0.0 and r1_metrics['recall'] == 0.0
                
                # Rank 2: Now FP
                # Cumulative: TP=0, FP=2. FN=2.
                assert r2_metrics['TP'] == 0 and r2_metrics['FP'] == 2
                assert r2_metrics['precision'] == 0.0 and r2_metrics['recall'] == 0.0
        

    def test_09_golden_apar_multi_frame(self):
        "Can use 2 different frames, each doubled so we have a 4 frame video"
        self.assertTrue(False)
        pass

if __name__ == '__main__':
    unittest.main()