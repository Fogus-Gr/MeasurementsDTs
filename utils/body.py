class Body:
    def __init__(self, score, xmin, ymin, xmax, ymax, keypoints_score, keypoints, keypoints_norm):
        self.score = score                      # global/mean score 
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.keypoints_score = keypoints_score  # individual scores of the keypoints
        self.keypoints_norm = keypoints_norm    # keypoints normalized ([0,1]) coordinates (x,y) in the input image
        self.keypoints = keypoints              # keypoints coordinates (x,y) in pixels in the input image

        # -- Evaluation Stuffs -- #
        # PCK
        self.correctness = None
        self.included_in_denominator = None

        # OKS
        self.oks = 0
        self.matched = False

        self.thresh_radius = None