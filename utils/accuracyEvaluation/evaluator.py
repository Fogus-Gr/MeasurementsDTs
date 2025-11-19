import cv2
import numpy as np
from base_hpe import Body
from utils.visualizer import render, draw_legend
from utils.accuracyEvaluation.keypointsDataset import KeypointsDataset
from utils.accuracyEvaluation.metrics.pck import PCKEvaluator
from utils.accuracyEvaluation.matching import Matcher

PALETTE = [
    (255, 0, 0),
    #(0, 255, 0), -> ground_truth
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (128, 0, 128),
    (255, 165, 0),
    (0, 128, 128),
]
    
def get_frame_from_video(cap, frame_number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    if not ret or frame is None:
        print("Could not grab frame.")
        frame = None

    cap.release()
    return frame

class Evaluator:
    def __init__(self, ground_truth_file, predictions_file_list: list, input_src, output, matching_method = "iou", pck_threshold = 0.2, confidence_threshold = 0.2, render_out = False, singleFrameFromVideo = -1, frame_number_offset = 0, verbose = False):
        print("Loading json files...")
        self.ground_truth = KeypointsDataset(ground_truth_file, "ground_truth")

        self.predictions = []
        for method, path in predictions_file_list.items():
            self.predictions.append(KeypointsDataset(path, method))

        print("Continuing process...")
        self.input_src = input_src
        self.output = output
        self.singleFrameFromVideo = singleFrameFromVideo

        self.pck_eval = PCKEvaluator(threshold_type="torso", alpha=pck_threshold)
        self.matcher = Matcher(method=matching_method)

        self.confidence_threshold = confidence_threshold

        self.render_out = render_out
        self.method_colors = {}  # method_name → BGR color tuple
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
                #print(f"self.video_fps: {self.video_fps}")
                self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.frame_number_adjustor = self.ground_truth.gt_fps / self.video_fps
        self.frame_number_offset = frame_number_offset
        self.verbose = verbose
        
    
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

                if not method_name == "ground_truth":
                    keypoints_score[keypoints_score < self.confidence_threshold] = 0.0

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

    def evaluate_frame(self, bodies):
        gt = bodies['ground_truth']
        pck_results = {}

        for method_name, prediction_bodies in bodies.items():
            if method_name == 'ground_truth':
                continue

            if not gt:
                continue

            matches = self.matcher.match(gt, prediction_bodies)
            pck_values = []

            for gt_body, pred_body in matches:
                pck, correctness, _ = self.pck_eval.evaluate(gt_body, pred_body)
                pred_body.correctness = correctness
                pck_values.append(pck)
                
            pck_results[method_name] = np.mean(pck_values) if pck_values else 0.0

        return pck_results

    def plot_keypoints(self, frame, bodies):
        if frame is None:
            print("Could not grab frame")

        for method_name, prediction_bodies in bodies.items():
            is_gt = (method_name == "ground_truth")
            
            color = (0, 255, 0) if is_gt else self._get_color_for_method(method_name)

            render(frame, 
                   prediction_bodies, 
                   self.LINES_BODY, 
                   score_thresh = 0.2, 
                   show_scores = False, 
                   show_bounding_box = False, 
                   show_numbering = True, 
                   isGroundTruth = is_gt, 
                   color_skeleton = color)              
                
        draw_legend(frame, self.method_colors)
        cv2.imwrite(self.output, frame)
        #print("Saved:", os.path.abspath(filename))
        resized_image = cv2.resize(frame, (2*640, 2*480)) 
        cv2.imshow("Frame", resized_image)

        # Press 'q' to quit early
        if cv2.waitKey(0) & 0xFF == ord('q'):
            print("Quitting loop.")
            exit(0)

    def get_frame_data(self, frame_number):
        results = {}

        adjusted_gt_frame_number = self.adjust_frame_number(frame_number)
        results["ground_truth"] = self.ground_truth.get_frame(adjusted_gt_frame_number)

        for pd in self.predictions:
            results[pd.source_name] = pd.get_frame(frame_number)

        return results
    
    def adjust_frame_number(self, frame_number: int) -> int:
        return int(round(self.frame_number_adjustor * frame_number)) + self.frame_number_offset


    def frame_generator(self):
        if self.input_type == "video":
            if self.singleFrameFromVideo >= 0:
                frame_number = self.singleFrameFromVideo
                frame = get_frame_from_video(self.cap, frame_number)
                if frame is None:
                    raise RuntimeError(f"Could not get frame {frame_number}")
                
                yield frame_number, frame
            else:
                while True:
                    ok, frame = self.cap.read()
                    if not ok:
                        break

                    frame_number = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    yield frame_number, frame
        else:
            raise NotImplementedError("Input selected not supported")
        
    def _get_color_for_method(self, method_name):
        if method_name not in self.method_colors:
            idx = len(self.method_colors) % len(PALETTE)
            self.method_colors[method_name] = PALETTE[idx]
        return self.method_colors[method_name]


    def main_loop(self):
        pck_per_method = {}

        try:
            for frame_number, frame in self.frame_generator():
                keypoint_list = self.get_frame_data(frame_number)
                bodies = self.update_body_format(keypoint_list)
                pck_results = self.evaluate_frame(bodies)

                if self.verbose:
                    pck_str = ""
                    if pck_results:
                        pck_str = "=> "
                        pck_str += ", ".join([f"{method}: {pck:.2f}" for method, pck in pck_results.items()])
                    print(f"Frame {frame_number} {pck_str}")

                for method, pck in pck_results.items():
                    if method not in pck_per_method:
                        pck_per_method[method] = []
                    pck_per_method[method].append(pck)

                if self.render_out:
                    self.plot_keypoints(frame, bodies)
        finally:
            if self.input_type == "video" and hasattr(self, "cap"):
                self.cap.release()
            cv2.destroyAllWindows()


        mean_dict = {}
        for method, vals in pck_per_method.items():
            mean_dict[method] = float(np.mean(vals))

        return mean_dict