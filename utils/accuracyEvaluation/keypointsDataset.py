import json

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)
    
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