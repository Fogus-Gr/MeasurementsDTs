import numpy as np
import pytest
from utils.accuracyEvaluation.metrics.pck import PCKEvaluator
from utils.constants import LABELED_VISIBLE, LABELED_NOT_VISIBLE


# ----------------------------------------------------
# Helper Dummy Class
# ----------------------------------------------------
class DummyBody:
    def __init__(self, keypoints, keypoints_score):
        self.keypoints = np.array(keypoints, dtype=float)
        self.keypoints_score = np.array(keypoints_score, dtype=float)


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

def test_pck_no_valid_keypoints():
    """
    Test when no keypoints are included in denominator.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100

    # All keypoints are not visible and not predicted
    gt_v = np.full(17, LABELED_NOT_VISIBLE)
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
    Visible keypoints are always included.
    Not-visible are only included if predicted.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    gt_v = np.array([
        LABELED_VISIBLE,
        LABELED_NOT_VISIBLE,
        LABELED_VISIBLE,
        LABELED_NOT_VISIBLE
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
        True    # not-visible + predicted
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
        LABELED_NOT_VISIBLE,  # 2
        LABELED_NOT_VISIBLE,  # 3
        LABELED_NOT_VISIBLE,  # 4
    ] + [LABELED_VISIBLE]*12)
    
    pred_scores = np.array([1.0, 1.0, 1.0, 1.0, 0.0]  + [1.0]*12)
    
    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)
    
    evaluator = PCKEvaluator(threshold_type="torso", alpha=0.2)
    pck, correctness, included = evaluator.evaluate(gt, pred)
    
    # Expected: points 0,1,2,3 included; 4 excluded
    # Correctness: 0✓, 1✗, 2✓, 3✗ → (17-2)/(17-1) = 15/16 = 0.875
    assert np.array_equal(included, [True, True, True, True, False] + [True] * 12)
    assert np.array_equal(correctness, [True, False, True, False, False] + [True] * 12)
    assert np.isclose(pck, 0.875)  