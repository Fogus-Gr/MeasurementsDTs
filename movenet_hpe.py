import numpy as np
from openvino_base_hpe import OpenVINOBaseHPE
from base_hpe import Body

class MoveNetHPE(OpenVINOBaseHPE):
    LINES_BODY = [
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    def load_model(self, device="CPU", **kwargs):
        super().load_model(model_type="movenet", device=device, **kwargs)
    
    def postprocess(self, predictions):
        result = np.squeeze(predictions[self.pd_kps]) # 6x56
        bodies = []
        
        for i in range(6):
            kps = result[i][:51].reshape(17,-1)
            bbox = result[i][51:55].reshape(2,2)          
            score = result[i][55]
            if score > self.score_thresh:   # TODO - use seperate keypoint scores
                ymin, xmin, ymax, xmax = (bbox * [self.padding.padded_h, self.padding.padded_w]).flatten().astype(int)

                kp_xy =kps[:,[1,0]]
                keypoints = kp_xy * np.array([self.padding.padded_w, self.padding.padded_h])
                keypoints = np.array(keypoints)

                body = Body(score=score, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax, 
                            keypoints_score = kps[:,2], 
                            keypoints = keypoints.astype(float),
                            keypoints_norm = keypoints / np.array([self.img_w, self.img_h]))
                
                bodies.append(body)
                
        return bodies