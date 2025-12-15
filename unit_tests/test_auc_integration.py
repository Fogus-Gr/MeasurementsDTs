"""
Integration tests for AUCEvaluator using 2-second test data
"""
import unittest
import os
import json
import tempfile
import numpy as np
import sys
from unittest.mock import patch

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAUCEvaluatorIntegration(unittest.TestCase):
    """Integration tests using real 2-second test data"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data paths"""
        cls.test_dir = os.path.join(os.path.dirname(__file__), '..', 'unit_tests')
        
        # Expected test files
        cls.video_path = os.path.join(cls.test_dir, 'video2sec', '160422_ultimatum_hd_00_00_2s.mp4')
        cls.gt_path = os.path.join(cls.test_dir, 'video2sec', 'all_body2DScenes_326_367.json')
        cls.pred_path = os.path.join(cls.test_dir, 'video2sec', 'pd_movenet.json')
        
        # Check if test data exists
        cls.has_test_data = all(
            os.path.exists(p) for p in [cls.video_path, cls.gt_path, cls.pred_path]
        )
        
        if not cls.has_test_data:
            print(f"   Test data not found. Skipping integration tests.")
            print(f"   Expected files:")
            print(f"     - {cls.video_path}")
            print(f"     - {cls.gt_path}")
            print(f"     - {cls.pred_path}")
    
    def setUp(self):
        if not self.has_test_data:
            self.skipTest("Test data not available")
        
        # Import here to avoid import errors if test data missing
        from utils.accuracyEvaluation.auc_evaluator import AUCEvaluator
        from utils.accuracyEvaluation.keypointsDataset import KeypointsDataset
        
        self.AUCEvaluator = AUCEvaluator
        self.KeypointsDataset = KeypointsDataset
    
    " Tier 1 - Smoke Tests"
    def test_01_smoke_test_initialization(self):
        """Smoke Test: Basic initialization"""
        
        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=os.path.join(self.test_dir, "output.jpg"),
            frame_number_offset=0,
            verbose=False
        )
        
        self.assertIsNotNone(evaluator)
        try:
            evaluator.initialize()
            self.assertIsNotNone(evaluator.ground_truth)
            self.assertGreater(len(evaluator.predictions), 0)
        except Exception as e:
            self.fail(f"initialize() crashed: {e}")

    def test_02_initialization(self):
        """Functional Test: Check initialize()"""
        
        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=os.path.join(self.test_dir, "output.jpg"),
            frame_number_offset=0,
            verbose=False
        )

        evaluator.initialize()
        
        self.assertIsNotNone(evaluator.ground_truth)
        self.assertIsNotNone(evaluator.video_fps)
        self.assertGreater(len(evaluator.ground_truth.by_frame), 0, "Gt data should be loaded")
        self.assertGreater(len(evaluator.predictions[0].by_frame), 0, "Pd data should be loaded")
        self.assertAlmostEqual(evaluator.ground_truth.gt_fps, 29.97, places=2)
        self.assertAlmostEqual(evaluator.video_fps, 29.97, places=2)
        assert evaluator.img_w == 1920
        assert evaluator.img_h == 1080
        self.assertAlmostEqual(evaluator.frame_number_adjustor, 1.0, places=3)

    
    def test_03_data_loading_verification(self):
        """Data Verification Test: Are files loaded correctly?"""
        
        # Test KeypointsDataset directly
        gt_dataset = self.KeypointsDataset(self.gt_path, "ground_truth")
        pred_dataset = self.KeypointsDataset(self.pred_path, "MoveNet")
        
        # Check basic properties
        self.assertIsNotNone(gt_dataset)
        self.assertIsNotNone(pred_dataset)
        
        # Check they have frames
        self.assertGreater(len(gt_dataset.by_frame), 0)
        self.assertGreater(len(pred_dataset.by_frame), 0)
        
        # Check frame alignment
        self.assertEqual(len(gt_dataset.by_frame), len(pred_dataset.by_frame), "Ground truth and predictions should have same number of frames")
        
        # Check first few frames
        for frame_id in range(min(3, len(gt_dataset.by_frame))):
            gt_frame = gt_dataset.get_frame(frame_id)
            pred_frame = pred_dataset.get_frame(frame_id)
            
            self.assertIsNotNone(gt_frame, f"GT frame {frame_id} should exist")
            self.assertIsNotNone(pred_frame, f"Pred frame {frame_id} should exist")

    def test_04_threshold_calculation(self):
        """Test that thresholds are calculated correctly with floating-point safety"""

        test_cases = [
            (0.1, 0.3, 0.1, [0.1, 0.2, 0.3]),
            (0.0, 0.5, 0.1, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]),
            (0.0, 1.0, 0.25, [0.0, 0.25, 0.5, 0.75, 1.0]),
        ]
        
        for start, stop, step, expected in test_cases:
            evaluator = self.AUCEvaluator(
                ground_truth_file=self.gt_path,
                predictions_file_list={"MoveNet": self.pred_path},
                input_src=self.video_path,
                start_threshold=start,
                stop_threshold=stop,
                step_threshold=step,
            )
      
            np.testing.assert_array_almost_equal(evaluator.thresholds, expected, 
                                            err_msg=f"Failed for start={start}, stop={stop}, step={step}")

    
    def test_05_smoke_test_single_frame_evaluation(self):
        """Smoke Test: Single frame"""
        
        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            frame_number_offset=325,
            singleFrameFromVideo=10,  # frame 10
            render_out=False,
            verbose=False
        )

        evaluator.initialize()
        
        try:
            result = evaluator.run_evaluation()
            
            # Basic sanity check on result
            self.assertIn("MoveNet", result)
            if "MoveNet" in result:
                pck = result["MoveNet"]
                self.assertGreaterEqual(pck, 0.0, "PCK should be >= 0")
                self.assertLessEqual(pck, 1.0, "PCK should be <= 1")
        except Exception as e:
            self.fail(f"run_evaluation() crashed: {e}")
    
    
    def test_06_smoke_test_all_frames_evaluation(self):
        """Smoke Test: All frames"""
        
        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            frame_number_offset=325,
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
                pck = result["MoveNet"]
                self.assertGreaterEqual(pck, 0.0)
                self.assertLessEqual(pck, 1.0)
        except Exception as e:
            self.fail(f"run_evaluation() crashed: {e}")
    
    def test_07_functional_test_confidence_threshold(self):
        """Functional Test: Check different confidences"""
        
        # Test with 3 different confidence thresholds
        results = {}        
        for confidence in [0.1, 0.5, 0.9, 1.0]:
            evaluator = self.AUCEvaluator(
                ground_truth_file=self.gt_path,
                predictions_file_list={"MoveNet": self.pred_path},
                input_src=self.video_path,
                confidence_threshold=confidence,
                frame_number_offset=325,
                singleFrameFromVideo=10,
                render_out=False,
                verbose=False
            )
            
            evaluator.initialize()
            result = evaluator.run_evaluation()
            results[confidence] = result.get("MoveNet", 0.0)
        
        # 1. PCK at confidence=1.0 MUST be 0
        self.assertEqual(results[1.0], 0.0)

        # 2. PCK at confidence=0.9 should be LOWER than at 0.1 or 0.5
        self.assertLess(results[0.9], results[0.1])
        self.assertLess(results[0.9], results[0.5])

    
    def test_08_functional_test_pck_threshold_effect(self):
        """Functional Test: Check pck alpha threshold"""
        
        results = {}
        for pck_alpha_threshold in [0.1, 0.3, 0.5]:
            evaluator = self.AUCEvaluator(
                ground_truth_file=self.gt_path,
                predictions_file_list={"MoveNet": self.pred_path},
                input_src=self.video_path,
                pck_alpha_threshold=pck_alpha_threshold,
                frame_number_offset=325,
                singleFrameFromVideo=7,
                render_out=False,
                verbose=False
            )
            
            evaluator.initialize()
            result = evaluator.run_evaluation()
            results[pck_alpha_threshold] = result.get("MoveNet", 0.0)
            print(f"   - PCK threshold {pck_alpha_threshold}: PCK = {results[pck_alpha_threshold]:.3f}")
        
        # PCK must be non-decreasing with α
        self.assertLessEqual(results[0.1], results[0.3], "PCK should not decrease when alpha increases")
        self.assertLessEqual(results[0.3], results[0.5], "PCK should not decrease when alpha increases")
    
    def test_09_edge_case_empty_predictions(self):
        """Edge Case Test: Handling empty predictions"""

        # Create a temporary empty predictions file (as an empty list)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            empty_pred_path = f.name

        try:
            evaluator = self.AUCEvaluator(
                ground_truth_file=self.gt_path,  # must be valid
                predictions_file_list={"Empty": empty_pred_path},
                input_src=self.video_path,
                frame_number_offset=0,
                singleFrameFromVideo=0,
                render_out=False,
                verbose=False
            )

            evaluator.initialize()
            result = evaluator.run_evaluation()

            # Handle gracefully
            pck = result.get("Empty", 0.0)
            self.assertEqual(pck, 0.0, "Empty predictions should give PCK = 0")

        finally:
            # Clean up temp file
            os.unlink(empty_pred_path)
    
    def test_10_invalid_alpha_pck(self):
        """Edge Case Test: Handling invalid pck alpha thresholds"""

        for invalid_alpha in [-0.5, 1.3]:
            with self.assertRaises(ValueError):
                evaluator = self.AUCEvaluator(
                    ground_truth_file=self.gt_path,
                    predictions_file_list={"MoveNet": self.pred_path},
                    input_src=self.video_path,
                    pck_alpha_threshold=invalid_alpha,
                    frame_number_offset=325,
                    singleFrameFromVideo=7,
                    render_out=False,
                    verbose=False
                )
                evaluator.initialize()  # should trigger ValueError via PCKEvaluator
        
    
    def test_11_smoke_test_auc_method(self):
        """Smoke Test: Full AUC pipeline on all frames (no rendering)"""

        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=os.path.join(self.test_dir, "auc_output.jpg"),
            start_threshold=0.1,
            stop_threshold=0.3,
            step_threshold=0.1,
            frame_number_offset=325,
            singleFrameFromVideo=-1,
            render_out=False,
            verbose=False
        )

        evaluator.initialize()

        # Mock draw_curve to avoid actual plotting
        with patch('utils.accuracyEvaluation.auc_evaluator.draw_curve') as mock_draw:
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                evaluator.AUC()

            output = f.getvalue()

            # Check that it ran through all thresholds
            self.assertIn("PCK_threshold: 0.1", output)
            self.assertIn("PCK_threshold: 0.2", output)
            self.assertIn("PCK_threshold: 0.3", output)

            # Draw curve must be called once
            mock_draw.assert_called_once()

    def test_12_functional_test_auc_calculation(self):
        """Functional Test: Verify AUC calculation is correct"""
        
        # Test parameters
        start_threshold = 0.1
        stop_threshold = 0.3
        step_threshold = 0.1
        
        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=os.path.join(self.test_dir, "auc_functional_output.jpg"),
            start_threshold=start_threshold,
            stop_threshold=stop_threshold,
            step_threshold=step_threshold,
            frame_number_offset=325,
            singleFrameFromVideo=-1,
            render_out=False,
            verbose=False
        )
        
        evaluator.initialize()
        
        # Capture output to analyze
        import io
        from contextlib import redirect_stdout
        
        with patch('utils.accuracyEvaluation.auc_evaluator.draw_curve'):
            f = io.StringIO()
            with redirect_stdout(f):
                evaluator.AUC()
            
            output = f.getvalue()
        
        # Parse the output to get PCK values
        lines = output.split('\n')
        pck_values = []
        
        for line in lines:
            if "PCK = " in line:
                # Extract the dictionary from the line
                dict_str = line.split('=', 1)[1].strip()
                pck_dict = eval(dict_str)  # Be careful with eval in production!
                pck_values.append(pck_dict.get("MoveNet", 0.0))
        
        # Should have 3 PCK values for 3 thresholds
        self.assertEqual(len(pck_values), 3, f"Expected 3 PCK values, got {len(pck_values)}")
        
        # Calculate AUC manually using the same formula
        pck_numeric = np.array(pck_values)
        expected_auc = (1 / (stop_threshold - start_threshold)) * np.sum(pck_numeric) * step_threshold
        
        # Extract AUC from output
        actual_auc = None
        for line in lines:
            if "AUC (MoveNet) = " in line:
                actual_auc = float(line.split('=')[1].strip())
                break
        
        self.assertIsNotNone(actual_auc, "Could not find AUC value in output")
        
        # Verify AUC calculation matches
        self.assertAlmostEqual(
            actual_auc, 
            expected_auc, 
            places=4,
            msg=f"AUC calculation is wrong! Expected {expected_auc:.4f}, got {actual_auc:.4f}"
        )
        

    def test_13_pck_curve_properties(self):
        """Test mathematical properties of PCK curve"""
        from utils.accuracyEvaluation.auc_evaluator import AUCEvaluator
        
        evaluator = AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            start_threshold=0.1,
            stop_threshold=0.5,
            step_threshold=0.1,  # 5 thresholds: 0.1, 0.2, 0.3, 0.4, 0.5
            frame_number_offset=325,
            singleFrameFromVideo=10,
            render_out=False,
            verbose=False
        )
        
        evaluator.initialize()
        
        # We'll manually run PCK at each threshold to test properties
        pck_values = []
        
        for alpha in evaluator.thresholds:
            evaluator.pck_eval.set_alpha(alpha)
            result = evaluator.run_evaluation()
            pck = result.get("MoveNet", 0.0)
            pck_values.append(pck)
            
            # Property 1: PCK ∈ [0, 1]
            self.assertGreaterEqual(pck, 0.0, f"PCK should be >= 0 at α={alpha}")
            self.assertLessEqual(pck, 1.0, f"PCK should be <= 1 at α={alpha}")
        
    
        # Property 2: Monotonicity
        for i in range(1, len(pck_values)):
            self.assertGreaterEqual(
                pck_values[i], 
                pck_values[i-1] - 0.01,  # Allow small numerical tolerance
                f"PCK decreased from α={evaluator.thresholds[i-1]} to α={evaluator.thresholds[i]}"
            )


    def test_14_visualization_output_mocked(self):
        """Test that visualization creates output file (mock cv2 display)"""

        output_file = os.path.join(self.test_dir, "visualization_output_mocked.jpg")
        
        # Remove if exists from previous run
        if os.path.exists(output_file):
            os.remove(output_file)
        
        evaluator = self.AUCEvaluator(
            ground_truth_file=self.gt_path,
            predictions_file_list={"MoveNet": self.pred_path},
            input_src=self.video_path,
            last_frame_output=output_file,
            frame_number_offset=325,
            singleFrameFromVideo=10,
            render_out=True,  # Enable rendering
            verbose=False
        )
        
        evaluator.initialize()
        
        # Mock the cv2 functions that cause windows to open
        with patch('cv2.imshow') as mock_imshow, \
            patch('cv2.waitKey') as mock_waitkey, \
            patch('cv2.destroyAllWindows') as mock_destroy:
            
            mock_waitkey.return_value = -1
            
            # Run evaluation
            result = evaluator.run_evaluation()
        
        # Just check file was created
        self.assertTrue(os.path.exists(output_file))

        # Clean up (optional)
        os.remove(output_file)