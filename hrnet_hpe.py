import numpy as np
from openvino_base_hpe import OpenVINOBaseHPE
from base_hpe import Body


class HigherHRNet_W32(OpenVINOBaseHPE):
    LINES_BODY = [
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    def load_model(self, device="CPU", **kwargs):
        super().load_model(model_type="higherhrnet", device=device, **kwargs)

    
    def postprocess(self, poses):
        bodies = []

        for pose in poses:
            keypoints_xy = pose[:, :2]  # Shape: (17, 2)
            keypoints_scores = pose[:, 2]  # Shape: (17,)

            # Use average keypoint confidence as pose score
            score = np.mean(keypoints_scores)

            if score > self.score_thresh:
                # Depad & rescale keypoints to original image size
                keypoints_xy_orig = keypoints_xy.copy()

                # Undo resizing from 256x256 to original + padding
                unpadded_w = self.img_w + self.padding.w
                unpadded_h = self.img_h + self.padding.h
                keypoints_xy_orig[:, 0] = keypoints_xy_orig[:, 0] * (unpadded_w / self.pd_w)
                keypoints_xy_orig[:, 1] = keypoints_xy_orig[:, 1] * (unpadded_h / self.pd_h)

                # Calculate bounding box (tight box around visible keypoints)
                visible_kps = keypoints_xy_orig[keypoints_scores > 0.1]
                if len(visible_kps) == 0:
                    continue

                xmin = int(np.min(visible_kps[:, 0]))
                xmax = int(np.max(visible_kps[:, 0]))
                ymin = int(np.min(visible_kps[:, 1]))
                ymax = int(np.max(visible_kps[:, 1]))

                body = Body(
                    score=score,
                    xmin=xmin,
                    ymin=ymin,
                    xmax=xmax,
                    ymax=ymax,
                    keypoints_score=keypoints_scores,
                    keypoints=keypoints_xy_orig.astype(float),
                    keypoints_norm=keypoints_xy_orig / np.array([self.img_w, self.img_h])
                )
                bodies.append(body)

        return bodies
