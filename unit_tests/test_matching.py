import unittest
import numpy as np
from utils.accuracyEvaluation.matching import Matcher

# Mock Body class to hold data
class MockBody:
    def __init__(self, keypoints, scores, img_size=(1920, 1080)):
        self.keypoints = np.array(keypoints)
        self.keypoints_score = np.array(scores)
        # Create normalized keypoints for the matcher
        self.keypoints_norm = self.keypoints / np.array(img_size)
        
        # Bounding box (simple min/max)
        valid = self.keypoints_score > 0
        if np.any(valid):
            self.xmin = np.min(self.keypoints[valid, 0])
            self.ymin = np.min(self.keypoints[valid, 1])
            self.xmax = np.max(self.keypoints[valid, 0])
            self.ymax = np.max(self.keypoints[valid, 1])
        else:
            self.xmin = self.ymin = self.xmax = self.ymax = 0

class TestMatcher(unittest.TestCase):
    def setUp(self):
        # Using data from frame_number = 10 from 2sec video after applying confidence_threshold = 0.71
        
        # GT 0 (Full body)
        gt0_kpts = [[1629, 367], [1612, 337], [1650, 344], [1560, 310], [1655, 324], 
                    [1480, 435], [1658, 428], [1463, 599], [1725, 638], [1636, 616], 
                    [1748, 626], [1546, 818], [1654, 855], [1561, 1054], [1688, 1087], 
                    [1563, 1294], [1515, 1321]]
        gt0_scores = [2]*14 + [1]*3 # Last 3 are score 1
        
        # GT 1 (Full body, far away)
        gt1_kpts = [[983, 409], [986, 394], [966, 393], [969, 405], [921, 404], 
                    [1001, 481], [868, 489], [1025, 586], [819, 591], [1065, 649], 
                    [859, 683], [1002, 701], [912, 712], [1002, 862], [915, 863], 
                    [993, 1018], [916, 997]]
        gt1_scores = [2]*17

        # PD 0 (Matches GT 1)
        pd0_kpts = [[973, 410], [976, 397], [955, 395], [958, 399], [911, 401], 
                    [1002, 483], [859, 483], [1020, 571], [816, 601], [1058, 658], 
                    [848, 690], [987, 683], [902, 691], [1009, 864], [910, 867], 
                    [988, 1006], [917, 1006]]
        # ~10 valid scores
        pd0_scores = [0, 0, 0, 0, 0.7, 0.8, 0.7, 0, 0, 0.7, 0, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8]

        # PD 1 (Matches GT 0, but only 2 points)
        pd1_kpts = np.zeros((17, 2))
        pd1_kpts[11] = [1499, 802]
        pd1_kpts[12] = [1625, 810]
        
        pd1_scores = np.zeros(17)
        pd1_scores[11] = 0.728
        pd1_scores[12] = 0.715

        self.gt_bodies = [MockBody(gt0_kpts, gt0_scores), MockBody(gt1_kpts, gt1_scores)]
        self.pred_bodies = [MockBody(pd0_kpts, pd0_scores), MockBody(pd1_kpts, pd1_scores)]

    def test_default_matching(self):
        """Test with default min_common_kpts=3"""

        matcher = Matcher(method="keypoint", min_common_kpts=3)
        matches = matcher.match(self.gt_bodies, self.pred_bodies)
        
        # Expectation: 
        # GT 1 should match PD 0 (They share 10 points)
        # GT 0 should NOT match PD 1 (They share only 2 points, 2 < 3)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], self.gt_bodies[1]) # GT 1
        self.assertEqual(matches[0][1], self.pred_bodies[0]) # PD 0

    def test_relaxed_matching(self):
        """Test with min_common_kpts=0 (Allows 2-point match)"""

        matcher = Matcher(method="keypoint", min_common_kpts=0, dist_thresh=0.1) 
        # Note: increased dist_thresh slightly just in case normalization is tight
        
        matches = matcher.match(self.gt_bodies, self.pred_bodies)
        
        # Expectation: Both should match now
        self.assertEqual(len(matches), 2)