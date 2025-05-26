import json
import csv

coco_results = []
csv_rows = []

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

def append_COCO_format_json(bodies, score_thresh, frame_number):
    global coco_results

    coco_results.extend(create_COCO_format(bodies, score_thresh, frame_number))

def append_COCO_format_csv(bodies, score_thresh, frame_number, timestamp):
    global csv_rows

    results = create_COCO_format(bodies, score_thresh, frame_number)
    json_string = json.dumps(results)
    
    csv_rows.append([frame_number, timestamp, json_string])

# coco_results resets only when the program starts
def reset_COCO_results():
    global coco_results, csv_rows
    coco_results = []
    csv_rows = []

def save_COCO_format_json(filepath):
    global coco_results

    print(f"Saving file {filepath}")
    with open(filepath, 'w') as f:
        json.dump(coco_results, f)

def save_COCO_format_csv(filepath):
    global csv_rows

    print(f"Saving file {filepath}")
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["frame_number", "timestamp", "json_output"])  # header
        writer.writerows(csv_rows)  # write all data rows