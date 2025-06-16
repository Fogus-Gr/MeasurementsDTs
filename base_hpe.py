from abc import ABC, abstractmethod
import cv2
import os
from collections import namedtuple
import glob
import time

from utils.visualizer import render
from utils.evaluator import append_COCO_format_json, append_COCO_format_csv, save_COCO_format_json, save_COCO_format_csv

class Body:
    def __init__(self, score, xmin, ymin, xmax, ymax, keypoints_score, keypoints, keypoints_norm):
        self.score = score # global/mean score 
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.keypoints_score = keypoints_score # individual scores of the keypoints
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
                enable_csv=False,
                save_image=False,
                save_video=False,
                score_thresh=0.2,
                show_scores = True,
                show_bounding_box = True,
                pd_w = 256,
                pd_h = 256):
        super().__init__()

        self.json = enable_json
        self.csv = enable_csv
        self.save_image = save_image
        self.save_video = save_video
        self.score_thresh = score_thresh
        self.show_scores = show_scores
        self.show_bounding_box = show_bounding_box
        
        self.img_w = 0
        self.img_h = 0
        self.pd_w = pd_w
        self.pd_h = pd_h
        self.current_image_file = ""

        self.start_time_of_experiment = time.time()
        self.input_file = os.path.basename(os.path.normpath(input_src))

        if self.json or self.save_image or self.save_video:
            if output_dir is not None:
                self.output_dir = output_dir
            else:
                self.output_dir = "out/"

            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

        if os.path.isdir(input_src):
            self.input_type = "directory"
            self.img_dir = input_src
            self.video_fps = 25
        elif input_src:
            if input_src.endswith('.jpg') or input_src.endswith('.png'):
                self.input_type = "image"
                self.img = cv2.imread(input_src)
                self.img_h, self.img_w = self.img.shape[:2]
                self.current_image_file = os.path.basename(input_src)
            elif input_src.startswith("http"):
                self.input_type = "ip_stream"
                
                print(f"Attempting to connect to IP stream at {input_src}...")

                # e.g. 60 tries * 1s = 60 seconds timeout
                max_retries = 60
                for attempt in range(max_retries):
                    self.cap = cv2.VideoCapture(input_src)
                    if self.cap.isOpened():
                        break
                    print(f"[{attempt+1}/{max_retries}] Stream not available, retrying in 1s...")
                    time.sleep(1)

                if not self.cap.isOpened():
                    raise ValueError(f"Failed to connect to video stream after {max_retries} attempts: {input_src}")

                # Give OpenCV a small buffer time to fetch metadata
                time.sleep(0.5)

                self.video_fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 25
                self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            else:
                if not input_src.isdigit():
                    self.input_type = "video"
                else:
                    input_src = int(input_src)
                    self.input_type = "webcam"
                self.cap = cv2.VideoCapture(input_src)
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_FOCUS, 0)
                self.video_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                self.img_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.img_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
            self.set_padding()
        else:
            raise ValueError("No valid input source provided")
            
        self.input_src = input_src  

        if (self.input_type == "directory" or self.input_type == "image") and self.save_video:
            raise ValueError("image input - video output not supported!")

        if self.save_video:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            filename = os.path.join(self.output_dir, "video.avi")
            self.output = cv2.VideoWriter(filename, fourcc, self.video_fps, (self.img_w, self.img_h))

    @abstractmethod
    def load_model(self):
        pass
    
    def main_loop(self):
        frame_number = 0

        if self.input_type == "image":
            self.process_frame(self.img, frame_number)

        elif self.input_type == "directory":
            # Get all image files from the directory
            image_files = glob.glob(os.path.join(self.img_dir, '*.[pjg][np][ge]*'))
            print(f"Found {len(image_files)} images in {self.img_dir}")

            # Sort files to ensure they are in alphanumeric order
            image_files = sorted(image_files)
            
            total_frames = len(image_files)
            for image_file in image_files:
                print(f"Processing {frame_number+1}/{total_frames}")
                self.img = cv2.imread(image_file)
                if self.img is None:
                    print(f"Failed to load image: {image_file}")
                    continue

                self.img_h, self.img_w = self.img.shape[:2]
                self.set_padding()
                self.process_frame(self.img, frame_number)

                frame_number += 1
        
        else:   # webcam, video or stream
            print("Starting processing video/webcam data. Press CTR+C to exit")
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break

                self.process_frame(frame, frame_number)

                frame_number += 1

        if self.json:
            save_COCO_format_json(os.path.join(self.output_dir, "COCOformat.json"))
        if self.csv:
            save_COCO_format_csv(os.path.join(self.output_dir, f"{self.model_type}-{self.start_time_of_experiment}-{self.input_file}.csv"))

    def process_frame(self, frame, frame_number):
        timestamp = time.time()

        padded = self.pad_and_resize(frame)
        predictions = self.run_model(padded)
        bodies = self.postprocess(predictions)

        if self.json:
            append_COCO_format_json(bodies, self.score_thresh, frame_number)
        if self.csv:
            append_COCO_format_csv(bodies, self.score_thresh, frame_number, timestamp)

        if self.save_image or self.save_video:
            # Ensure that LINES_BODY is defined in the child class
            if not hasattr(self, 'LINES_BODY'):
                raise ValueError("LINES_BODY is not defined in the child class.")
            
            render(frame, bodies, self.LINES_BODY, self.score_thresh, self.show_scores, self.show_bounding_box)

            if self.save_video:
                if not self.output.isOpened():
                    raise ValueError("Failed to open the video writer")
                self.output.write(frame)

            elif self.save_image:
                filename = os.path.join(self.output_dir, f"frame_{frame_number:04d}.jpg")
                cv2.imwrite(filename, frame)
    
    @abstractmethod
    def run_model(self, padded):
        pass

    @abstractmethod
    def postprocess(self, predictions):
        pass

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