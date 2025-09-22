# 1. Make sure ground truth is saved with COCO format (currently there are 19 keypoints)
# 2. Make sure all methods save in same COCO format AND same precision on each keypoints
# 3. For each prediction, find closest timestamp (univTime) from groundTruth (implement a matching strategy in a seperate function
# so latter we can use different. Here we'll firstly use nearest-neighbor)
# 4. Show in saved image both prediction and ground truth
# 5. Calculate accuracy
# 6. Check other accuracy measures?

import json
#import argparse
import cv2
import numpy as np
from utils.visualizer import render
from base_hpe import Body

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)
    
def get_frame_from_video(cap, frame_number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    if not ret or frame is None:
        print("Could not grab frame.")
        frame = None

    cap.release()
    return frame
    
class KeypointsDataset:
    def __init__(self, json_file, source_name):
        self.data = load_json(json_file)
        self.source_name = source_name
        
        # Organize data by frame for faster lookup
        self.by_frame = {}
        for entry in self.data:
            frame = entry["frame_number"]
            if frame not in self.by_frame:
                self.by_frame[frame] = []
            self.by_frame[frame].append(entry["keypoints"])

    def get_frame(self, frame_number):
        """Return all detections for a given frame"""
        return self.by_frame.get(frame_number, [])

class Evaluator:
    def __init__(self, ground_truth: KeypointsDataset, predictions: list, input_src, output, singleFrameFromVideo = -1, tolerance=0.05):
        self.ground_truth = ground_truth
        self.predictions = predictions
        self.input_src = input_src
        self.output = output
        self.singleFrameFromVideo = singleFrameFromVideo

        self.LINES_BODY = [
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]
        
        if input_src:
            if input_src.endswith('.jpg') or input_src.endswith('.png'):
                self.input_type = "image"

            elif input_src.endswith('.mp4') or input_src.endswith('.avi'):
                self.input_type = "video"
                self.cap = cv2.VideoCapture(input_src)
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_FOCUS, 0)
                self.video_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                print(self.video_fps)
                self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
    """
    Convert Panoptic ground-truth keypoints into Body objects.
    
    Args:
        gt (dict): one GT entry (with "keypoints19_2d")
        img_w, img_h (int): image dimensions
    
    Returns:
        Body
    """
    def update_body_format(self, keypoint_list, img_w, img_h):
        bodies = []

        for gt in keypoint_list:
            # Panoptic gives flat list [x1, y1, s1, x2, y2, s2, ..., x17, y17, s17]
            kps = np.array(gt).reshape(-1, 3)  # shape (17, 3)

            # Extract (x, y) pixel coordinates
            keypoints = kps[:, :2].astype(float)

            # Extract confidence scores
            keypoints_score = kps[:, 2]

            # Normalize keypoints
            keypoints_norm = keypoints / np.array([img_w, img_h])

            # Bounding box from min/max keypoints
            valid = keypoints_score > 0
            if np.any(valid):
                xmin, ymin = keypoints[valid, 0].min(), keypoints[valid, 1].min()
                xmax, ymax = keypoints[valid, 0].max(), keypoints[valid, 1].max()
            else:
                xmin = ymin = xmax = ymax = 0

            # Global score = mean of valid keypoints
            score = keypoints_score[valid].mean() if np.any(valid) else 0.0

            body = Body(
                score=score,
                xmin=int(xmin),
                ymin=int(ymin),
                xmax=int(xmax),
                ymax=int(ymax),
                keypoints_score=keypoints_score,
                keypoints=keypoints,
                keypoints_norm=keypoints_norm,
            )

            bodies.append(body)

        return bodies

    
    # TODO: rename to get_frame_data?
    def find_closest_gt(self, frame_number = None, timestamp = None):
        results = {}

        results["ground_truth"] = self.ground_truth.get_frame(frame_number)
        for pd in self.predictions:
            results[pd.source_name] = pd.get_frame(frame_number)


        return results

    def evaluate(self, frame, keypoint_list, render_out=True, out_video=None):
        if frame is None:
            print("Could not grab frame")

        for method_name, keypoints_body in keypoint_list.items():
            bodies = self.update_body_format(keypoints_body, img_w = 640, img_h = 480) # TODO -> Not hardcoded

            is_gt = (method_name == "ground_truth")
            
            # TODO - different color for each pd
            render(frame, bodies, self.LINES_BODY, score_thresh = 0.2, show_scores = False, show_bounding_box = False, show_numbering = True, isGroundTruth = is_gt)              
                
        if render_out:
            cv2.imwrite(self.output, frame)
            #print("Saved:", os.path.abspath(filename))
            resized_image = cv2.resize(frame, (640, 480)) 
            cv2.imshow("Frame", resized_image)

            # Press 'q' to quit early
            if cv2.waitKey(0) & 0xFF == ord('q'):
                print("Quitting loop.")
                exit(0)

    def main_loop(self):
        if self.input_type == "image":
            frame = cv2.imread(self.input_src)
            #self.img_h, self.img_w = self.img.shape[:2]

            keypoint_list = self.find_closest_gt(frame_number = 118)    # TODO
            self.evaluate(frame, keypoint_list)
        elif self.input_type == "video":
            if self.singleFrameFromVideo >= 0:
                frame = get_frame_from_video(self.cap, self.singleFrameFromVideo)
                if frame is None:
                    exit(0)

                keypoint_list = self.find_closest_gt(self.singleFrameFromVideo)
                self.evaluate(frame, keypoint_list)                
            else:
                while True:
                    ok, frame = self.cap.read()
                    if not ok:
                        break

                    frame_number = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    print(f"Processing frame {frame_number}")

                    keypoint_list = self.find_closest_gt(frame_number = frame_number)
                    self.evaluate(frame, keypoint_list)


def main():
    ## Keypoints
    gt_file          = "keypoint_json/ground_truth_panoptic/00_00_single/all_body2DScenes.json"
    predictions_file = {
        "MoveNet": "keypoint_json/movenet/00_00/COCOformat.json",
        #"OpenPose": "results/COCOformatMovenet.json",
    }

    ground_truth = KeypointsDataset(gt_file, "ground_truth")

    predictions = []
    for method, path in predictions_file.items():
        predictions.append(KeypointsDataset(path, method))

    # Image/Video
    input  = "/mnt/data/panoptic-toolbox/scripts/171204_pose1_backup/hdVideos/hd_00_00.mp4"
    output = "/home/ioannis-2004/Desktop/MeasurementsDTs/out/gt05_08.jpg"
    
    singleFrameFromVideo = -1

    ev = Evaluator(ground_truth=ground_truth, predictions=predictions, input_src=input, output=output, singleFrameFromVideo=singleFrameFromVideo)
    ev.main_loop()

if __name__ == "__main__":
    main()