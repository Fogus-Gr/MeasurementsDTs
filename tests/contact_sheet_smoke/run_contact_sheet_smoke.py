import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METHODS = ["movenet", "openpose", "hrnet", "ae1", "ae2", "ae3", "alphapose"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run HPE image smoke tests and create a visual contact sheet."
    )
    parser.add_argument(
        "--input",
        default="unit_tests/images/testImage.jpg",
        help="Input image to run through each model.",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=DEFAULT_METHODS,
        choices=DEFAULT_METHODS,
        help="Models to run. Defaults to all supported HPE methods.",
    )
    parser.add_argument(
        "--device",
        default="CPU",
        choices=["CPU", "GPU"],
        help="Inference device passed to main.py.",
    )
    parser.add_argument(
        "--output-root",
        default="out",
        help="Directory where the timestamped smoke session is created.",
    )
    parser.add_argument(
        "--session-name",
        help="Optional session directory name. Defaults to contact_sheet_smoke_<timestamp>.",
    )
    parser.add_argument(
        "--timeout-per-model",
        type=int,
        default=180,
        help="Seconds before a single model command is stopped.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Create the sheet and exit 0 even if one or more models fail.",
    )
    return parser.parse_args()


def run_model(method, input_path, device, session_dir, timeout_per_model):
    method_dir = session_dir / method
    method_dir.mkdir(parents=True, exist_ok=True)
    log_path = method_dir / "run.log"
    status_path = method_dir / "status.txt"

    cmd = [
        sys.executable,
        "main.py",
        "--method",
        method,
        "--input",
        str(input_path),
        "--device",
        device,
        "--save_image",
        "--output_dir",
        str(method_dir),
    ]

    with log_path.open("w", encoding="utf-8") as log_file:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout_per_model,
            )
            status = "OK" if result.returncode == 0 else "FAIL exit={}".format(result.returncode)
        except subprocess.TimeoutExpired:
            status = "FAIL timeout={}s".format(timeout_per_model)

    status_path.write_text(status + "\n", encoding="utf-8")
    return {
        "method": method,
        "status": status,
        "output_dir": str(method_dir),
        "log": str(log_path),
        "image": str(method_dir / "frame_0000.jpg"),
    }


def draw_text_block(image, x, y, lines, color):
    for index, line in enumerate(lines):
        cv2.putText(
            image,
            line,
            (x, y + index * 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            color,
            2,
            cv2.LINE_AA,
        )


def create_contact_sheet(results, session_dir):
    cell_w, cell_h = 360, 260
    label_h = 38
    cols = 3
    rows = (len(results) + cols - 1) // cols
    sheet = np.full((rows * (cell_h + label_h), cols * cell_w, 3), 245, dtype=np.uint8)

    for index, result in enumerate(results):
        row, col = divmod(index, cols)
        x0 = col * cell_w
        y0 = row * (cell_h + label_h)
        img_y = y0 + label_h
        method = result["method"]
        status = result["status"]

        cv2.rectangle(sheet, (x0, y0), (x0 + cell_w - 1, y0 + label_h - 1), (35, 35, 35), -1)
        status_color = (80, 220, 80) if status == "OK" else (80, 80, 240)
        cv2.putText(
            sheet,
            "{}: {}".format(method, status),
            (x0 + 10, y0 + 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            status_color,
            2,
            cv2.LINE_AA,
        )

        image_path = Path(result["image"])
        if image_path.exists():
            image = cv2.imread(str(image_path))
            if image is not None:
                h, w = image.shape[:2]
                scale = min(cell_w / float(w), cell_h / float(h))
                resized_w, resized_h = int(w * scale), int(h * scale)
                resized = cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
                px = x0 + (cell_w - resized_w) // 2
                py = img_y + (cell_h - resized_h) // 2
                sheet[py:py + resized_h, px:px + resized_w] = resized
                continue

        cv2.rectangle(sheet, (x0 + 12, img_y + 12), (x0 + cell_w - 13, img_y + cell_h - 13), (230, 230, 255), -1)
        cv2.rectangle(sheet, (x0 + 12, img_y + 12), (x0 + cell_w - 13, img_y + cell_h - 13), (0, 0, 180), 2)
        draw_text_block(sheet, x0 + 28, img_y + 82, ["No output image", "See run.log"], (0, 0, 180))

    output_path = session_dir / "contact_sheet.jpg"
    cv2.imwrite(str(output_path), sheet)
    return output_path


def main():
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = REPO_ROOT / input_path
    if not input_path.exists():
        raise SystemExit("Input image not found: {}".format(input_path))

    session_name = args.session_name or "contact_sheet_smoke_{}".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = REPO_ROOT / output_root
    session_dir = output_root / session_name
    session_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for method in args.methods:
        print("Running {}...".format(method), flush=True)
        result = run_model(method, input_path, args.device, session_dir, args.timeout_per_model)
        print("  {}".format(result["status"]), flush=True)
        results.append(result)

    contact_sheet = create_contact_sheet(results, session_dir)
    summary_path = session_dir / "summary.json"
    summary = {
        "input": str(input_path),
        "device": args.device,
        "contact_sheet": str(contact_sheet),
        "results": results,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("Contact sheet: {}".format(contact_sheet))
    print("Summary: {}".format(summary_path))

    failed = [result for result in results if result["status"] != "OK"]
    if failed and not args.allow_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
