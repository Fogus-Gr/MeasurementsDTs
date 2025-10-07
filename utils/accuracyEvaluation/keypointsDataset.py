import json

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)
    
class KeypointsDataset:
    def __init__(self, json_file, source_name):
        self.data = load_json(json_file)
        self.source_name = source_name
        self.gt_fps = None
        
        # Organize data by frame for faster lookup
        self.by_frame = {}
        for entry in self.data:
            frame = entry["frame_number"]
            if frame not in self.by_frame:
                self.by_frame[frame] = []
            self.by_frame[frame].append(entry["keypoints"])

            if self.gt_fps is None and source_name == "ground_truth":
                fpsType = entry["fpsType"]
                if fpsType == "hd_29_97":
                    self.gt_fps = 29.97
                else:
                    print("Exiting... Not handling this ground truth fps")
                    exit(1)

    def get_frame(self, frame_number):
        """Return all detections for a given frame"""
        return self.by_frame.get(frame_number, [])