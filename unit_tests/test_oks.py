"""
OKS doesn't apply threshold, is purely geometrical.
"""

import numpy as np
from utils.constants import LABELED_VISIBLE, NOT_LABELED
from utils.accuracyEvaluation.metrics.oks import OKSEvaluator


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
def test_oks_no_valid_keypoints():
    """
    Test when no keypoints are included in denominator.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    scores = np.zeros(17) # suppressed

    gt   = DummyBody(gt_kpts, np.full(17, NOT_LABELED))
    pred = DummyBody(gt_kpts, scores)

    evaluator = OKSEvaluator()
    oks, ks_per_keypoint, included = evaluator.evaluate(gt, pred)

    assert oks == 0.0
    assert not included.any()
    assert ks_per_keypoint.shape == (17,)
    assert np.allclose(ks_per_keypoint, 1.0)


def test_oks_segmentation_mask_approximation():
    """
    Test that boundingBox^2 is calculated correctly.
    """
    np.random.seed(42)  # For reproducible tests
    
    x_min, y_min = 10, 20
    x_max, y_max = 150, 80
    scale = 10

    gt_kpts = np.empty((17,2))
    gt_kpts[0] = (x_min, y_min)
    gt_kpts[1] = (x_max, y_max)

    # fill the rest uniformly inside the box
    gt_kpts[2:] = np.column_stack([
        np.random.uniform(x_min, x_max, 15),
        np.random.uniform(y_min, y_max, 15)
    ])

    scaled_kpts = gt_kpts * scale

    evaluator = OKSEvaluator()

    s_squared        = evaluator._get_scale_squared(gt_kpts)
    s_squared_scaled = evaluator._get_scale_squared(scaled_kpts)

    assert s_squared == 8400
    assert s_squared_scaled == s_squared * (scale**2)


def test_oks_perfect_prediction():
    """
    OKS should be 1.0 when prediction matches GT exactly.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    scores = np.ones(17)

    gt   = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(gt_kpts.copy(), scores)

    evaluator = OKSEvaluator()
    oks, _, included = evaluator.evaluate(gt, pred)

    assert np.isclose(oks, 1.0)
    assert included.all()


def test_oks_distance_effect():
    """
    ks_i = exp(- ||d_i||_2^2 / (2 * s^2 * k_i^2)
    dispalcement (1,1) => ||d_i||_2^2 = 2    => ks_i = exp(-   1 / (s^2 * k_i^2) = KS1
    dispalcement t     => ||d_i||_2^2 = 2t^2 => ks_i = exp(- t^2 / (s^2 * k_i^2) = KS1^(t^2)
    """
    np.random.seed(42)  # For reproducible tests
    
    # Create instance with s_squared = 8400 
    x_min, y_min = 10, 20
    x_max, y_max = 150, 80

    gt_kpts = np.empty((17,2))
    gt_kpts[0] = (x_min, y_min)
    gt_kpts[1] = (x_max, y_max)

    # fill the rest uniformly inside the box
    gt_kpts[2:] = np.column_stack([
        np.random.uniform(x_min, x_max, 15),
        np.random.uniform(y_min, y_max, 15)
    ])
    scores = np.ones(17)

    t = np.random.uniform() * 100
    pred_kpts  = gt_kpts + np.ones((17, 2))
    pred_kpts2 = gt_kpts + np.ones((17, 2)) * t

    gt    = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred  = DummyBody(pred_kpts, scores)
    pred2 = DummyBody(pred_kpts2, scores)

    evaluator = OKSEvaluator()
    oks1, ks_per_keypoint1, _ = evaluator.evaluate(gt, pred)
    oks2, ks_per_keypoint2, _ = evaluator.evaluate(gt, pred2)

    ks_expected = np.array([0.838529140379, 0.826565437624, 0.826565437624, 0.907391091116, 0.907391091116, 0.981105691024, 0.981105691024, 0.977297242992, 0.977297242992, 0.969504925365, 0.969504925365, 0.989655793049, 0.989655793049, 0.984394728644, 0.984394728644, 0.985083009867, 0.985083009867])

    assert np.allclose(ks_per_keypoint1, ks_expected, rtol=1e-6)
    assert np.allclose(ks_per_keypoint2, ks_expected ** (t**2), rtol=1e-6)
    assert np.allclose(oks1, np.mean(ks_expected), rtol=1e-6)
    assert np.allclose(oks2, np.mean(ks_expected ** (t**2)), rtol=1e-6)


def test_visibility_logic():
    """
    Visible keypoints are always included.
    Not-visible are not included.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    gt_v = np.array([
        LABELED_VISIBLE,
        NOT_LABELED,
        LABELED_VISIBLE,
        NOT_LABELED,
        LABELED_VISIBLE
    ] + [LABELED_VISIBLE]*12)

    pred_scores = np.array([1.0, 0.0, 1.0, 0.9, 0.0] + [1.0]*12)
    pred_kpts = gt_kpts.copy()

    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)

    evaluator = OKSEvaluator()
    _, _, included = evaluator.evaluate(gt, pred)

    expected = np.array([
        True,   # visible     + predicted
        False,  # not-visible + not predicted
        True,   # visible     + predicted
        False,  # not-visible + predicted
        True    # visible     + not predicted
    ]
    + [True] * 12 # visible
    )

    assert np.array_equal(included, expected)


def test_oks_mixed_scenario():
    """
    Test complex scenario with mixed visibility and correctness.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Create instance with s_squared = 8400 
    x_min, y_min = 10, 20
    x_max, y_max = 150, 80

    gt_kpts = np.empty((17,2))
    gt_kpts[0] = (x_min, y_min)
    gt_kpts[1] = (x_max, y_max)

    # fill the rest uniformly inside the box
    gt_kpts[2:] = np.column_stack([
        np.random.uniform(x_min, x_max, 15),
        np.random.uniform(y_min, y_max, 15)
    ])
    
    # Keypoint states:
    # 0: visible, correct                (included) (distance=0)
    # 1: visible, offBy3                 (included) (distance=3)
    # 2: visible, not predicted, offBy18 (included) (distance=18.3)
    # 3: not-visible, predicted, offBy5  (excluded) (distance=5)
    # 4: not-visible, not predicted      (excluded)
    
    pred_kpts = gt_kpts.copy()
    pred_kpts[1] = pred_kpts[1] + [3,   0]   # Add error
    pred_kpts[2] = pred_kpts[2] + [15, 10]   # Add error
    pred_kpts[3] = pred_kpts[3] + [3,   4]   # Add error
    
    gt_v = np.array([
        LABELED_VISIBLE,      # 0
        LABELED_VISIBLE,      # 1  
        LABELED_VISIBLE,      # 2
        NOT_LABELED,          # 3
        NOT_LABELED,          # 4
    ] + [LABELED_VISIBLE]*12)
    
    pred_scores = np.array([1.0, 1.0, 0.0, 1.0, 0.0]  + [1.0]*12)
    
    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)
    
    evaluator = OKSEvaluator()
    oks, ks_per_keypoint, included = evaluator.evaluate(gt, pred)

    ks_expected = np.array([1.0, 0.4243728, 0.0, 0.2967777, 1.0]  + [1.0]*12)   # ks_expected[2] = 3.6103703226521694e-14
    oks_expected = np.mean(np.array([1.0, 0.4243728, 0.0]  + [1.0]*12))
    
    # Expected: all points included expect 5th
    assert np.array_equal(included, [True, True, True, False, False] + [True] * 12)
    assert np.allclose(ks_per_keypoint, ks_expected, rtol=1e-6)
    assert np.allclose(oks, oks_expected, rtol=1e-6)


def test_oks_golden_1():
    """
    Golden test: Compare one pair from frame 10
    """
    gt_0_kpts = np.array([[1629.56, 367.38], [1612.36, 337.09], [1650.83, 344.0], [1560.72, 310.15], [1655.3, 324.27], [1480.17, 435.91], [1658.41, 428.14], [1463.49, 599.63], [1725.03, 638.45], [1636.73, 616.44], [1748.03, 626.4], [1546.02, 818.51], [1654.32, 855.73], [1561.75, 1054.97], [1688.38, 1087.12], [1563.59, 1294.85], [1515.26, 1321.52]])
    pd_1_kpts = np.array([[1633.44, 333.24], [1613.1, 303.15], [1650.16, 313.03], [1574.19, 301.05], [1656.52, 323.51], [1462.59, 419.2], [1671.74, 434.84], [1489.96, 600.19], [1729.05, 651.04], [1714.74, 578.62], [1766.95, 611.91], [1499.47, 802.03], [1625.89, 810.15], [1555.16, 1050.95], [1705.14, 1049.46], [1550.16, 1054.34], [1642.63, 1061.36]])
    gt_vis      = np.array([   2.,   2.,    2.,    2.,    2.,    2.,   2.,    2.,    2.,    2.,    2.,    2.,    2.,    2.,    0.,  0., 0.])
    pd_1_scores = np.array([0.471, 0.39, 0.542, 0.507, 0.655, 0.703, 0.61, 0.373, 0.692, 0.275, 0.483, 0.728, 0.715, 0.646, 0.707, 0.133, 0.103])
    
    total_gt_visible = np.sum(gt_vis == LABELED_VISIBLE)
    assert total_gt_visible == 14

    # Run OKS
    gt = DummyBody(gt_0_kpts, gt_vis)
    pred = DummyBody(pd_1_kpts, pd_1_scores)

    evaluator = OKSEvaluator()
    s_squared = evaluator._get_scale_squared(gt_0_kpts)
    calculated_OKS, ks_per_keypoint, _ = evaluator.evaluate(gt, pred)
    
    # 1. Expected Constants
    # Scale Squared: W
    # Logic: Uses v > 0 (All 17 points)
    # New Max Y is 1321.52 (Index 16), Min Y is 310.15 (Index 3) -> Height = 1011.37
    # Width is 284.54
    # 284.54 * 1011.37 = 287775.22
    expected_s_squared = 287775.22
    
    # Per-keypoint OKS (Hand-calculated)
    ks_expected = np.array([
        0.0481, 0.0406, 0.0694, 0.6874, 0.9970,  # Head
        0.8489, 0.9399, 0.7906, 0.9431, 0.0334,  # Upper Body
        0.7736, 0.6906, 0.6454, 0.9864,          # Lower Body (Visible)
        0.6770, 0.0000, 0.0000                   # Hidden (v=1) - calc'd but ignored in mean
    ])

    # Mean OKS: Average of the 14 visible keypoints
    # Sum(visible) / 14
    oks_expected = 0.60677

    # 2. Assertions
    # Check Scale
    # Using atol=1.0 because scale is a large number (200k+)
    assert np.isclose(s_squared, expected_s_squared, atol=1.0), f"Scale squared mismatch: {s_squared} vs {expected_s_squared}"

    # Check Per-Keypoint Scores
    # Using atol=1e-4 for robustness
    # Note: We slice both arrays to [:14] to compare only valid points, 
    # or ensure your evaluator returns 0.0 for invisible ones.
    np.testing.assert_allclose(ks_per_keypoint, ks_expected, atol=1e-4, err_msg="Visible keypoint scores mismatch")

    # Check Total OKS
    assert np.isclose(calculated_OKS, oks_expected, atol=1e-4), f"Total OKS mismatch: {calculated_OKS} vs {oks_expected}"

    
def test_pck_golden_2():
    """
    Golden test: Compare other pair from frame 10
    """
    gt_1_kpts = np.array([[983.41, 409.8], [986.72, 394.83], [966.41, 393.85], [969.26, 405.93], [921.29, 404.06], [1001.51, 481.51], [868.5, 489.84], [1025.67, 586.68], [819.34, 591.23], [1065.95, 649.66], [859.48, 683.59], [1002.56, 701.89], [912.24, 712.18], [1002.28, 862.96], [915.65, 863.93], [993.6, 1018.39], [916.58, 997.54]])
    pd_0_kpts = np.array([[973.68, 410.14], [976.85, 397.81], [955.09, 395.6], [958.68, 399.17], [911.47, 401.46], [1002.33, 483.33], [859.42, 483.38], [1020.72, 571.15], [816.42, 601.41], [1058.11, 658.96], [848.94, 690.28], [987.34, 683.89], [902.52, 691.48], [1009.8, 864.55], [910.04, 867.61], [988.33, 1006.85], [917.45, 1006.12]])
    gt_vis      = np.array([   2.,   2.,    2.,    2.,    2.,    2.,    2.,    2.,    2.,    2.,   2.,    2.,    2.,    2.,    2.,    2.,    2.])
    pd_0_scores = np.array([0.698, 0.691, 0.47, 0.681, 0.734, 0.805, 0.766, 0.659, 0.633, 0.719, 0.67, 0.754, 0.717, 0.753, 0.768, 0.825, 0.812])
    
    total_gt_visible = np.sum(gt_vis == LABELED_VISIBLE)
    assert total_gt_visible == 17
    
    # Run OKS
    gt = DummyBody(gt_1_kpts, gt_vis)
    pred = DummyBody(pd_0_kpts, pd_0_scores)

    evaluator = OKSEvaluator()
    s_squared = evaluator._get_scale_squared(gt_1_kpts)
    calculated_OKS, ks_per_keypoint, _ = evaluator.evaluate(gt, pred)
    
    # Assertions
    
    # Check Scale Squared (s^2)
    # Width: 1065.95 - 819.34 = 246.61
    # Height: 1018.39 - 393.85 = 624.54
    # Area: 154,017.8094
    expected_s_squared = 154017.8094

    # Calculated using exp(-distance^2 / (2 * s^2 * k^2))
    ks_expected = np.array([
        0.634316, 0.575720, 0.505898, 0.658482, 0.760738,  # Head
        0.997929, 0.937497, 0.846665, 0.932247, 0.882512,  # Upper Body
        0.876580, 0.854181, 0.862198, 0.974953, 0.980892,  # Lower Body
        0.936087, 0.969968                                 # Ankles
    ])
    oks_expected = 0.834521

    
    np.testing.assert_allclose(ks_per_keypoint, ks_expected, atol=1e-4)
    assert np.isclose(s_squared, expected_s_squared, atol=1e-5)
    assert np.isclose(calculated_OKS, oks_expected, atol=1e-5)