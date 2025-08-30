import numpy as np
import cv2

def render(frame, bodies, LINES_BODY, score_thresh, show_scores, show_bounding_box):
        thickness = 3 
        color_skeleton = (255, 180, 90)
        color_box = (0,255,255)

        for body in bodies:                
            # Draw skeleton lines
            lines = []
            for line in LINES_BODY:
                # Check if keypoints in line exist and have valid scores
                if (len(body.keypoints) > line[0] and len(body.keypoints) > line[1] and 
                    len(body.keypoints_score) > line[0] and len(body.keypoints_score) > line[1] and 
                    body.keypoints_score[line[0]] > score_thresh and 
                    body.keypoints_score[line[1]] > score_thresh):
                    
                    # Map keypoint positions to integer coordinates for drawing
                    point_coords = [list(map(int, body.keypoints[point])) for point in line]
                    lines.append(np.array(point_coords))
            
            # Draw all valid skeleton lines
            cv2.polylines(frame, lines, False, color_skeleton, 2, cv2.LINE_AA)
            
            # TODO - I think coloring works correctly only for Movenet
            for i,x_y in enumerate(body.keypoints):
                if body.keypoints_score[i] > score_thresh:
                    if i % 2 == 1:
                        color = (0,255,0) 
                    elif i == 0:
                        color = (0,255,255)
                    else:
                        color = (0,0,255)
                    cv2.circle(frame, (int(x_y[0]), int(x_y[1])), 4, color, -11)

                    if show_scores:
                        score_text = f"{body.keypoints_score[i]:.1f}"
                        cv2.putText(frame, 
                                score_text, 
                                (int(x_y[0]) + 5, int(x_y[1]) - 5),  # Offset slightly from the circle
                                cv2.FONT_HERSHEY_SIMPLEX, 
                                0.4,  # Font scale
                                color,  # Use the same color as the keypoint
                                1,  # Thickness
                                cv2.LINE_AA)

            if show_bounding_box:
                cv2.rectangle(frame, (body.xmin, body.ymin), (body.xmax, body.ymax), color_box, thickness)