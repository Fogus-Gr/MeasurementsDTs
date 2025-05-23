import json

coco_results = []

def create_COCO_format(bodies, score_thresh, frame_number):
    # Flags for COCO format
    CATEGORY_PERSON = 1
    NOT_LABELED = 0
    LABELED_NOT_VISIBLE = 1
    LABELED_VISIBLE = 2

    results = []

    for body in bodies:
        keypoints = []
        for (x, y), score in zip(body.keypoints, body.keypoints_score):
            v = LABELED_VISIBLE if score >=score_thresh else LABELED_NOT_VISIBLE
            keypoints.extend([float(x), float(y), v])

        results.append({
            "image_id": frame_number,
            "category_id": CATEGORY_PERSON,
            "keypoints": keypoints,
            "score": float(body.score)
        })

    return results

def append_COCO_format(bodies, score_thresh, frame_number):
    global coco_results

    coco_results.extend(create_COCO_format(bodies, score_thresh, frame_number))

# coco_results resets only when the program starts
def reset_COCO_results():
    global coco_results
    coco_results = []

def save_COCO_format_json(filepath):
    global coco_results

    print(f"Saving file {filepath}")
    with open(filepath, 'w') as f:
        json.dump(coco_results, f)