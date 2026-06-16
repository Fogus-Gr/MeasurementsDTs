import os
import sys
import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
import torchvision.transforms.functional as F
from base_hpe import BaseHPE, Body, Padding
from types import SimpleNamespace

torch.set_num_threads(5)

try:
	from models.AlphaPose.detector.apis import get_detector
	from models.AlphaPose.alphapose.models import builder
	from models.AlphaPose.alphapose.utils.config import update_config
	from models.AlphaPose.alphapose.utils.detector import DetectionLoader
	from models.AlphaPose.alphapose.utils.transforms import flip, flip_heatmap, get_func_heatmap_to_coord
	from models.AlphaPose.alphapose.utils.vis import getTime
	from models.AlphaPose.alphapose.utils.webcam_detector import WebCamDetectionLoader
except ImportError as e:
    print('AlphaPose import error!')
    raise e

DEFAULT_CFG        = "models/AlphaPose/pretrained_models/256x192_res50_lr1e-3_1x.yaml"
DEFAULT_CHECKPOINT = "models/AlphaPose/pretrained_models/fast_res50_256x192.pth"

# Note: current input handles max 1 gpu - so no option fo gpus = "0,1" for example
DEVICE_TO_GPU = {
            "GPU": "0",
            "CPU": "-1"
        }

class AlphaPoseHPE(BaseHPE):
    LINES_BODY = [ 
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    def __init__(self, detbatch: int, cfg = DEFAULT_CFG, device = "GPU", posebatch = 4, detector = "yolo", 
                 checkpoint = DEFAULT_CHECKPOINT, sp = True, *args, **kwargs):
        # detbatch is now passed from main.py
        gpus = DEVICE_TO_GPU.get(device, "-1")
        self.cfg = cfg
        self.gpus = [int(i) for i in gpus.split(',')] if torch.cuda.device_count() >= 1 else [-1]
        self.device = torch.device("cuda:" + str(self.gpus[0]) if self.gpus[0] >= 0 else "cpu")
        self.detbatch = detbatch * len(self.gpus)
        self.posebatch = posebatch * len(self.gpus)
        self.detector = detector
        self.checkpoint = checkpoint
        self.sp = sp

        self.model_type = "alphapose"
        print(f"[INFO] Running AlphaPose on {self.device}")

        if not self.sp:
            torch.multiprocessing.set_start_method('forkserver', force=True)
            torch.multiprocessing.set_sharing_strategy('file_system')

        # No preprocessing needed - resizing/padding handled from the model (frame_preprocess)
        kwargs['pd_w'] = 0
        kwargs['pd_h'] = 0

        # Pass gpu_id to BaseHPE for PyNvCodec
        super().__init__(*args, gpu_id=self.gpus[0] if self.gpus[0] >= 0 else -1, **kwargs)


    def load_model(self):
        # Handle case where cfg might already be an EasyDict or a file path
        if isinstance(self.cfg, str):
            self.cfg = update_config(self.cfg)
        elif not hasattr(self.cfg, 'MODEL'):
            # If cfg is not a proper config dict, use default config file
            self.cfg = update_config(DEFAULT_CFG)
        qsize = 1024
        
        # Load detector model
        opt1 = SimpleNamespace(detector=self.detector, gpus=self.gpus, device=self.device)
        self.detector_model = get_detector(opt1)
        
        # For image/directory inputs, we still need to handle loading
        if self.input_type == "image" or self.input_type == "directory":
            inputpath = os.getcwd()
            if self.input_type == "image":
                input_src_dir = os.path.dirname(self.input_src)
                inputpath = os.path.join(inputpath, input_src_dir)
                self.input_src = os.path.basename(self.input_src)
            elif self.input_type == "directory":
                inputpath = os.path.join(inputpath, self.img_dir)
            
            opt2 = SimpleNamespace(device=self.device, sp=self.sp, inputpath=inputpath, tracking=False)
            self.det_loader = DetectionLoader([self.input_src], None, self.detector_model, self.cfg, opt2, batchSize=self.detbatch, mode=self.input_type, queueSize=qsize)
            self.det_worker = self.det_loader.start()
        else: # Video, webcam, or stream handled by BaseHPE
            self.det_loader = None # No need for DetectionLoader to manage input
            self.det_worker = None

        # Load pose model
        self.pose_model = builder.build_sppe(self.cfg.MODEL, preset_cfg=self.cfg.DATA_PRESET)

        print('Loading pose model from %s...' % (self.checkpoint,))
        self.pose_model.load_state_dict(torch.load(self.checkpoint, map_location=self.device))
        self.pose_dataset = builder.retrieve_dataset(self.cfg.DATASET.TRAIN)

        if len(self.gpus) > 1:
            self.pose_model = torch.nn.DataParallel(self.pose_model, device_ids=self.gpus).to(self.device)
        else:
            self.pose_model.to(self.device)
        self.pose_model.eval()

        self.runtime_profile = {
            'dt': [],
            'pt': [],
            'pn': []
        }

        # Define the transformation for pose estimation input
        # This should match the input requirements of your AlphaPose model
        # For example, if it expects 256x192, normalized, and (C, H, W)
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def run_model(self, frame_input):
        # frame_input can be a NumPy array (from OpenCV) or a PyTorch Tensor (from PyNvCodec)
        norm_type = 'softmax'
        flip = False
        profile = False

        with torch.no_grad():
            if self.det_loader: # For image/directory inputs, use DetectionLoader
                (inps, orig_img, im_name, boxes, scores, ids, cropped_boxes) = self.det_loader.frame_preprocess(frame_input)
                if orig_img is None:
                    return []
                orig_h, orig_w = orig_img.shape[:2]
            else: # For video/webcam/stream with PyNvCodec, frame_input is a GPU tensor
                # frame_input is already a torch.Tensor on GPU (RGB, H, W, C)
                if isinstance(frame_input, np.ndarray):
                    orig_img_tensor = torch.from_numpy(frame_input).to(self.device)
                else:
                    orig_img_tensor = frame_input.to(self.device)
                orig_h, orig_w = orig_img_tensor.shape[:2]
                
                # Use detector_model's image_preprocess if available, else fallback to manual preprocessing
                if self.det_loader and self.det_loader.detector_model:
                    detector_input = self.det_loader.detector_model.image_preprocess(orig_img_tensor.cpu().numpy())
                    detector_input = detector_input.to(self.device)
                else:
                    # Fallback: resize to expected input size (608) and normalize manually
                    import torchvision.transforms.functional as F
                    det_input_size = 608
                    resized_img_tensor = F.resize(orig_img_tensor.permute(2,0,1), (det_input_size, det_input_size), antialias=True)
                    detector_input = resized_img_tensor.float() / 255.0
                    detector_input = detector_input.unsqueeze(0).to(self.device)

                # Perform detection directly using the loaded detector model
                # The images_detection method expects a list of images and original dimensions
                # For a single image, it's a list with one item.
                # The output format of images_detection needs to be parsed.
                
                # Assuming self.detector_model.images_detection returns a list of dicts,
                # where each dict contains 'boxes', 'scores', 'ids', 'inps', 'cropped_boxes'
                # This is a simplification and might need adjustment based on actual detector API.
                
                # Call images_detection
                # orig_dim_list needs to be a tensor for YOLODetector
                orig_dim_tensor = torch.FloatTensor([(orig_w, orig_h, orig_w, orig_h)]).to(self.device)
                det_results = self.detector_model.images_detection(detector_input, orig_dim_tensor)
                
                # Parse detection results
                # det_results is a tensor of shape (n, (batch_idx, x1, y1, x2, y2, c, s, idx of cls))
                if isinstance(det_results, int) or det_results.shape[0] == 0:
                    return []
                
                # Filter for human class (idx of cls == 0 for COCO) and current batch_idx (which is 0)
                # Assuming human class index is 0 based on yolo_api.py's write_results
                human_detections = det_results[(det_results[:, 0] == 0) & (det_results[:, 7] == 0)]

                if human_detections.nelement() == 0:
                    return []

                # Extract boxes, scores, ids
                boxes = human_detections[:, 1:5] # x1, y1, x2, y2
                scores = human_detections[:, 6] # class score
                ids = torch.arange(1, boxes.shape[0] + 1, device=self.device) # Generate dummy IDs for now
                cropped_boxes = boxes # For now, cropped_boxes are the same as boxes

                # --- Implement GPU-accelerated cropping and resizing for pose model ---
                inps_list = []
                pose_input_size = self.cfg.MODEL.get("IMAGE_SIZE", [256, 192]) if hasattr(self.cfg.MODEL, "get") else [256, 192]
                
                # orig_img_tensor is (H, W, C) RGB
                # We need to permute to (C, H, W) for F.crop and F.resize
                orig_img_tensor_chw = orig_img_tensor.permute(2, 0, 1)

                for i in range(boxes.shape[0]):
                    box = boxes[i]
                    x1, y1, x2, y2 = box.int().tolist()

                    # Ensure coordinates are within image bounds
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(orig_w, x2), min(orig_h, y2)
                    
                    if x2 <= x1 or y2 <= y1: # Skip invalid boxes
                        continue

                    # Cropping on GPU
                    cropped_person = F.crop(orig_img_tensor_chw, y1, x1, y2-y1, x2-x1) # (C, H, W)
                    
                    # Resizing on GPU
                    resized_person = F.resize(cropped_person, pose_input_size[::-1], antialias=True) # F.resize expects (H, W) for size

                    # Apply normalization (self.transform)
                    # self.transform is a Compose of ToTensor and Normalize.
                    # ToTensor expects a PIL Image or NumPy array.
                    # We need a GPU-aware normalization.
                    # For now, let's apply normalization manually on GPU.
                    
                    # Convert to float and normalize [0,1]
                    normalized_person = resized_person.float() / 255.0
                    
                    # Apply mean/std normalization on GPU
                    mean = torch.tensor([0.485, 0.456, 0.406], device=self.device).view(3, 1, 1)
                    std = torch.tensor([0.229, 0.224, 0.225], device=self.device).view(3, 1, 1)
                    normalized_person = (normalized_person - mean) / std
                    
                    inps_list.append(normalized_person)
                
                if inps_list:
                    inps = torch.stack(inps_list).to(self.device)
                else:
                    inps = torch.empty((0, 3, pose_input_size[1], pose_input_size[0]), device=self.device)

                if inps.nelement() == 0:
                    return []

            # Pose Estimation (common for both paths)
            # 'inps' should now be ready for the pose model
            if inps is None:
                return []

            # Pose Estimation (common for both paths)
            # 'inps' should now be ready for the pose model
            if inps is None:
                return []

            try:
                inps = inps.to(self.device)
            except Exception as e:
                print(f"Error moving tensor to device: {e}")
                return []
            
            datalen = inps.size(0)
            leftover = 0
            batchSize = self.posebatch
            if (datalen) % batchSize:
                leftover = 1
            num_batches = datalen // batchSize + leftover
            hm = []
            for j in range(num_batches):
                inps_j = inps[j * batchSize:min((j + 1) * batchSize, datalen)]
                if flip:
                    inps_j = torch.cat((inps_j, flip(inps_j)))
                hm_j = self.pose_model(inps_j)
                if flip:
                    hm_j_flip = flip_heatmap(hm_j[int(len(hm_j) / 2):], self.pose_dataset.joint_pairs, shift=True)
                    hm_j = (hm_j[0:int(len(hm_j) / 2)] + hm_j_flip) / 2
                hm.append(hm_j)
            hm = torch.cat(hm)
            if profile:
                ckpt_time, pose_time = getTime(ckpt_time)
                self.runtime_profile['pt'].append(pose_time)
            hm = hm.cpu()

            self.heatmap_to_coord = get_func_heatmap_to_coord(self.cfg)

            if boxes is None or boxes.nelement() == 0:
                return []
            
            keypoints_array = []
            for j in range(hm.shape[0]):
                bbox = cropped_boxes[j].tolist()
                hm_size = hm[j].shape[-2:]
                pose_coord, pose_score = self.heatmap_to_coord(hm[j], bbox, hm_shape=hm_size, norm_type=norm_type)

                pose_coord[:, 0] /= orig_w
                pose_coord[:, 1] /= orig_h
                
                person_keypoints = np.hstack((pose_coord, pose_score.reshape(-1, 1)))
                keypoints_array.append((person_keypoints, bbox))
            
            return keypoints_array
        
    def postprocess(self, predictions):
        bodies = []

        for person_keypoints, det_box in predictions:
            normalized_kps = person_keypoints[:, :2]    # x, y coordinates normalized in [0,1]
            scores = person_keypoints[:, 2]
            valid_scores = scores > self.score_thresh

            if np.any(valid_scores):
                valid_kps = normalized_kps[valid_scores]

                # Rescale normalized keypoints to padded dimensions
                keypoints = valid_kps * np.array([self.padding.padded_w, self.padding.padded_h])
                keypoints = np.array(keypoints)

                # Use detector bounding box scaled to padded-frame coordinates
                if det_box is not None:
                    scale_x = self.padding.padded_w / self.img_w if self.img_w > 0 else 1.0
                    scale_y = self.padding.padded_h / self.img_h if self.img_h > 0 else 1.0
                    x1, y1, x2, y2 = det_box
                    xmin = int(x1 * scale_x)
                    ymin = int(y1 * scale_y)
                    xmax = int(x2 * scale_x)
                    ymax = int(y2 * scale_y)
                else:
                    # Fallback: derive from visible keypoints
                    print("[WARNING] AlphaPose: no detector box, falling back to keypoint bbox", file=sys.stderr)
                    kp_min = valid_kps.min(axis=0)
                    kp_max = valid_kps.max(axis=0)
                    xmin = int(kp_min[0] * self.padding.padded_w)
                    ymin = int(kp_min[1] * self.padding.padded_h)
                    xmax = int(kp_max[0] * self.padding.padded_w)
                    ymax = int(kp_max[1] * self.padding.padded_h)

                body = Body(
                    score=np.mean(scores[valid_scores]),  # Average score of valid keypoints
                    xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
                    keypoints_score=scores[valid_scores],
                    keypoints=keypoints.astype(float),
                    keypoints_norm=normalized_kps
                )
                bodies.append(body)

        return bodies
    
    # AlphaPose expects original resolution inputs
    # Override - No padding, no resizing
    def set_padding(self):
       
        self.padding = Padding(0, 0, self.img_w, self.img_h)
    
    def pad_and_resize(self, frame):
        return frame
