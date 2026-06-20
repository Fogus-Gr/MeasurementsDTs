#!/usr/bin/env python3

import argparse
import csv
import json
import os
import re
import statistics
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Validate an ffmpeg_hpe results directory.")
    parser.add_argument("results_dir", nargs="?", help="Results directory to validate. Defaults to latest results_* directory.")
    parser.add_argument("--rx-tolerance-percent", type=float, default=2.0, help="Allowed BCC RX vs FFmpeg bytes-read delta.")
    parser.add_argument("--min-avg-cpu-percent", type=float, default=1.0, help="Minimum plausible average HPE container CPU percent.")
    parser.add_argument("--min-memory-mb", type=float, default=50.0, help="Minimum plausible HPE container memory working set.")
    return parser.parse_args()


def latest_results_dir(base_dir):
    candidates = [p for p in base_dir.glob("results_*") if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def read_text(path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def read_csv(path):
    with path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def numeric(value):
    if value is None:
        raise ValueError("missing value")
    text = str(value).strip()
    if text == "":
        raise ValueError("empty value")
    return float(text)


def integer(value):
    number = numeric(value)
    if int(number) != number:
        raise ValueError("not an integer")
    return int(number)


def add_check(checks, name, passed, details, metrics=None):
    checks.append({
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
        "metrics": metrics or {},
    })


def find_one(patterns):
    matches = []
    for pattern in patterns:
        matches.extend(pattern.parent.glob(pattern.name))
    return sorted(matches)


def validate_hpe_exit(results_dir, checks, metrics):
    exit_log = results_dir / "logs" / "hpe_exit.log"
    text = read_text(exit_log)
    match = re.search(r"exit code:\s*([0-9]+|unknown)", text, re.IGNORECASE)
    if not match:
        add_check(checks, "hpe_exit_code", False, "Missing or malformed logs/hpe_exit.log")
        return

    exit_code = match.group(1)
    metrics["hpe_exit_code"] = exit_code
    add_check(
        checks,
        "hpe_exit_code",
        exit_code == "0",
        "HPE container exit code is {}".format(exit_code),
        {"exit_code": exit_code},
    )


def parse_hpe_log(results_dir, checks, metrics):
    hpe_log = results_dir / "logs" / "hpe.log"
    text = read_text(hpe_log)
    if not text:
        add_check(checks, "hpe_log", False, "Missing or empty logs/hpe.log")
        return None, None

    frame_matches = re.findall(r"Processing completed\. Total frames processed:\s*([0-9]+)", text)
    ffmpeg_matches = re.findall(r"Statistics:\s*([0-9]+)\s+bytes read", text)

    processed_frames = int(frame_matches[-1]) if frame_matches else None
    ffmpeg_bytes = int(ffmpeg_matches[-1]) if ffmpeg_matches else None

    metrics["processed_frames_from_log"] = processed_frames
    metrics["ffmpeg_bytes_read"] = ffmpeg_bytes

    add_check(
        checks,
        "processed_frame_log",
        processed_frames is not None,
        "Processed frame count {}".format(processed_frames) if processed_frames is not None else "Could not find processed frame count in hpe.log",
        {"processed_frames": processed_frames},
    )
    add_check(
        checks,
        "ffmpeg_bytes_read_log",
        ffmpeg_bytes is not None and ffmpeg_bytes > 0,
        "FFmpeg bytes read {}".format(ffmpeg_bytes) if ffmpeg_bytes is not None else "Could not find FFmpeg bytes-read line in hpe.log",
        {"ffmpeg_bytes_read": ffmpeg_bytes},
    )

    return processed_frames, ffmpeg_bytes


def validate_json_output(results_dir, processed_frames, checks, metrics):
    json_files = find_one([results_dir / "hpe_output" / "*_JSON.csv"])
    if len(json_files) != 1:
        add_check(checks, "hpe_json_csv_presence", False, "Expected exactly one *_JSON.csv, found {}".format(len(json_files)))
        return

    path = json_files[0]
    try:
        rows = read_csv(path)
    except (OSError, csv.Error) as exc:
        add_check(checks, "hpe_json_csv_parse", False, "Could not parse {}: {}".format(path.name, exc))
        return

    metrics["json_csv"] = str(path)
    metrics["json_frame_rows"] = len(rows)

    add_check(checks, "hpe_json_csv_nonempty", len(rows) > 0, "{} has {} data rows".format(path.name, len(rows)), {"rows": len(rows)})

    frame_numbers = []
    malformed = None
    for index, row in enumerate(rows):
        try:
            frame_number = integer(row.get("frame_number"))
            json.loads(row.get("json_output", ""))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            malformed = "row {}: {}".format(index + 2, exc)
            break
        frame_numbers.append(frame_number)

    add_check(
        checks,
        "hpe_json_csv_malformed",
        malformed is None,
        "All JSON CSV rows are parseable" if malformed is None else malformed,
    )

    expected = list(range(len(frame_numbers)))
    sequential = frame_numbers == expected
    add_check(
        checks,
        "hpe_json_frame_sequence",
        sequential,
        "Frame numbers are sequential 0..{}".format(len(frame_numbers) - 1) if sequential else "Frame numbers are not sequential from 0",
        {"first_frame": frame_numbers[0] if frame_numbers else None, "last_frame": frame_numbers[-1] if frame_numbers else None},
    )

    if processed_frames is not None:
        add_check(
            checks,
            "hpe_json_frame_count",
            len(rows) == processed_frames,
            "JSON rows {} vs processed frames {}".format(len(rows), processed_frames),
            {"json_rows": len(rows), "processed_frames": processed_frames},
        )


def validate_tx_output(results_dir, checks, metrics):
    tx_files = find_one([results_dir / "hpe_output" / "*_Tx.csv"])
    if len(tx_files) != 1:
        add_check(checks, "hpe_tx_csv_presence", False, "Expected exactly one *_Tx.csv, found {}".format(len(tx_files)))
        return

    path = tx_files[0]
    try:
        rows = read_csv(path)
    except (OSError, csv.Error) as exc:
        add_check(checks, "hpe_tx_csv_parse", False, "Could not parse {}: {}".format(path.name, exc))
        return

    malformed = None
    total_json_bytes = 0
    for index, row in enumerate(rows):
        try:
            numeric(row.get("msecond"))
            json_bytes = integer(row.get("json_bytes"))
            if json_bytes < 0:
                raise ValueError("negative json_bytes")
            total_json_bytes += json_bytes
        except ValueError as exc:
            malformed = "row {}: {}".format(index + 2, exc)
            break

    metrics["tx_csv"] = str(path)
    metrics["hpe_output_payload_bytes"] = total_json_bytes
    add_check(
        checks,
        "hpe_tx_csv_parse",
        rows and malformed is None,
        "HPE output payload CSV is parseable; this is JSON payload bytes, not network TX" if rows and malformed is None else (malformed or "Tx CSV is empty"),
        {"rows": len(rows), "json_payload_bytes": total_json_bytes},
    )


def validate_bcc_rx(results_dir, ffmpeg_bytes, tolerance_percent, checks, metrics):
    trace_files = find_one([
        results_dir / "traces" / "bcc" / "video_rx.csv",
        results_dir / "traces" / "bcc" / "hpe_video_rx.csv",
    ])
    if not trace_files:
        add_check(checks, "bcc_rx_csv_presence", False, "Missing traces/bcc/video_rx.csv")
        return

    path = trace_files[0]
    try:
        rows = read_csv(path)
    except (OSError, csv.Error) as exc:
        add_check(checks, "bcc_rx_csv_parse", False, "Could not parse {}: {}".format(path.name, exc))
        return

    if not rows:
        add_check(checks, "bcc_rx_csv_nonempty", False, "{} is empty".format(path.name))
        return

    final_bytes = None
    try:
        if "rx_video_bytes_current" in rows[-1]:
            final_bytes = integer(rows[-1].get("rx_video_bytes_current"))
        elif "rx_video_bytes_delta" in rows[-1]:
            final_bytes = sum(integer(row.get("rx_video_bytes_delta")) for row in rows)
    except ValueError as exc:
        add_check(checks, "bcc_rx_csv_parse", False, "Malformed RX byte value: {}".format(exc))
        return

    metrics["bcc_rx_bytes"] = final_bytes
    add_check(
        checks,
        "bcc_rx_csv_nonempty",
        final_bytes is not None and final_bytes > 0,
        "BCC final RX bytes {}".format(final_bytes),
        {"bcc_rx_bytes": final_bytes, "rows": len(rows)},
    )

    if ffmpeg_bytes is not None and ffmpeg_bytes > 0 and final_bytes is not None:
        diff = abs(final_bytes - ffmpeg_bytes)
        diff_percent = (float(diff) / float(ffmpeg_bytes)) * 100.0
        metrics["bcc_vs_ffmpeg_diff_percent"] = diff_percent
        add_check(
            checks,
            "bcc_rx_matches_ffmpeg_bytes",
            diff_percent <= tolerance_percent,
            "BCC RX {} vs FFmpeg {} bytes; diff {:.3f}%".format(final_bytes, ffmpeg_bytes, diff_percent),
            {"bcc_rx_bytes": final_bytes, "ffmpeg_bytes_read": ffmpeg_bytes, "diff_percent": diff_percent},
        )

    port_info = results_dir / "traces" / "bcc" / "port_info.txt"
    port_text = read_text(port_info)
    port_match = re.search(r"(?:Monitoring HPE traffic on port\s+|BCC detected HPE video port:\s*)([0-9]+)", port_text)
    add_check(
        checks,
        "bcc_port_detection",
        port_match is not None,
        "Detected HPE video port {}".format(port_match.group(1)) if port_match else "Missing BCC port detection line",
        {"port": int(port_match.group(1)) if port_match else None},
    )


def validate_perf(results_dir, min_avg_cpu_percent, min_memory_mb, checks, metrics):
    path = results_dir / "perf" / "perf_metrics.csv"
    if not path.exists():
        add_check(checks, "perf_metrics_presence", False, "Missing perf/perf_metrics.csv")
        return

    try:
        rows = read_csv(path)
    except (OSError, csv.Error) as exc:
        add_check(checks, "perf_metrics_parse", False, "Could not parse perf_metrics.csv: {}".format(exc))
        return

    if not rows:
        add_check(checks, "perf_metrics_nonempty", False, "perf_metrics.csv has no data rows")
        return

    cpu_values = []
    memory_values = []
    active_pids = []
    malformed = None
    for index, row in enumerate(rows):
        try:
            cpu = numeric(row.get("total_cpu_percent"))
            memory = numeric(row.get("total_mem_rss_kb"))
            pids = numeric(row.get("active_pids"))
        except ValueError as exc:
            malformed = "row {}: {}".format(index + 2, exc)
            break
        cpu_values.append(cpu)
        memory_values.append(memory)
        active_pids.append(pids)

    add_check(
        checks,
        "perf_metrics_parse",
        malformed is None,
        "CPU/memory metrics are parseable" if malformed is None else malformed,
        {"rows": len(rows)},
    )
    if malformed is not None:
        return

    avg_cpu = statistics.mean(cpu_values)
    max_cpu = max(cpu_values)
    avg_memory_mb = statistics.mean(memory_values) / 1024.0
    max_memory_mb = max(memory_values) / 1024.0
    max_active_pids = max(active_pids)
    online_cpus = []
    for row in rows:
        value = row.get("cpu_online_cpus")
        if value not in (None, ""):
            try:
                online_cpus.append(numeric(value))
            except ValueError:
                pass
    plausible_cpu_limit = (max(online_cpus) if online_cpus else (os.cpu_count() or 1)) * 125.0

    metrics["perf_metric_source"] = rows[-1].get("metric_source", "pid_or_legacy")
    metrics["avg_cpu_percent"] = avg_cpu
    metrics["max_cpu_percent"] = max_cpu
    metrics["avg_memory_mb"] = avg_memory_mb
    metrics["max_memory_mb"] = max_memory_mb

    add_check(
        checks,
        "perf_cpu_positive",
        avg_cpu >= min_avg_cpu_percent and max_cpu > 0.0,
        "Average CPU {:.2f}%, max CPU {:.2f}%".format(avg_cpu, max_cpu),
        {"avg_cpu_percent": avg_cpu, "max_cpu_percent": max_cpu, "min_avg_cpu_percent": min_avg_cpu_percent},
    )
    add_check(
        checks,
        "perf_cpu_plausible",
        max_cpu <= plausible_cpu_limit,
        "Max CPU {:.2f}% with plausible limit {:.2f}%".format(max_cpu, plausible_cpu_limit),
        {"max_cpu_percent": max_cpu, "plausible_limit_percent": plausible_cpu_limit},
    )
    add_check(
        checks,
        "perf_memory_positive",
        avg_memory_mb >= min_memory_mb and max_memory_mb >= min_memory_mb,
        "Average memory {:.1f} MB, max memory {:.1f} MB".format(avg_memory_mb, max_memory_mb),
        {"avg_memory_mb": avg_memory_mb, "max_memory_mb": max_memory_mb, "min_memory_mb": min_memory_mb},
    )
    add_check(
        checks,
        "perf_active_pids_positive",
        max_active_pids > 0,
        "Max active PIDs {}".format(max_active_pids),
        {"max_active_pids": max_active_pids},
    )

    if "memory_working_set_kb" in rows[-1] and "memory_usage_kb" in rows[-1]:
        try:
            mismatches = 0
            impossible = 0
            for row in rows:
                compat_memory = numeric(row.get("total_mem_rss_kb"))
                working_set = numeric(row.get("memory_working_set_kb"))
                raw_usage = numeric(row.get("memory_usage_kb"))
                if abs(compat_memory - working_set) > 1:
                    mismatches += 1
                if working_set > raw_usage:
                    impossible += 1
            add_check(
                checks,
                "perf_docker_memory_consistency",
                mismatches == 0 and impossible == 0,
                "Docker memory working set is internally consistent",
                {"working_set_mismatches": mismatches, "working_set_gt_usage_rows": impossible},
            )
        except ValueError as exc:
            add_check(checks, "perf_docker_memory_consistency", False, "Malformed Docker memory columns: {}".format(exc))


def validate_gpu(results_dir, checks, metrics):
    path = results_dir / "gpu" / "gpu_metrics.csv"
    if not path.exists():
        add_check(checks, "gpu_metrics_presence", False, "Missing gpu/gpu_metrics.csv")
        return

    try:
        rows = read_csv(path)
    except (OSError, csv.Error) as exc:
        add_check(checks, "gpu_metrics_parse", False, "Could not parse gpu_metrics.csv: {}".format(exc))
        return

    required = ["timestamp", "gpu_id", "gpu_utilization", "mem_utilization", "temperature", "power_usage"]
    malformed = None
    max_gpu_util = 0.0
    for index, row in enumerate(rows):
        for column in required:
            if column not in row:
                malformed = "missing column {}".format(column)
                break
        if malformed:
            break
        try:
            numeric(row.get("timestamp"))
            numeric(row.get("gpu_id"))
            gpu_util = numeric(row.get("gpu_utilization"))
            numeric(row.get("mem_utilization"))
            numeric(row.get("temperature"))
            numeric(row.get("power_usage"))
        except ValueError as exc:
            malformed = "row {}: {}".format(index + 2, exc)
            break
        max_gpu_util = max(max_gpu_util, gpu_util)

    metrics["max_gpu_utilization"] = max_gpu_util
    add_check(
        checks,
        "gpu_metrics_parse",
        rows and malformed is None,
        "GPU CSV is parseable; zero GPU utilization is acceptable for CPU MoveNet" if rows and malformed is None else (malformed or "GPU CSV is empty"),
        {"rows": len(rows), "max_gpu_utilization": max_gpu_util},
    )


def report_text(report):
    lines = [
        "Validation: {}".format(report["status"]),
        "Results directory: {}".format(report["results_dir"]),
        "",
    ]
    for check in report["checks"]:
        lines.append("[{}] {} - {}".format(check["status"], check["name"], check["details"]))
    return "\n".join(lines) + "\n"


def write_reports(results_dir, report):
    json_path = results_dir / "validation_report.json"
    txt_path = results_dir / "validation_report.txt"

    try:
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        txt_path.write_text(report_text(report))
    except OSError as exc:
        print("[ERROR] Could not write validation reports in {}: {}".format(results_dir, exc), file=sys.stderr)
        print(report_text(report))
        return False

    return True


def main():
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    if args.results_dir:
        results_dir = Path(args.results_dir)
        if not results_dir.is_absolute():
            if results_dir.is_dir():
                results_dir = results_dir.resolve()
            else:
                results_dir = script_dir / results_dir
    else:
        results_dir = latest_results_dir(script_dir)

    if results_dir is None or not results_dir.is_dir():
        print("[ERROR] Results directory not found", file=sys.stderr)
        return 2

    checks = []
    metrics = {}
    thresholds = {
        "rx_tolerance_percent": args.rx_tolerance_percent,
        "min_avg_cpu_percent": args.min_avg_cpu_percent,
        "min_memory_mb": args.min_memory_mb,
    }

    validate_hpe_exit(results_dir, checks, metrics)
    processed_frames, ffmpeg_bytes = parse_hpe_log(results_dir, checks, metrics)
    validate_json_output(results_dir, processed_frames, checks, metrics)
    validate_tx_output(results_dir, checks, metrics)
    validate_bcc_rx(results_dir, ffmpeg_bytes, args.rx_tolerance_percent, checks, metrics)
    validate_perf(results_dir, args.min_avg_cpu_percent, args.min_memory_mb, checks, metrics)
    validate_gpu(results_dir, checks, metrics)

    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    report = {
        "status": status,
        "results_dir": str(results_dir),
        "thresholds": thresholds,
        "metrics": metrics,
        "checks": checks,
    }
    wrote_reports = write_reports(results_dir, report)

    print("Validation: {}".format(status))
    if wrote_reports:
        print("Report: {}".format(results_dir / "validation_report.txt"))
    else:
        print("Report files were not written")
        return 2
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
