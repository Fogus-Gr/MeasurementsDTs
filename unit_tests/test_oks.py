import numpy as np
import pytest
from utils.constants import LABELED_VISIBLE, LABELED_NOT_VISIBLE
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
def test_oks_invalid_confidence_threshold():
    """
    Test that invalid threshold type raises error.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100

    gt   = DummyBody(gt_kpts, np.full(17, LABELED_VISIBLE))
    pred = DummyBody(gt_kpts, np.ones(17))

    with pytest.raises(ValueError):
        OKSEvaluator(confidence_threshold=-0.1).evaluate(gt, pred)


def test_oks_no_valid_keypoints():
    """
    Test when no keypoints are included in denominator.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    scores = np.zeros(17) # suppressed

    gt   = DummyBody(gt_kpts, np.full(17, LABELED_NOT_VISIBLE))
    pred = DummyBody(gt_kpts, scores)

    evaluator = OKSEvaluator(confidence_threshold=0.2)
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

    evaluator = OKSEvaluator(confidence_threshold=0.2)

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

    evaluator = OKSEvaluator(confidence_threshold=0.2)
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

    evaluator = OKSEvaluator(confidence_threshold=0.2)
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
    Not-visible are only included if predicted.
    """
    np.random.seed(42)  # For reproducible tests
    
    # Generate random but valid keypoints
    gt_kpts = np.random.rand(17, 2) * 100
    gt_v = np.array([
        LABELED_VISIBLE,
        LABELED_NOT_VISIBLE,
        LABELED_VISIBLE,
        LABELED_NOT_VISIBLE,
        LABELED_NOT_VISIBLE
    ] + [LABELED_VISIBLE]*12)

    pred_scores = np.array([1.0, 0.0, 1.0, 0.9, 0.3] + [1.0]*12)
    pred_kpts = gt_kpts.copy()

    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)

    evaluator = OKSEvaluator(confidence_threshold=0.4)
    _, _, included = evaluator.evaluate(gt, pred)

    expected = np.array([
        True,   # visible
        False,  # not-visible + not predicted
        True,   # visible
        True,   # not-visible + predicted
        False   # not-visible + predicted under thresh
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
    # 0: visible, correct (distance=0)
    # 1: visible, offBy3  (distance=3)
    # 2: not-visible, predicted, offBy1 (distance=1)
    # 3: not-visible, predicted, offBy5 (distance=5)
    # 4: not-visible, not predicted (excluded)
    
    pred_kpts = gt_kpts.copy()
    pred_kpts[1] = pred_kpts[1] + [3, 0]   # Add error
    pred_kpts[2] = pred_kpts[2] + [0, 1]   # Add error
    pred_kpts[3] = pred_kpts[3] + [3, 4]   # Add error
    
    gt_v = np.array([
        LABELED_VISIBLE,      # 0
        LABELED_VISIBLE,      # 1  
        LABELED_NOT_VISIBLE,  # 2
        LABELED_NOT_VISIBLE,  # 3
        LABELED_NOT_VISIBLE,  # 4
    ] + [LABELED_VISIBLE]*12)
    
    pred_scores = np.array([1.0, 1.0, 1.0, 1.0, 0.1]  + [1.0]*12)
    
    gt = DummyBody(gt_kpts, gt_v)
    pred = DummyBody(pred_kpts, pred_scores)
    
    evaluator = OKSEvaluator(confidence_threshold=0.4)
    oks, ks_per_keypoint, included = evaluator.evaluate(gt, pred)

    ks_expected = np.array([1.0, 0.424372845677, 0.909156442877, 0.296777783795, 1.0]  + [1.0]*12)
    
    # Expected: all points included expect 5th
    assert np.array_equal(included, [True, True, True, True, False] + [True] * 12)
    assert np.allclose(ks_per_keypoint, ks_expected, rtol=1e-6)
    assert np.allclose(oks, np.mean(ks_expected[included]), rtol=1e-6)