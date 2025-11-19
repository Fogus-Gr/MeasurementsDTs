from utils.accuracyEvaluation.evaluator import Evaluator
from utils.accuracyEvaluation.metrics.pck import draw_curve
import numpy as np

def AUC(gt_file, predictions_file_list, input, output, singleFrameFromVideo, frame_number_offset, confidence_threshold = 0.2, start_thres = 0, stop_thres  = 0.5, step_thres  = 0.1):#, step_thres  = 0.01):
    print("Confidence_threshold: {confidence_threshold}")
    thresholds = np.linspace(start_thres, stop_thres, int((stop_thres - start_thres) / step_thres) + 1)
    pck_values = []

    for t in thresholds:
        print(f"PCK_threshold: {t}")
        ev = Evaluator(ground_truth_file = gt_file, 
                   predictions_file_list = predictions_file_list, 
                   input_src=input, 
                   output=output, 
                   matching_method="iou",
                   pck_threshold = t,
                   confidence_threshold = confidence_threshold,
                   render_out = False,
                   singleFrameFromVideo=singleFrameFromVideo, 
                   frame_number_offset = frame_number_offset,
                   verbose = False)
        mean_dict = ev.main_loop()
        pck_values.append(mean_dict)
        print(f"PCK = {mean_dict}")

    print("Final stats:")
    print(thresholds)
    print(pck_values)
    
    methods = pck_values[0].keys()
    for method in methods:
        pck_numeric = np.array([d[method] for d in pck_values])
        auc = (1 / (stop_thres - start_thres)) * np.sum(pck_numeric) * step_thres
        print(f"AUC ({method}) = {auc}")

    draw_curve(pck_values, thresholds)

    return

def main():
    ## Keypoints
    gt_file          = "projected_2d/00_00_single/all_body2DScenes.json"
    predictions_file_list = {
        "MoveNet": "out/COCOformat.json"
        #"OpenPose": "results/COCOformatMovenet.json",
    }

    # Image/Video
    input = "/media/ioannis-2004/ToshibaEXT/2DCMUPanopticPaper/ultimatum/160422_ultimatum1/hdVideos/hd_00_00_15s.mp4"
    output = "/home/ioannis-2004/Desktop/MeasurementsDTs/out/gt05_08.jpg"
    
    singleFrameFromVideo = -1
    frame_number_offset = -174   # IF VGA frame_number_offset = 105 else 0

    AUC(gt_file, predictions_file_list, input, output, singleFrameFromVideo, frame_number_offset)

if __name__ == "__main__":
    main()