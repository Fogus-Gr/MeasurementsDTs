from pathlib import Path
from utils.accuracyEvaluation.auc_evaluator import AUCEvaluator

def main():
    # === CONFIG ===
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    base = PROJECT_ROOT / "unit_tests" / "video2sec"

    gt_file = base / "all_body2DScenes_499_540.json"
    predictions_file_list = {
        "MoveNet": base / "pd_movenet.json",
        # "OpenPose": base / "pd_openpose.json",
        # "AlphaPose": base / "pd_alphapose.json",
    }

    input = base / "160422_ultimatum_hd_00_00_2s.mp4"
    last_frame_output = PROJECT_ROOT / "out" / "gt05_08.jpg"
    singleFrameFromVideo = -1
    frame_number_offset = 499   # IF VGA frame_number_offset = 105 else 0
  
    # === MAIN PROCESS ===
    auc_eval = AUCEvaluator(pck_alpha_threshold = 0.2, 
                            start_threshold = 0.45, 
                            stop_threshold  = 0.5, 
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
                            verbose = False)
    auc_eval.initialize()
    auc_eval.AUC()

if __name__ == "__main__":
    main()