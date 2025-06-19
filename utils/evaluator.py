import json
import csv

coco_results = []
csv_rows = []
bytes_per_mseconds_rows = []
ultimate_ms = None
json_buffer = ""
interval_msec = None

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

def append_COCO_format_csv(bodies, score_thresh, frame_number, timestamp, measurement_interval_ms):
    global csv_rows

    results = create_COCO_format(bodies, score_thresh, frame_number)
    json_string = json.dumps(results)
    csv_rows.append([frame_number, timestamp, json_string])

    append_Tx_csv_data(json_string, timestamp, measurement_interval_ms)    

# Measuring the transmitted data volume per time period
def append_Tx_csv_data(json_string, timestamp, measurement_interval_ms):
    global ultimate_ms, json_buffer, bytes_per_mseconds_rows, interval_msec

    interval_msec = measurement_interval_ms / 1000.0
    current_ms = int(float(timestamp) // interval_msec)

    if ultimate_ms is None:
        ultimate_ms = current_ms
        json_buffer = json_string
        return
    
    if current_ms == ultimate_ms:
        # Same second, accumulate
        json_buffer += json_string
    else:
        # Time has advanced
        # Store previous msecond's total bytes
        bytes_per_mseconds_rows.append([round(ultimate_ms * interval_msec, 3), len(json_buffer.encode('utf-8'))])

        # Fill missing mseconds with 0
        for missing_ms in range(ultimate_ms + 1, current_ms):
            bytes_per_mseconds_rows.append([round(missing_ms * interval_msec, 3), 0])

        # Reset buffer for new msecond
        ultimate_ms = current_ms
        json_buffer = json_string

def reset_results():
    global coco_results, csv_rows, bytes_per_mseconds_rows, ultimate_ms, json_buffer, interval_msec
    coco_results = []
    csv_rows = []
    bytes_per_mseconds_rows = []
    ultimate_ms = None
    interval_msec = None
    json_buffer = ""

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

def save_Tx_csv_data(filepath):
    global bytes_per_mseconds_rows, ultimate_ms, json_buffer, interval_msec

    # Flush last mseconds if data exists
    if ultimate_ms is not None and json_buffer:
        bytes_per_mseconds_rows.append([round(ultimate_ms * interval_msec, 3), len(json_buffer.encode('utf-8'))])


    print(f"Saving file {filepath}")
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["msecond", "json_bytes"])
        writer.writerows(bytes_per_mseconds_rows)