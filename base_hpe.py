from abc import ABC, abstractmethod
import cv2
import numpy as np
import os
from collections import namedtuple

class Body:
    def __init__(self, score, xmin, ymin, xmax, ymax, keypoints_score, keypoints, keypoints_norm):
        self.score = score # global score - TODO -> not used
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.keypoints_score = keypoints_score # scores of the keypoints
        self.keypoints_norm = keypoints_norm # keypoints normalized ([0,1]) coordinates (x,y) in the input image
        self.keypoints = keypoints # keypoints coordinates (x,y) in pixels in the input image

# Padding (all values are in pixel) :
# w (resp. h): horizontal (resp. vertical) padding on the source image to make its ratio same as Movenet model input. 
#               The padding is done on one side (bottom or right) of the image.
# padded_w (resp. padded_h): width (resp. height) of the image after padding
Padding = namedtuple('Padding', ['w', 'h', 'padded_w',  'padded_h'])

class BaseHPE(ABC):
    input_type = None
    output_dir = ""

    def __init__(self, input_src=None,
                output_dir=None,
                enable_json=False,
                save_image=False,
                show_image=False,
                score_thresh=0.2,
                show_scores = True,
                show_bounding_box = True):
        super().__init__()

        self.json = enable_json
        self.save_image = save_image
        self.show_image = show_image
        self.score_thresh = score_thresh
        self.show_scores = show_scores
        self.show_bounding_box = show_bounding_box
        
        self.img_w = 0
        self.img_h = 0
        self.pd_w = 256
        self.pd_h = 256
        self.current_image_file = ""

        if self.json or self.save_image:
            if output_dir is not None:
                self.output_dir = output_dir
            else:
                self.output_dir = "out/"

            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

        if os.path.isdir(input_src):
            self.input_type = "directory"
            self.img_dir = input_src
        elif input_src:
            if input_src.endswith('.jpg') or input_src.endswith('.png'):
                self.input_type = "image"
                self.img = cv2.imread(input_src)
                self.img_h, self.img_w = self.img.shape[:2]
                self.current_image_file = os.path.basename(input_src)
            else:
                if not input_src.isdigit():
                    self.input_type = "video"
                else:
                    input_src = int(input_src)
                    self.input_type = "webcam"
                self.cap = cv2.VideoCapture(input_src)
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_FOCUS, 0)
                self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
            self.set_padding()
        else:
            raise ValueError("No valid input source provided")
            
        self.input_src = input_src  

    @abstractmethod
    def load_model(self):
        pass
    
    def main_loop(self):
        if self.input_type == "image":
            self.process_frame(self.img)

    def process_frame(self, frame):
        padded = self.pad_and_resize(frame)
        predictions = self.run_model(padded)
        bodies = self.postprocess(predictions)

        if self.save_image or self.show_image:
            self.render(frame, bodies)

            if self.input_type == "image" or self.input_type == "directory":
                if self.save_image:
                    frame_id = 0
                    filename = os.path.join(self.output_dir, f"frame_{frame_id:04d}.jpg")
                    cv2.imwrite(filename, frame)
    
    @abstractmethod
    def run_model(self, padded):
        pass

    @abstractmethod
    def postprocess(self, predictions):
        pass

    def render(self, frame, bodies):
        thickness = 3 
        color_skeleton = (255, 180, 90)
        color_box = (0,255,255)

        # Ensure that LINES_BODY is defined in the child class
        if not hasattr(self, 'LINES_BODY'):
            raise ValueError("LINES_BODY is not defined in the child class.")

        for body in bodies:                
            # Draw skeleton lines
            lines = []
            for line in self.LINES_BODY:
                # Check if keypoints in line exist and have valid scores
                if (len(body.keypoints) > line[0] and len(body.keypoints) > line[1] and 
                    len(body.keypoints_score) > line[0] and len(body.keypoints_score) > line[1] and 
                    body.keypoints_score[line[0]] > self.score_thresh and 
                    body.keypoints_score[line[1]] > self.score_thresh):
                    
                    # Map keypoint positions to integer coordinates for drawing
                    point_coords = [list(map(int, body.keypoints[point])) for point in line]
                    lines.append(np.array(point_coords))
            
            # Draw all valid skeleton lines
            cv2.polylines(frame, lines, False, color_skeleton, 2, cv2.LINE_AA)
            
            # TODO - I think coloring works correctly only for Movenet
            for i,x_y in enumerate(body.keypoints):
                if body.keypoints_score[i] > self.score_thresh:
                    if i % 2 == 1:
                        color = (0,255,0) 
                    elif i == 0:
                        color = (0,255,255)
                    else:
                        color = (0,0,255)
                    cv2.circle(frame, (int(x_y[0]), int(x_y[1])), 4, color, -11)

                    if self.show_scores:
                        score_text = f"{body.keypoints_score[i]:.1f}"
                        cv2.putText(frame, 
                                score_text, 
                                (int(x_y[0]) + 5, int(x_y[1]) - 5),  # Offset slightly from the circle
                                cv2.FONT_HERSHEY_SIMPLEX, 
                                0.4,  # Font scale
                                color,  # Use the same color as the keypoint
                                1,  # Thickness
                                cv2.LINE_AA)

            if self.show_bounding_box:
                cv2.rectangle(frame, (body.xmin, body.ymin), (body.xmax, body.ymax), color_box, thickness)

    # Define the padding
    # Note we don't center the source image. The padding is applied
    # on the bottom or right side. That simplifies a bit the calculation
    # when depadding
    def set_padding(self):
        if self.img_w / self.img_h > self.pd_w / self.pd_h:
            pad_h = int(self.img_w * self.pd_h / self.pd_w - self.img_h)
            self.padding = Padding(0, pad_h, self.img_w, self.img_h + pad_h)
        else:
            pad_w = int(self.img_h * self.pd_w / self.pd_h - self.img_w)
            self.padding = Padding(pad_w, 0, self.img_w + pad_w, self.img_h)

    # Pad and resize the image to prepare for the model input.
    def pad_and_resize(self, frame):
        padded = cv2.copyMakeBorder(frame, 0, self.padding.h, 0, self.padding.w, cv2.BORDER_CONSTANT)
        padded = cv2.resize(padded, (self.pd_w, self.pd_h), interpolation=cv2.INTER_AREA)

        return padded