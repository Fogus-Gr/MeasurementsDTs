import numpy as np
import pytest
from utils.accuracyEvaluation.metrics.pck import PCKEvaluator
from utils.constants import LABELED_VISIBLE, NOT_LABELED


# ----------------------------------------------------
# Helper Dummy Class
# ----------------------------------------------------
class DummyBody:
    def __init__(self, keypoints, keypoints_score):
        self.keypoints = np.array(keypoints, dtype=float)
        self.keypoints_score = np.array(keypoints_score, dtype=float)

        self.thresh_radius = None
        

# ----------------------------------------------------
# Tests
# ----------------------------------------------------
def test_pck_invalid_threshold_type():
    """
    Test that invalid threshold type raises error.
    """
    gt_kpts = np.zeros((17, 2))
    gt = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(gt_kpts, np.ones(17))
    
    with pytest.raises(ValueError):
        evaluator = PCKEvaluator(threshold_type="invalid", alpha=0.2)
        evaluator.evaluate(gt, pred)

def test_pck_invalid_threshold_type2():
    """
    Test that invalid threshold type raises error.
    """
    gt_kpts = np.zeros((17, 2))
    gt = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(gt_kpts, np.ones(17))
    
    with pytest.raises(ValueError):
        evaluator = PCKEvaluator(threshold_type="torso", alpha=-0.2)
        evaluator.evaluate(gt, pred)

def test_pck_alpha_zero_behavior():
    """
    PCK with alpha = 0.0 should only count exactly correct keypoints.
    """
    gt_kpts = np.zeros((17, 2))
    pred_kpts_exact = gt_kpts.copy()
    pred_kpts_off = gt_kpts + 0.1
    
    gt = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred_exact = DummyBody(pred_kpts_exact, np.full(17, LABELED_VISIBLE))
    pred_off = DummyBody(pred_kpts_off, np.full(17, LABELED_VISIBLE))
    
    evaluator = PCKEvaluator(threshold_type="torso", alpha=0.0)
    
    # Perfect match → PCK = 1.0
    pck_exact, _, _ = evaluator.evaluate(gt, pred_exact)
    assert np.isclose(pck_exact, 1.0)
    
    # Small error → PCK = 0.0
    pck_off, _, _ = evaluator.evaluate(gt, pred_off)
    assert np.isclose(pck_off, 0.0)


def test_pck_no_valid_keypoints():
    """
    Test when no keypoints are included in denominator.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100

    # All keypoints are not visible and not predicted
    gt_v = np.full(17, NOT_LABELED)
    pred_scores = np.zeros(17)  # No predictions
    
    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(gt_kpts, pred_scores)
    
    evaluator = PCKEvaluator(threshold_type="torso", alpha=0.2)
    pck, correctness, included = evaluator.evaluate(gt, pred)
    
    assert pck == 0.0
    assert not included.any()  # No keypoints included

def test_pck_distance_calculation():
    """
    Test that Euclidean distance is calculated correctly.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts   = np.random.rand(17, 2) * 100
    pred_kpts = np.random.rand(17, 2) * 100
    
    # Set torso points for normalization
    gt_kpts[5] = [0, 0]
    gt_kpts[12] = [10, 0]
    
    # Test point with known distance
    gt_kpts[0] = [0, 0]
    pred_kpts[0] = [3, 4]  # Distance should be 5
    
    gt = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(pred_kpts, np.ones(17))
    
    evaluator20 = PCKEvaluator(threshold_type="torso", alpha=0.2)
    evaluator49 = PCKEvaluator(threshold_type="torso", alpha=0.49)
    evaluator50 = PCKEvaluator(threshold_type="torso", alpha=0.5)
    _, correctness20, _ = evaluator20.evaluate(gt, pred)
    _, correctness49, _ = evaluator49.evaluate(gt, pred)
    _, correctness50, _ = evaluator50.evaluate(gt, pred)
    
    assert not correctness20[0]
    assert not correctness49[0]
    assert correctness50[0]

def test_pck_perfect_prediction():
    """
    PCK should be 1.0 when prediction matches GT exactly.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100  # [0, 100]

    # Ensure torso points are separated for meaningful threshold
    gt_kpts[5] = [0, 0]    # Left shoulder
    gt_kpts[12] = [50, 0]  # Right hip → torso distance = 50

    pred_kpts = gt_kpts.copy()

    gt = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(pred_kpts, np.ones(17))

    evaluator = PCKEvaluator(threshold_type="torso", alpha=0.2)
    pck, correctness, included = evaluator.evaluate(gt, pred)

    assert np.isclose(pck, 1.0)
    assert correctness.all()
    assert included.all()


def test_pck_threshold_behavior():
    """
    Small error should still be correct if below threshold.
    Large error should be incorrect.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100  # [0, 100]

    # Torso distance: |(5) - (12)|
    # Set keypoint 5 = (0,0), keypoint 12 = (10, 0)
    gt_kpts_with_torso = gt_kpts.copy()
    gt_kpts_with_torso[5] = np.array([0, 0])
    gt_kpts_with_torso[12] = np.array([10, 0])

    # threshold = 0.2 * 10 = 2px
    alpha = 0.2

    # Predictions: first KP error=1px (<2px threshold), second error=5px (>2px)
    pred_kpts = gt_kpts_with_torso.copy()
    pred_kpts[0] = gt_kpts_with_torso[0] + np.array([1, 0])  # correct
    pred_kpts[1] = gt_kpts_with_torso[1] + np.array([5, 0])  # incorrect

    gt = DummyBody(gt_kpts_with_torso, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(pred_kpts, np.ones(17))

    evaluator = PCKEvaluator(threshold_type="torso", alpha=alpha)
    pck, correctness, included = evaluator.evaluate(gt, pred)

    # Check correctness:
    assert correctness[0] == True
    assert correctness[1] == False

    # Ratio
    expected = correctness[included].mean()
    assert np.isclose(pck, expected)


def test_pck_head_threshold():
    """
    Test PCK with head-based thresholding.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100

    # Set ear positions for head distance calculation
    gt_kpts[3] = [0, 0]   # Left ear
    gt_kpts[4] = [8, 0]   # Right ear
    
    pred_kpts = gt_kpts.copy()
    
    gt = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(pred_kpts, np.ones(17))
    
    evaluator = PCKEvaluator(threshold_type="head", alpha=0.2)
    pck, correctness, included = evaluator.evaluate(gt, pred)
    
    # Head distance should be 8, threshold = 0.2 * 8 = 1.6
    assert evaluator._get_norm_dist(gt_kpts) == 8.0
    assert np.isclose(pck, 1.0)


def test_pck_visibility_logic():
    """
    Visible keypoints are included.
    Not-visible are not included.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    gt_v = np.array([
        LABELED_VISIBLE,
        NOT_LABELED,
        LABELED_VISIBLE,
        NOT_LABELED
    ] + [LABELED_VISIBLE]*13)

    pred_scores = np.array([1.0, 0.0, 1.0, 0.9] + [1.0]*13)
    pred_kpts = gt_kpts.copy()

    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)

    evaluator = PCKEvaluator(threshold_type="torso", alpha=0.2)
    _, correctness, included = evaluator.evaluate(gt, pred)

    expected = np.array([
        True,   # visible
        False,  # not-visible + not predicted
        True,   # visible
        False    # not-visible + predicted
    ]
    + [True] * 13 # visible
    )

    assert np.array_equal(included, expected)


def test_pck_mixed_scenario():
    """
    Test complex scenario with mixed visibility and correctness.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100  # [0, 100]
    
    gt_kpts[5] = [0, 0]  # Shoulder L
    gt_kpts[12] = [10, 0]  # Hips R
    
    # Keypoint states:
    # 0: visible, correct (distance=0)
    # 1: visible, incorrect (distance=3, threshold=2)
    # 2: not-visible, predicted, correct (distance=1)
    # 3: not-visible, predicted, incorrect (distance=3)
    # 4: not-visible, not predicted (excluded)
    
    pred_kpts = gt_kpts.copy()
    pred_kpts[1] = pred_kpts[1] + [3, 0]   # Large error
    pred_kpts[2] = pred_kpts[2] + [1, 0]   # Small error
    pred_kpts[3] = pred_kpts[3] + [3, 0]   # Large error
    
    gt_v = np.array([
        LABELED_VISIBLE,      # 0
        LABELED_VISIBLE,      # 1  
        NOT_LABELED,  # 2
        NOT_LABELED,  # 3
        NOT_LABELED,  # 4
    ] + [LABELED_VISIBLE]*12)
    
    pred_scores = np.array([1.0, 1.0, 1.0, 1.0, 0.0]  + [1.0]*12)
    
    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)
    
    evaluator = PCKEvaluator(threshold_type="torso", alpha=0.2)
    pck, correctness, included = evaluator.evaluate(gt, pred)
    
    # Expected: points 0,1 included; 2,3,4 excluded
    # Correctness: 0✓, 1✗, 2✓, 3✗ → (17-1-3)/(17-3) = 13/14 = 0.928571429
    assert np.array_equal(included, [True, True, False, False, False] + [True] * 12)
    assert np.array_equal(correctness, [True, False, False, False, False] + [True] * 12)
    assert np.isclose(pck, 0.92857, atol=1e-04) 


def test_pck_golden_1():
        """
        Golden test: Compare one pair from frame 10
        """
        gt_0_kpts = np.array([[1629.56, 367.38], [1612.36, 337.09], [1650.83, 344.0], [1560.72, 310.15], [1655.3, 324.27], [1480.17, 435.91], [1658.41, 428.14], [1463.49, 599.63], [1725.03, 638.45], [1636.73, 616.44], [1748.03, 626.4], [1546.02, 818.51], [1654.32, 855.73], [1561.75, 1054.97], [1688.38, 1087.12], [1563.59, 1294.85], [1515.26, 1321.52]])
        pd_1_kpts = np.array([[1633.44, 333.24], [1613.1, 303.15], [1650.16, 313.03], [1574.19, 301.05], [1656.52, 323.51], [1462.59, 419.2], [1671.74, 434.84], [1489.96, 600.19], [1729.05, 651.04], [1714.74, 578.62], [1766.95, 611.91], [1499.47, 802.03], [1625.89, 810.15], [1555.16, 1050.95], [1705.14, 1049.46], [1550.16, 1054.34], [1642.63, 1061.36]])
        gt_vis      = np.array([   2.,   2.,    2.,    2.,    2.,    2.,   2.,    2.,    2.,    2.,    2.,    2.,    2.,    2.,    0.,  0., 0.])
        pd_1_scores = np.array([0.471, 0.39, 0.542, 0.507, 0.655, 0.703, 0.61, 0.373, 0.692, 0.275, 0.483, 0.728, 0.715, 0.646, 0.707, 0.0, 0.0])

        # Evaluation parameters
        conf_thresh = 0.71
        
        # Only indices 11 (0.728) and 12 (0.715) have score > 0.71
        passing_indices = np.where(pd_1_scores >= conf_thresh)[0]
        assert np.array_equal(passing_indices, [11, 12])
        
        total_gt_visible = np.sum(gt_vis == LABELED_VISIBLE)
        assert total_gt_visible == 14
        
        threshold = np.linalg.norm(gt_0_kpts[5] - gt_0_kpts[12]) # LShoulder - LHip
        dists = np.linalg.norm(gt_0_kpts - pd_1_kpts, axis=1)

        # Run PCK
        pd_1_scores = np.array([0]*11 + [1, 1, 0, 0, 0, 0])
        gt = DummyBody(gt_0_kpts, gt_vis)
        pred = DummyBody(pd_1_kpts, pd_1_scores)

        evaluator = PCKEvaluator(threshold_type="torso")
        calculated_pck = []
        for alpha in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
            evaluator.set_alpha(alpha)
            pck, _, _ = evaluator.evaluate(gt, pred)
            calculated_pck.append(pck)
        
        # Assert
        expected_pck_curve = np.array([0, 0, 0, 2/14, 2/14, 2/14, 2/14])
        np.testing.assert_allclose(calculated_pck, expected_pck_curve, atol=1e-3, err_msg="High confidence PCK calculation failed manual verification")

    
def test_pck_golden_2():
        """
        Golden test: Compare other pair from frame 10
        """
        gt_1_kpts = np.array([[983.41, 409.8], [986.72, 394.83], [966.41, 393.85], [969.26, 405.93], [921.29, 404.06], [1001.51, 481.51], [868.5, 489.84], [1025.67, 586.68], [819.34, 591.23], [1065.95, 649.66], [859.48, 683.59], [1002.56, 701.89], [912.24, 712.18], [1002.28, 862.96], [915.65, 863.93], [993.6, 1018.39], [916.58, 997.54]])
        pd_0_kpts = np.array([[973.68, 410.14], [976.85, 397.81], [955.09, 395.6], [958.68, 399.17], [911.47, 401.46], [1002.33, 483.33], [859.42, 483.38], [1020.72, 571.15], [816.42, 601.41], [1058.11, 658.96], [848.94, 690.28], [987.34, 683.89], [902.52, 691.48], [1009.8, 864.55], [910.04, 867.61], [988.33, 1006.85], [917.45, 1006.12]])
        gt_vis      = np.array([   2.,   2.,    2.,    2.,    2.,    2.,    2.,    2.,    2.,    2.,   2.,    2.,    2.,    2.,    2.,    2.,    2.])
        pd_0_scores = np.array([0.698, 0.691, 0.47, 0.681, 0.734, 0.805, 0.766, 0.659, 0.633, 0.719, 0.67, 0.754, 0.717, 0.753, 0.768, 0.825, 0.812])

        # Evaluation parameters
        conf_thresh = 0.71
        
        # Only indices 11 (0.728) and 12 (0.715) have score > 0.71
        passing_indices = np.where(pd_0_scores >= conf_thresh)[0]
        assert np.array_equal(passing_indices, [4, 5, 6, 9, 11, 12, 13, 14, 15, 16])
        
        total_gt_visible = np.sum(gt_vis == LABELED_VISIBLE)
        assert total_gt_visible == 17
        
        threshold = np.linalg.norm(gt_1_kpts[5] - gt_1_kpts[12]) # LShoulder - LHip
        dists = np.linalg.norm(gt_1_kpts - pd_0_kpts, axis=1)

        # Run PCK
        pd_0_scores = np.array([0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1])
        gt = DummyBody(gt_1_kpts, gt_vis)
        pred = DummyBody(pd_0_kpts, pd_0_scores)

        evaluator = PCKEvaluator(threshold_type="torso")
        calculated_pck = []
        for alpha in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
            evaluator.set_alpha(alpha)
            pck, _, _ = evaluator.evaluate(gt, pred)
            calculated_pck.append(pck)
        
        # Assert
        expected_pck_curve = np.array([0, 7/17, 10/17, 10/17, 10/17, 10/17, 10/17])
        np.testing.assert_allclose(calculated_pck, expected_pck_curve, atol=1e-3, err_msg="High confidence PCK calculation failed manual verification")