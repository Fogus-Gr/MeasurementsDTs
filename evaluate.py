from utils.accuracyEvaluation.keypointsDataset import KeypointsDataset
from utils.accuracyEvaluation.evaluator import Evaluator

def main():
    ## Keypoints
    gt_file          = "keypoint_json/ground_truth_panoptic/00_00_single/all_body2DScenes.json"
    predictions_file = {
        "MoveNet": "keypoint_json/movenet/00_00/COCOformat.json",
        #"OpenPose": "results/COCOformatMovenet.json",
    }

    ground_truth = KeypointsDataset(gt_file, "ground_truth")

    predictions = []
    for method, path in predictions_file.items():
        predictions.append(KeypointsDataset(path, method))

    # Image/Video
    input  = "/mnt/data/panoptic-toolbox/scripts/171204_pose1_backup/hdVideos/hd_00_00.mp4"
    output = "/home/ioannis-2004/Desktop/MeasurementsDTs/out/gt05_08.jpg"
    
    singleFrameFromVideo = -1

    ev = Evaluator(ground_truth=ground_truth, predictions=predictions, input_src=input, output=output, singleFrameFromVideo=singleFrameFromVideo)
    ev.main_loop()

if __name__ == "__main__":
    main()