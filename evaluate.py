from utils.accuracyEvaluation.evaluator import Evaluator

def main():
    ## Keypoints
    gt_file          = "keypoint_json/ground_truth_panoptic/00_00_single/all_body2DScenes.json"
    predictions_file_list = {
        "MoveNet": "keypoint_json/movenet/00_00/COCOformat.json",
        #"OpenPose": "results/COCOformatMovenet.json",
    }

    # Image/Video
    input  = "/mnt/data/panoptic-toolbox/scripts/171204_pose1_backup/hdVideos/hd_00_00.mp4"
    output = "/home/ioannis-2004/Desktop/MeasurementsDTs/out/gt05_08.jpg"
    
    singleFrameFromVideo = -1

    ev = Evaluator(ground_truth_file = gt_file, predictions_file_list = predictions_file_list, input_src=input, output=output, singleFrameFromVideo=singleFrameFromVideo)
    ev.main_loop()

if __name__ == "__main__":
    main()