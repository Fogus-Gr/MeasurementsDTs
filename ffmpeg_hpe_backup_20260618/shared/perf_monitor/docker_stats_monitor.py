#!/usr/bin/env python3

import csv
import json
import os
import signal
import socket
import sys
import time
from http.client import HTTPConnection
from urllib.parse import quote


running = True


class DockerApiError(Exception):
    def __init__(self, status, reason, body):
        super().__init__("Docker API error {} {}: {}".format(status, reason, body))
        self.status = status
        self.reason = reason
        self.body = body


class UnixHTTPConnection(HTTPConnection):
    def __init__(self, unix_socket_path, timeout=5):
        HTTPConnection.__init__(self, "localhost", timeout=timeout)
        self.unix_socket_path = unix_socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.unix_socket_path)


def log(message, level="INFO"):
    print("[{}] {}".format(level, message), flush=True)


def stop_handler(signum, frame):
    global running
    running = False


def docker_get(socket_path, path):
    conn = UnixHTTPConnection(socket_path)
    try:
        conn.request("GET", path, headers={"Host": "docker"})
        response = conn.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        if response.status >= 400:
            raise DockerApiError(response.status, response.reason, body)
        if not body:
            return {}
        return json.loads(body)
    finally:
        conn.close()


def cpu_snapshot(stats):
    cpu_stats = stats.get("cpu_stats", {})
    usage = cpu_stats.get("cpu_usage", {})
    total_usage = usage.get("total_usage", 0) or 0
    system_usage = cpu_stats.get("system_cpu_usage", 0) or 0
    online_cpus = cpu_stats.get("online_cpus", 0) or 0
    if not online_cpus:
        percpu = usage.get("percpu_usage") or []
        online_cpus = len(percpu)
    if not online_cpus:
        online_cpus = os.cpu_count() or 1
    return total_usage, system_usage, online_cpus


def cpu_percent(previous_stats, current_stats):
    current_total, current_system, online_cpus = cpu_snapshot(current_stats)

    if previous_stats is None:
        previous_stats = {"cpu_stats": current_stats.get("precpu_stats", {})}

    previous_total, previous_system, _ = cpu_snapshot(previous_stats)
    cpu_delta = current_total - previous_total
    system_delta = current_system - previous_system

    if cpu_delta <= 0 or system_delta <= 0:
        return 0.0, online_cpus, current_total, current_system

    return (float(cpu_delta) / float(system_delta)) * online_cpus * 100.0, online_cpus, current_total, current_system


def memory_values(stats):
    memory_stats = stats.get("memory_stats", {})
    usage = memory_stats.get("usage", 0) or 0
    limit = memory_stats.get("limit", 0) or 0
    nested_stats = memory_stats.get("stats", {}) or {}

    inactive_file = nested_stats.get("total_inactive_file")
    if inactive_file is None:
        inactive_file = nested_stats.get("inactive_file", 0) or 0

    if usage >= inactive_file:
        working_set = usage - inactive_file
    else:
        working_set = usage

    if limit > 0:
        memory_percent = (float(working_set) / float(limit)) * 100.0
    else:
        memory_percent = 0.0

    return usage, working_set, limit, memory_percent


def write_row(writer, container_name, container_id, stats, previous_stats):
    cpu, online_cpus, cpu_total_ns, system_cpu_ns = cpu_percent(previous_stats, stats)
    memory_usage, memory_working_set, memory_limit, memory_percent = memory_values(stats)
    active_pids = stats.get("pids_stats", {}).get("current", 0) or 0

    writer.writerow({
        "timestamp": int(time.time() * 1000),
        "total_cpu_percent": "{:.2f}".format(cpu),
        "total_mem_rss_kb": int(memory_working_set / 1024),
        "active_pids": active_pids,
        "container_name": container_name,
        "container_id": container_id[:12],
        "memory_usage_kb": int(memory_usage / 1024),
        "memory_working_set_kb": int(memory_working_set / 1024),
        "memory_limit_kb": int(memory_limit / 1024),
        "memory_percent": "{:.2f}".format(memory_percent),
        "cpu_online_cpus": online_cpus,
        "cpu_total_usage_ns": cpu_total_ns,
        "system_cpu_usage_ns": system_cpu_ns,
        "metric_source": "docker_api",
    })


def main():
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    socket_path = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    output_file = os.environ.get("OUTPUT_FILE", os.path.join(output_dir, "perf_metrics.csv"))
    target_container = os.environ.get("TARGET_CONTAINER", "hpe")
    interval = float(os.environ.get("INTERVAL", "0.5"))

    if interval <= 0:
        log("INTERVAL must be positive", "ERROR")
        return 2

    if not os.path.exists(socket_path):
        log("Docker socket not found at {}".format(socket_path), "ERROR")
        return 2

    os.makedirs(output_dir, exist_ok=True)

    fieldnames = [
        "timestamp",
        "total_cpu_percent",
        "total_mem_rss_kb",
        "active_pids",
        "container_name",
        "container_id",
        "memory_usage_kb",
        "memory_working_set_kb",
        "memory_limit_kb",
        "memory_percent",
        "cpu_online_cpus",
        "cpu_total_usage_ns",
        "system_cpu_usage_ns",
        "metric_source",
    ]

    log("Starting Docker API monitor for container '{}' at {}s interval".format(target_container, interval))
    log("Output file: {}".format(output_file))

    previous_stats = None
    saw_running_container = False
    encoded_name = quote(target_container, safe="")

    with open(output_file, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        csv_file.flush()

        while running:
            try:
                inspect_data = docker_get(socket_path, "/containers/{}/json".format(encoded_name))
            except DockerApiError as exc:
                if exc.status == 404 and not saw_running_container:
                    log("Waiting for target container '{}' to exist...".format(target_container), "WARN")
                    time.sleep(interval)
                    continue
                if exc.status == 404 and saw_running_container:
                    log("Target container '{}' disappeared; stopping monitor".format(target_container), "WARN")
                    break
                log(str(exc), "ERROR")
                time.sleep(interval)
                continue
            except (OSError, ValueError) as exc:
                log("Could not query Docker API: {}".format(exc), "ERROR")
                time.sleep(interval)
                continue

            state = inspect_data.get("State", {}) or {}
            container_id = inspect_data.get("Id", "")
            if not state.get("Running", False):
                if saw_running_container:
                    log("Target container '{}' is no longer running; stopping monitor".format(target_container))
                    break
                log("Target container '{}' exists but is not running yet".format(target_container), "WARN")
                time.sleep(interval)
                continue

            saw_running_container = True

            try:
                stats = docker_get(socket_path, "/containers/{}/stats?stream=false".format(encoded_name))
            except (DockerApiError, OSError, ValueError) as exc:
                log("Could not read Docker stats: {}".format(exc), "ERROR")
                time.sleep(interval)
                continue

            write_row(writer, target_container, container_id, stats, previous_stats)
            csv_file.flush()
            previous_stats = stats
            time.sleep(interval)

    log("Docker API monitoring complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
