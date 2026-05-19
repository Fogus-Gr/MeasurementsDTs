#!/bin/bash
# DEPRECATED — replaced by run_experiment.sh after the RTSP/MediaMTX migration.
#
# This script targeted the old `h264-streaming-server` HTTP-over-port-8089
# pipeline. That service no longer exists in docker-compose.yaml; the stack
# now uses MediaMTX (rtsp-broker:8554) + an NVENC FFmpeg streamer.
#
# `run_experiment.sh` already starts bcc-tracer alongside hpe and perf_monitor
# and is the supported entry point for all BCC-enabled experiment runs.
#
# Keeping this script as a hard-fail stub instead of deleting it preserves the
# git history while preventing accidental misleading-failure runs (e.g. CI or
# `find` invocations that would otherwise try to run a stale script and get
# cryptic "no such service: h264-streaming-server" errors).
set -e
cat >&2 <<'EOF'
[run_experiment_bcc.sh] DEPRECATED.

This script targeted the old HTTP h264-streaming-server (port 8089), which was
removed when the pipeline migrated to RTSP/MediaMTX. Use:

    ./run_experiment.sh <method>      # e.g. ./run_experiment.sh movenet

run_experiment.sh starts the bcc-tracer service together with hpe and
perf_monitor; the BCC outputs are collected into results_<...>/traces/bcc/.
EOF
exit 1
