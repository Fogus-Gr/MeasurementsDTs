from utils.accuracyEvaluation.evaluator import Evaluator

def main():
    ## Keypoints
    gt_file          = "projected_2d/01_01_single/all_body2DScenes.json"
    predictions_file_list = {
        "MoveNet": "outSSA/COCOformat.json"
        #"OpenPose": "results/COCOformatMovenet.json",
    }

    # Image/Video
    input = "/media/ioannis-2004/ToshibaEXT/panoptic-toolbox/171204_pose1/vgaVideos/vga_01_01.mp4"
    output = "/home/ioannis-2004/Desktop/MeasurementsDTs/out/gt05_08.jpg"
    
    singleFrameFromVideo = -1
    frame_number_offset = 105   # IF VGA frame_number_offset = 105 else 0

    ev = Evaluator(ground_truth_file = gt_file, 
                   predictions_file_list = predictions_file_list, 
                   input_src=input, 
                   output=output, 
                   singleFrameFromVideo=singleFrameFromVideo, 
                   frame_number_offset = frame_number_offset)
    ev.main_loop()

if __name__ == "__main__":
    main()