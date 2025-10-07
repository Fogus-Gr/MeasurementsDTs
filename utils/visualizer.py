import numpy as np
import cv2
from utils.constants import LABELED_VISIBLE

def render(frame, bodies, LINES_BODY, score_thresh, show_scores, show_bounding_box, show_numbering=False, isGroundTruth = False, color_skeleton = (255, 180, 90)):
        thickness = 3 
        color_box = (0,255,255)

        for body in bodies:                
            # Draw skeleton lines
            lines = []
            for line in LINES_BODY:
                # Check if keypoints in line exist and have valid scores
                if (len(body.keypoints) > line[0] and len(body.keypoints) > line[1] and 
                    len(body.keypoints_score) > line[0] and len(body.keypoints_score) > line[1] and 
                    body.keypoints_score[line[0]] == LABELED_VISIBLE and 
                    body.keypoints_score[line[1]] == LABELED_VISIBLE):
                    
                    # Map keypoint positions to integer coordinates for drawing
                    point_coords = [list(map(int, body.keypoints[point])) for point in line]
                    lines.append(np.array(point_coords))
            
            # Draw all valid skeleton lines
            cv2.polylines(frame, lines, False, color_skeleton, 2, cv2.LINE_AA)
            
            for i,x_y in enumerate(body.keypoints):
                v = body.keypoints_score[i]

                if v != LABELED_VISIBLE:
                    continue

                if isGroundTruth:
                    color = (0,255,0)
                    x, y = x_y
                    cv2.circle(frame, (int(x), int(y)), 5, color, -1)
                else:
                    x, y = x_y
                    if body.correctness is not None and i < len(body.correctness):
                        if body.correctness[i]:
                            # Correct: green circle
                            color = (0, 255, 0)
                            cv2.circle(frame, (int(x), int(y)), 5, color, -1)
                        else:
                            # Incorrect: red cross
                            color = (0, 0, 255)
                            cross_size = 5
                            x_int, y_int = int(x), int(y)
                            cv2.line(frame, (x_int - cross_size, y_int - cross_size),
                                            (x_int + cross_size, y_int + cross_size),
                                            color, 2)
                            cv2.line(frame, (x_int - cross_size, y_int + cross_size),
                                            (x_int + cross_size, y_int - cross_size),
                                            color, 2)
                    else:
                        # fallback yellow circle if correctness unknown
                        color = (0, 255, 255)
                        cv2.circle(frame, (int(x), int(y)), 5, color, -1)

                if show_scores:
                    score_text = f"{v:.1f}"
                    cv2.putText(frame, 
                            score_text, 
                            (int(x_y[0]) + 5, int(x_y[1]) - 5),  # Offset slightly from the circle
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            fontScale = 0.8,
                            color = (255,255,255),
                            thickness = 2,
                            lineType =cv2.LINE_AA)
                if show_numbering:
                    score_text = f"{i}"
                    cv2.putText(frame, 
                            score_text, 
                            (int(x_y[0]) - 5, int(x_y[1]) - 10),  # Offset slightly from the circle
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            fontScale = 0.8,
                            color = (255,255,255),
                            thickness = 2,
                            lineType =cv2.LINE_AA)

            if show_bounding_box:
                cv2.rectangle(frame, (body.xmin, body.ymin), (body.xmax, body.ymax), color_box, thickness)


"""
Draw a legend box with method names and colors in the top-right corner.
    
size: one of {"small", "normal", "big"} to control legend scaling.
"""
def draw_legend(frame, method_colors, size="normal"):
    if not method_colors:
        return
    
    # 🔸 Size presets
    size_factors = {
        "small": 1.0,
        "normal": 2.0,
        "big": 3.5
    }
    if size not in size_factors:
        raise ValueError(f"Invalid size '{size}'. Use one of {list(size_factors.keys())}.")

    s = size_factors[size]

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5 * s
    font_thickness = max(1, int(1 * s))
    line_height = int(20 * s)
    padding = int(10 * s)
    swatch_size = int(12 * s)

    # Sort legend entries so ground_truth is always first
    legend_items = [('ground_truth', (0, 255, 0))] + [
        (name, color) for name, color in method_colors.items()
        if name != 'ground_truth'
    ]

    # Legend box dimensions
    max_text_width = max([cv2.getTextSize(name, font, font_scale, font_thickness)[0][0] for name, _ in legend_items])
    box_width = padding * 3 + swatch_size + max_text_width
    box_height = padding * 2 + line_height * len(legend_items)

    # Position in top-right corner
    x0 = frame.shape[1] - box_width - 10
    y0 = 10
    x1 = x0 + box_width
    y1 = y0 + box_height

    # Draw semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (50, 50, 50), -1)
    alpha = 0.6
    frame[:] = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Draw each legend entry
    for i, (name, color) in enumerate(legend_items):
        y = y0 + padding + i * line_height + swatch_size // 2

        # color swatch
        cv2.rectangle(frame, (x0 + padding, y - swatch_size // 2),
                             (x0 + padding + swatch_size, y + swatch_size // 2),
                             color, -1)

        # method name
        cv2.putText(frame, name,
                    (x0 + padding * 2 + swatch_size, y + swatch_size // 4),
                    font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)