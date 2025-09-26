import cv2
import numpy as np
from base_hpe import Body
from utils.visualizer import render
from utils.accuracyEvaluation.keypointsDataset import KeypointsDataset
from utils.accuracyEvaluation.metrics.pck import PCKEvaluator
    
def get_frame_from_video(cap, frame_number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    if not ret or frame is None:
        print("Could not grab frame.")
        frame = None

    cap.release()
    return frame

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
                print("Exiting... Not handling single image")
                exit(1)

            elif input_src.endswith('.mp4') or input_src.endswith('.avi'):
                self.input_type = "video"
                self.cap = cv2.VideoCapture(input_src)
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_FOCUS, 0)
                self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"self.video_fps: {self.video_fps}")
                self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
    
    # Convert COCO17 keypoints into Body objects
    def update_body_format(self, keypoint_list, img_w = 640, img_h = 480):   # TODO -> Not hardcoded/default values
        bodies = {}

        for method_name, keypoint_item in keypoint_list.items():
            persons = []

            for person in keypoint_item:
                kps = np.array(person).reshape(-1, 3)  # shape (17, 3)

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

                persons.append(body)

            bodies[method_name] = persons

        return bodies

    
    def get_frame_data(self, frame_number = None):
        results = {}

        results["ground_truth"] = self.ground_truth.get_frame(frame_number)
        for pd in self.predictions:
            results[pd.source_name] = pd.get_frame(frame_number)

        return results

    def evaluate_frame(self, bodies):
        gt = bodies['ground_truth']

        for method_name, prediction_bodies in bodies.items():
            if method_name == 'ground_truth':
                continue

            if not gt:
                continue

            # TODO - For now: single person assumption
            gt_kpts = gt[0].keypoints
            pred_body = prediction_bodies[0]

            if not prediction_bodies:
                num_joints = gt_kpts.shape[0]

                pck = 0.0
                correctness = np.zeros(num_joints, dtype=bool)
            else:
                pck_eval = PCKEvaluator(threshold_type="torso", alpha=0.2)
                pck, correctness = pck_eval.evaluate(gt_kpts, pred_body.keypoints)

            pred_body.correctness = correctness
            print(f"{method_name} PCK: {pck:.2f}")
            print(f"{method_name} pred_body.correctness: {pred_body.correctness}")

        return

    def plot_keypoints(self, frame, bodies):
        if frame is None:
            print("Could not grab frame")

        for method_name, prediction_bodies in bodies.items():
            is_gt = (method_name == "ground_truth")
            
            # TODO - different color for each pd
            render(frame, prediction_bodies, self.LINES_BODY, score_thresh = 0.2, show_scores = False, show_bounding_box = False, show_numbering = True, isGroundTruth = is_gt)              
                
        cv2.imwrite(self.output, frame)
        #print("Saved:", os.path.abspath(filename))
        resized_image = cv2.resize(frame, (640, 480)) 
        cv2.imshow("Frame", resized_image)

        # Press 'q' to quit early
        if cv2.waitKey(0) & 0xFF == ord('q'):
            print("Quitting loop.")
            exit(0)

    def main_loop(self):
        render_out=True

        if self.input_type == "video":
            if self.singleFrameFromVideo >= 0:
                frame = get_frame_from_video(self.cap, self.singleFrameFromVideo)
                if frame is None:
                    exit(0)

                keypoint_list = self.get_frame_data(self.singleFrameFromVideo)
                bodies = self.update_body_format(keypoint_list)
                self.evaluate_frame(bodies)
                if render_out:
                    self.plot_keypoints(frame, bodies)                
            else:
                while True:
                    ok, frame = self.cap.read()
                    if not ok:
                        break

                    frame_number = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    print(f"Processing frame {frame_number}")

                    keypoint_list = self.get_frame_data(frame_number = frame_number)
                    bodies = self.update_body_format(keypoint_list)
                    self.evaluate_frame(bodies)
                    if render_out:
                        self.plot_keypoints(frame, bodies)