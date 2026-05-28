#!/usr/bin/env python3
"""
BCC-based TX (outgoing) byte counter for HPE container.

Attaches to the sys_enter_sendto tracepoint and counts bytes sent by the HPE
process (filtered by PID). Polls at configurable interval (default 10ms) and
writes timestamped deltas to CSV.

This complements bcc_rx_bytes.py (which measures incoming video stream bytes).
"""

from bcc import BPF
import time
import sys
import ctypes
import os

def log(message, level="INFO"):
    print(f"[{level}] {message}", file=sys.stderr)

def wait_for_pid(pid_file, timeout=30):
    """Wait for PID file to be created by run_experiment.sh."""
    log(f"Waiting for PID file: {pid_file}")
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(pid_file):
            try:
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                    if pid > 0:
                        log(f"Found HPE PID: {pid}")
                        return pid
            except (ValueError, IOError) as e:
                log(f"Error reading PID file: {e}", "WARNING")
        time.sleep(0.5)
    raise SystemExit(f"Timeout waiting for PID file: {pid_file}")

def main(poll_interval_s=0.01):
    PID_FILE = os.getenv("PID_FILE", "/pids/hpe.pid")
    OUTPUT_CSV = "/opt/tracer/output/hpe_video_tx.csv"

    # Wait for HPE container to start and PID file to be written
    hpe_pid = wait_for_pid(PID_FILE)

    bpf_text = """
#include <uapi/linux/ptrace.h>

BPF_HASH(tx_bytes, u32, u64);

// Tracepoint for sys_enter_sendto — fires when HPE calls sendto()
TRACEPOINT_PROBE(syscalls, sys_enter_sendto) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    
    // Filter: only count bytes from the HPE process
    if (pid != %d)
        return 0;

    u64 size = (u64)args->size;
    u32 key = 0;
    u64 *val = tx_bytes.lookup_or_init(&key, &size);
    if (val) {
        __sync_fetch_and_add(val, size);
    }
    return 0;
}
""" % hpe_pid

    try:
        b = BPF(text=bpf_text)
        log("BPF program loaded and attached to sys_enter_sendto")
    except Exception as e:
        log(f"BPF initialization failed: {str(e)}", "ERROR")
        sys.exit(1)

    # Prepare output directory and CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    with open(OUTPUT_CSV, "w") as f:
        f.write("timestamp_ms,tx_bytes_delta,tx_bytes_current,tx_bytes_prev,dt_ms\n")
        key = ctypes.c_uint(0)
        prev_bytes = 0
        prev_time = int(time.time() * 1000)
        
        log(f"Starting TX monitoring (poll interval: {poll_interval_s * 1000:.0f}ms)")
        
        while True:
            try:
                now_ms = int(time.time() * 1000)
                val = b["tx_bytes"][key] if key in b["tx_bytes"] else 0
                bytes_total = val.value if hasattr(val, 'value') else val
                delta = bytes_total - prev_bytes
                dt = now_ms - prev_time
                
                f.write(f"{now_ms},{delta},{bytes_total},{prev_bytes},{dt}\n")
                f.flush()
                
                prev_bytes = bytes_total
                prev_time = now_ms
                
                # Clear the map to avoid unbounded growth
                try:
                    b["tx_bytes"].clear()
                except Exception:
                    pass
                
                time.sleep(poll_interval_s)
                
            except KeyboardInterrupt:
                log("Received interrupt, shutting down")
                break
            except Exception as e:
                log(f"Monitoring error: {str(e)}", "ERROR")
                time.sleep(1)

if __name__ == "__main__":
    # Get polling interval from environment variable, default to 0.01s (10ms)
    poll_interval_s = float(os.getenv("BCC_POLL_INTERVAL_S", "0.01"))
    log(f"TX tracer starting with {poll_interval_s * 1000:.0f}ms poll interval")
    main(poll_interval_s)
