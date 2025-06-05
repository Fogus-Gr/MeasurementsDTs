import os
import numpy as np
import torch
from base_hpe import BaseHPE, Body, Padding
from types import SimpleNamespace

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

class AlphaPoseHPE(BaseHPE):
    LINES_BODY = [ 
        [4,2], [2,0], [0,1], [1,3],
        [10,8], [8,6], [6,5], [5,7], [7,9],
        [6,12], [12,11], [11,5],
        [12,14], [14,16], [11,13], [13,15]
    ]

    def __init__(self, cfg = DEFAULT_CFG, gpus = "0", detbatch = 1, posebatch = 32, detector = "yolo", 
                 checkpoint = DEFAULT_CHECKPOINT, sp = True, *args, **kwargs):
        self.cfg = cfg
        self.gpus = [int(i) for i in gpus.split(',')] if torch.cuda.device_count() >= 1 else [-1]
        self.device = torch.device("cuda:" + str(self.gpus[0]) if self.gpus[0] >= 0 else "cpu")
        self.detbatch = detbatch * len(self.gpus)
        self.posebatch = posebatch * len(self.gpus)
        self.detector = detector
        self.checkpoint = checkpoint
        self.sp = sp

        self.model_type = "alphapose"

        if not self.sp:
            torch.multiprocessing.set_start_method('forkserver', force=True)
            torch.multiprocessing.set_sharing_strategy('file_system')

        # No preprocessing needed - resizing/padding handled from the model (frame_preprocess)
        kwargs['pd_w'] = 0
        kwargs['pd_h'] = 0

        super().__init__(*args, **kwargs)


    def load_model(self):
        self.cfg = update_config(self.cfg)
        qsize = 1024
        
        # Load detection loader
        if self.input_type == 'webcam':
            opt1 = SimpleNamespace(detector=self.detector, gpus=self.gpus, device=self.device)
            opt2 = SimpleNamespace(tracking=False, sp=self.sp)
            self.det_loader = WebCamDetectionLoader(self.input_src, self.cap, get_detector(opt1), self.cfg, opt2, queueSize=1)
            det_worker = self.det_loader.start()
        else:
            inputpath = os.getcwd()

            if self.input_type == "image":
                self.cap = ""
                input_src_dir = os.path.dirname(self.input_src)  # Extracts 'frames_pair'
                inputpath = os.path.join(inputpath, input_src_dir)
                self.input_src = os.path.basename(self.input_src)
            elif self.input_type == "directory":
                self.cap = ""
                inputpath = os.path.join(inputpath, self.img_dir)
            elif self.input_type == "video":
                input_src_dir = os.path.dirname(self.input_src)
                inputpath = os.path.join(inputpath, input_src_dir)
                self.input_src = os.path.basename(self.input_src)
            
            opt1 = SimpleNamespace(detector=self.detector, gpus=self.gpus, device=self.device)
            opt2 = SimpleNamespace(device=self.device, sp=self.sp, inputpath=inputpath, tracking=False)
            self.det_loader = DetectionLoader([self.input_src], self.cap, get_detector(opt1), self.cfg, opt2, batchSize=self.detbatch, mode=self.input_type, queueSize=qsize)
            det_worker = self.det_loader.start()

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

    def run_model(self, padded):
        # TODO - AlphaPose can handle multiple image with parallelization, here we pass one-one even in directories
        norm_type = 'softmax'  # Default normalization (update based on cfg)
        flip = False
        profile = False

        orig_h = 0
        orig_w = 0

        # Specific inference for AlphaPose
        batchSize = self.posebatch
        if flip:
            batchSize = int(batchSize / 2)
        with torch.no_grad():
                (inps, orig_img, im_name, boxes, scores, ids, cropped_boxes) = self.det_loader.frame_preprocess(padded)
                
                if orig_img is None:
                    return []

                orig_h, orig_w = orig_img.shape[:2]
                
                # Pose Estimation
                inps = inps.to(self.device)
                datalen = inps.size(0)
                leftover = 0
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

                # TODO - This should be done in postprocess
                self.heatmap_to_coord = get_func_heatmap_to_coord(self.cfg)

                if boxes is None or boxes.nelement() == 0:
                    return []
                
                keypoints_array = []
                for j in range(hm.shape[0]):
                    bbox = cropped_boxes[j].tolist()
                    hm_size = hm[j].shape[-2:]  # Heatmap dimensions
                    pose_coord, pose_score = self.heatmap_to_coord(hm[j], bbox, hm_shape=hm_size, norm_type=norm_type)

                    # Normalize coordinates to [0,1] range
                    pose_coord[:, 0] /= orig_w
                    pose_coord[:, 1] /= orig_h
                    
                    # Combine coordinates and scores into a single array
                    person_keypoints = np.hstack((pose_coord, pose_score.reshape(-1, 1)))
                    keypoints_array.append(person_keypoints)
                
                return keypoints_array
        
    def postprocess(self, predictions):
        bodies = []

        for person_keypoints in predictions:
            normalized_kps = person_keypoints[:, :2]    # x, y coordinates normalized in [0,1]
            scores = person_keypoints[:, 2]
            valid_scores = scores > self.score_thresh

            if np.any(valid_scores):
                valid_kps = normalized_kps[valid_scores]

                # Calculate bounding box in normalized coordinates - TODO note: this is not calculated by the model
                xmin, ymin = valid_kps.min(axis=0)
                xmax, ymax = valid_kps.max(axis=0)
                
                # Rescale normalized keypoints to padded dimensions
                keypoints = valid_kps * np.array([self.padding.padded_w, self.padding.padded_h])
                keypoints = np.array(keypoints)
                
                body = Body(
                    score=np.mean(scores[valid_scores]),  # Average score of valid keypoints
                    xmin=int(xmin * self.padding.padded_w), ymin=int(ymin * self.padding.padded_h),
                    xmax=int(xmax * self.padding.padded_w), ymax=int(ymax * self.padding.padded_h),
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