import argparse
import sys
from pathlib import Path
from utils.accuracyEvaluation.auc_evaluator import AUCEvaluator
from utils.accuracyEvaluation.apar_evaluator import APAREvaluator

def parse_arguments():
        parser = argparse.ArgumentParser()
        parser.add_argument("--method", type=str, required=True, choices=['auc', 'apar'])

        parser.add_argument('--gt_file',     type=str, required=True,            help="Path to json file to be used as ground truth keypoints")
        parser.add_argument('--pd_files',              required=True, nargs='+', help="List of paths to json files (e.g., --pd_files path/a.json path/b.json)")
        parser.add_argument('--input_video', type=str, required=True,            help="Path to video file to use as input")
        
        parser.add_argument("--last_frame_output",    type=str,   default='None',                            help="Path to directory where last output image will be saved")          
        parser.add_argument("--matching",             type=str,   default='iou', choices=['iou', 'keypoint'])
        parser.add_argument("--confidence_threshold", type=float, default=None,                              help="Only for AUC. APAR set's it to 0.")
        parser.add_argument("--frame",                type=int,   default=-1,                                help="Evaluate single frame from video")
        parser.add_argument("--frame_offset",         type=int,   default=0,                                 help="If spesific camera isn't synchronized with ground truth frame 0")

        parser.add_argument("--start_threshold", type=float)
        parser.add_argument("--stop_threshold",  type=float)
        parser.add_argument("--step_threshold",  type=float)
        
        parser.add_argument('-v', '--verbose', action='store_true')
        parser.add_argument('--render',        action='store_true')
        
        return parser

def get_accuracy_method(args):
    # Prepare the clean arguments
    kwargs = base_args(args)
    
    # Initialize the correct class using **unpacking
    if args.method == 'auc':
        return AUCEvaluator(**kwargs)
    elif args.method == 'apar':
        return APAREvaluator(**kwargs)
    else:
        raise ValueError(f"Unknown method: {args.method}")

def base_args(args):
    # Example: ['dir/pd_movenet.json'] -> {'pd_movenet': 'dir/pd_movenet.json'}
    predictions_dict = {}
    for file_path in args.pd_files:
        p = Path(file_path)
        # .stem gives the filename without extension (e.g., "pd_movenet")
        key_name = p.stem 
        predictions_dict[key_name] = str(p)
        
    args_list = {
        "ground_truth_file": args.gt_file, 
        "predictions_file_list": predictions_dict, 
        "input_src": args.input_video, 
        "last_frame_output": args.last_frame_output,
        "matching_method": args.matching,
        "confidence_threshold": args.confidence_threshold, 
        "start_threshold": args.start_threshold,
        "stop_threshold": args.stop_threshold,
        "step_threshold": args.step_threshold,
        "render_out": args.render, 
        "singleFrameFromVideo": args.frame, 
        "frame_number_offset": args.frame_offset, 
        "verbose": args.verbose
    }
    
    # Create a new dict excluding None values for those specific keys
    #threshold_keys = ['start_threshold', 'stop_threshold', 'step_threshold']
    clean_kwargs = {
        k: v for k, v in args_list.items() 
        #if k not in threshold_keys or v is not None
        if v is not None and v != 'None'
    }
    
    return clean_kwargs

def run_default_test():
    print(">>> No arguments provided. Running DEBUG Test Case...")
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # === CONFIG ===
    PROJECT_ROOT = Path(__file__).resolve().parent
    base = PROJECT_ROOT / "unit_tests" / "video2sec"

    gt_file = str(base / "all_body2DScenes_499_540.json")
    predictions_file_list = {
        "MoveNet": str(base / "pd_movenet.json"),
    }

    input = str(base / "160422_ultimatum_hd_00_00_2s.mp4")
    last_frame_output = str(PROJECT_ROOT / "out" / "gt05_08.jpg")

    singleFrameFromVideo = -1
    frame_number_offset = 499   # IF VGA frame_number_offset = 105 else 0
  
    # === MAIN PROCESS ===
    auc_eval = AUCEvaluator(start_threshold = 0.0, 
                            stop_threshold  = 0.3, 
                            step_threshold  = 0.1,
                            ground_truth_file = gt_file, 
                            predictions_file_list = predictions_file_list, 
                            input_src = input, 
                            last_frame_output = last_frame_output, 
                            matching_method = "iou", 
                            confidence_threshold = 0.2, 
                            render_out = True, 
                            singleFrameFromVideo = singleFrameFromVideo, 
                            frame_number_offset = frame_number_offset, 
                            verbose = True)
    auc_eval.initialize()
    auc_eval.AUC()

def main():
    # Check if the script was run without arguments
    if len(sys.argv) == 1:
        run_default_test()
        return
    
    parser = parse_arguments()
    args = parser.parse_args()

    evaluator = get_accuracy_method(args)
    evaluator.initialize()
 
    if args.method == 'auc':
        auc_scores, pck_values, thresholds = evaluator.AUC()
    elif args.method == 'apar':
        results = evaluator.APAR()
        
        # --- PRINTING ---
        print("\n" + "="*30)
        print(f"{'Method':<20} | {'mAP':<8} | {'mAR':<8}")
        print("-" * 40)
        
        for method_name, metrics in results.items():
            # Get values (assuming they are floats 0.0-1.0)
            map_val = metrics['mAP']
            mar_val = metrics['mAR']
            
            # Print formatted row
            print(f"{method_name:<20} | {map_val:.4f}   | {mar_val:.4f}")
        
        print("="*30 + "\n")

if __name__ == "__main__":
    main()