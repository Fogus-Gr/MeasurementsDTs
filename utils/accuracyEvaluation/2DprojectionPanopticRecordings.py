import os
import json
import numpy as np
from glob import glob
import argparse
from utils.constants import LABELED_VISIBLE, NOT_LABELED

selected_cam = (0, 0)  # example: camera panel=0, node=5

# === CONFIG ===
data_path = "/mnt/data/panoptic-toolbox/scripts/171204_pose1"
calib_file = os.path.join(data_path, "calibration_171204_pose1.json")
input_3d_path = os.path.join(data_path, "hdPose3d_stage1_coco19")

# Input Options
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["single", "multiple"], default="single",
                    help="Save either one big JSON file ('single') or one file per frame ('multiple')")
args = parser.parse_args()

# Output folder for 2D json
panel, node = selected_cam
cam_name = f"{panel:02d}_{node:02d}"
base_out_dir = "projected_2d"
output_2d_path = os.path.join(base_out_dir, f"{cam_name}_{args.mode}")
os.makedirs(output_2d_path, exist_ok=True)
print("Saving 2D projections to:", output_2d_path)

# === Mapping Table ===
# mapping Panoptic indices → COCO indices
panoptic_to_coco = {
    0: 1,   # Nose
    1: 15,  # Left Eye
    2: 17,  # Right Eye
    3: 16,  # Left Ear
    4: 18,  # Right Ear
    5: 3,   # Left Shoulder
    6: 9,   # Right Shoulder
    7: 4,   # Left Elbow
    8: 10,  # Right Elbow
    9: 5,   # Left Wrist
    10: 11, # Right Wrist
    11: 6,  # Left Hip
    12: 12, # Right Hip
    13: 7,  # Left Knee
    14: 13, # Right Knee
    15: 8,  # Left Ankle
    16: 14, # Right Ankle
}

# Convert Panoptic joints19 (x,y,c) to COCO joints17 (x,y,c)
def panoptic_to_coco17(joints19, img_w, img_h):
    coco17 = [0.0] * (17*3)
    for coco_idx, pan_idx in panoptic_to_coco.items():
        x, y, c = joints19[pan_idx*3: pan_idx*3+3]

        if 0 <= x < img_w and 0 <= y < img_h:
            v = LABELED_VISIBLE
        else:
            v = NOT_LABELED

        coco17[coco_idx*3:coco_idx*3+3] = [x, y, v]
    return coco17

# === panutils.py ===
#import panutils  # from PanopticStudio Toolbox
def projectPoints(X, K, R, t, Kd):
    """ Projects points X (3xN) using camera intrinsics K (3x3),
    extrinsics (R,t) and distortion parameters Kd=[k1,k2,p1,p2,k3].
    
    Roughly, x = K*(R*X + t) + distortion
    
    See http://docs.opencv.org/2.4/doc/tutorials/calib3d/camera_calibration/camera_calibration.html
    or cv2.projectPoints
    """    
    x = np.asarray(R@X + t)
    
    x[0:2,:] = x[0:2,:]/x[2,:]
    
    r = x[0,:]*x[0,:] + x[1,:]*x[1,:]
    
    x[0,:] = x[0,:]*(1 + Kd[0]*r + Kd[1]*r*r + Kd[4]*r*r*r) + 2*Kd[2]*x[0,:]*x[1,:] + Kd[3]*(r + 2*x[0,:]*x[0,:])
    x[1,:] = x[1,:]*(1 + Kd[0]*r + Kd[1]*r*r + Kd[4]*r*r*r) + 2*Kd[3]*x[0,:]*x[1,:] + Kd[2]*(r + 2*x[1,:]*x[1,:])

    x[0,:] = K[0,0]*x[0,:] + K[0,1]*x[1,:] + K[0,2]
    x[1,:] = K[1,0]*x[0,:] + K[1,1]*x[1,:] + K[1,2]
    
    return x

# === LOAD CALIBRATION ===
with open(calib_file, "r") as f:
    calib = json.load(f)

cameras = {(c['panel'], c['node']): c for c in calib['cameras']}
cam = cameras[selected_cam]

# Convert calibration params to numpy
K = np.array(cam["K"])
R = np.array(cam["R"])
t = np.array(cam["t"]).reshape(3, 1)
distCoef = np.array(cam["distCoef"])
resolution_w, resolution_h = np.array(cam["resolution"]) # [x,y]

# === PROCESS ALL 3D FILES ===
json_files = sorted(glob(os.path.join(input_3d_path, "body3DScene_*.json")))

original_time = None
image_id = 0
all_frames_json_data = []
for jf in json_files:
    with open(jf, "r") as f:
        frame_data = json.load(f)

    # parse frame index from filename (e.g. "body3DScene_00000130.json" → 130)
    frame_str = os.path.splitext(os.path.basename(jf))[0].split("_")[-1]
    frame_idx = int(frame_str)

    if original_time is None:
        original_time = frame_data["univTime"]

    new_bodies = []
    for body in frame_data["bodies"]:
        skel3d = np.array(body["joints19"]).reshape((-1, 4))  # (19, 4)
        xyz = skel3d[:, :3].T  # shape (3, 19)
        conf = skel3d[:, 3]    # shape (19,)

        # project 3D → 2D
        pts2d = projectPoints(xyz, K, R, t, distCoef)  # shape (2, 19)

        # pack back into flat array [x1,y1,c1, x2,y2,c2, ...]
        joints2d = []
        for i in range(pts2d.shape[1]):
            x, y, c = float(pts2d[0, i]), float(pts2d[1, i]), float(conf[i])

            joints2d.extend([x, y, c])

        new_bodies.append({
            "id": body["id"],
            "keypoints19_2d": joints2d
        })

    # build new JSON
    out_json = []
    for body in new_bodies:
        out_json.append({
            "image_id": image_id,
            "frame_number": frame_idx,
            "category_id": 1,
            "person_id": body["id"],
            "keypoints": panoptic_to_coco17(body["keypoints19_2d"], resolution_w, resolution_h),
            "keypoint_format": "coco17",
            "univTime": frame_data["univTime"],
            "fpsType": frame_data["fpsType"]
        })

        

    # save
    if args.mode == "multiple":
        out_name = os.path.basename(jf).replace("body3DScene_", "body2DScene_")
        out_file = os.path.join(output_2d_path, out_name)
        with open(out_file, "w") as f:
            json.dump(out_json, f)

    elif args.mode == "single":
        all_frames_json_data.extend(out_json)

    image_id += 1

if args.mode == "single":
    out_file = os.path.join(output_2d_path, "all_body2DScenes.json")
    with open(out_file, "w") as f:
        json.dump(all_frames_json_data, f)
