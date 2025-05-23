import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from movenet_hpe import MoveNetHPE
from openvino_base_hpe import OpenVINOBaseHPE
from alphapose_hpe import AlphaPoseHPE

def main():
    parser = parse_arguments()
    args = parser.parse_args()

    hpe = get_hpe_method(args)
    hpe.load_model()
    hpe.main_loop()

def parse_arguments():
        parser = argparse.ArgumentParser()
        parser.add_argument('--method', type=str, required=True, choices=['openpose', 'alphapose', 'movenet', 'hrnet'])
        parser.add_argument('--input', type=str, default='0', help="Path to video or image file to use as input (default=%(default)s)")
        parser.add_argument("--output_dir", type=str, help="Path to directory where output files will be saved")          
        parser.add_argument("--json", action="store_true", help="Enable export keypoints to a single json file")
        parser.add_argument("--save_video", action="store_true", help="Save resutls into a video file")
        parser.add_argument("--save_image", action="store_true", help="Save image with keypoints")
        
        return parser

def get_hpe_method(args):
    name = args.method.lower()
    if name == 'movenet':
        return MoveNetHPE(input_src = args.input, output_dir=args.output_dir, enable_json=args.json, save_image=args.save_image, save_video=args.save_video)
    elif name == 'alphapose':
        return AlphaPoseHPE(input_src = args.input, output_dir=args.output_dir, enable_json=args.json, save_image=args.save_image, save_video=args.save_video)
    elif name == 'openpose':
        return OpenVINOBaseHPE(model_type='openpose', input_src = args.input, output_dir=args.output_dir, enable_json=args.json, save_image=args.save_image, save_video=args.save_video)
    elif name == 'hrnet':
        return OpenVINOBaseHPE(model_type='higherhrnet', input_src = args.input, output_dir=args.output_dir, enable_json=args.json, save_image=args.save_image, save_video=args.save_video)
    else:
        raise ValueError(f"Unknown method: {name}")

if __name__ == "__main__":
    main()