# recent-dash Experiment Rig

`recent-dash` is a DASH/HTTP adaptive bitrate caching experiment rig. It is separate from the HPE/RTSP rigs: no HPE model runs here, no pose-estimation output is produced, and the main subject under measurement is the HTTP proxy/cache path between the DASH server and DASH client.

## Prerequisites

Install these on the host before running the rig:

- Docker with Compose v2
- `bc`, used by `run_experiment.sh` for startup/timestamp timing
- Linux host support for privileged packet capture when using `trace_container`

The tracer image already includes `tcpdump`, `gawk`, `iproute2`, `procps`, and `net-tools`.

## Services

`docker-compose.yml` starts five services:

| Service | Purpose |
|---|---|
| `http_server` | Origin HTTP server for DASH content. |
| `http_proxy` | DASH caching/ABR proxy under measurement. |
| `http_client` | HTTP client endpoint that exposes the DASH manifest URL for VLC/player access. |
| `perf_monitor` | Reads proxy PIDs from `./pids/dash.pid` and writes 500 ms `/proc` delta CPU/RSS samples to `results/perf_metrics.csv` inside the container. |
| `trace_container` | Captures DASH-only TCP payload bytes and writes `/opt/tracer/output/trace.csv`. |

## Build

```bash
cd recent-dash
docker compose build
```

## Run

```bash
cd recent-dash
./run_experiment.sh
```

The default run duration is 500 seconds. Override it with:

```bash
EXPERIMENT_DURATION_SECONDS=120 ./run_experiment.sh
```

Readiness checks wait up to 60 seconds by default and poll every 2 seconds. Override them with:

```bash
READINESS_TIMEOUT_SECONDS=90 READINESS_POLL_SECONDS=3 ./run_experiment.sh
```

Optional first argument changes the result-directory label:

```bash
./run_experiment.sh dash
```

## How `run_experiment.sh` Works

The runner performs one complete experiment lifecycle:

1. Checks host prerequisites, currently `bc`.
2. Creates a timestamped result directory named like `results_dash_<cpu_model>_<timestamp>`.
3. Cleans previous transient CSV files from local output folders.
4. Runs `docker compose down --remove-orphans` to clear old containers.
5. Starts `http_server`, `http_proxy`, and `http_client`.
6. Detects the host PIDs for the proxy container and writes them to `./pids/dash.pid` for `perf_monitor`.
7. Resolves the published `http_client` port and waits for `http://localhost:<mapped_port>/manifest.mpd` to respond.
8. Resolves Docker-network IPs for `http_server`, `http_proxy`, and `http_client`.
9. Exports those IPs as `DASH_SERVER_IP`, `DASH_PROXY_IP`, and `DASH_CLIENT_IP` before starting the tracer.
10. Builds and starts `perf_monitor`.
11. Starts `trace_container` with the exported DASH endpoint IPs.
12. Prints the player URL: `http://localhost:<mapped_port>/manifest.mpd`.
13. Sleeps for `EXPERIMENT_DURATION_SECONDS`.
14. Copies performance CSV, trace CSV, and logs into the timestamped result directory.
15. Stops the compose stack and writes a short `results.txt` summary.

## DASH-Only Network Tracing

The rig traces DASH video bytes only by filtering TCP payloads on the DASH HTTP response paths. It does not count all interface traffic.

Trace directions:

| Direction | Meaning | CSV column |
|---|---|---|
| origin server `:80` -> proxy | bytes received by proxy from the origin DASH server | `proxy_rx_video_bytes` |
| proxy `:80` -> client | bytes sent by proxy to the DASH client/player | `proxy_tx_video_bytes` |

This avoids DNS noise, host background traffic, and unrelated packets on the interface. The tracer uses `tcpdump`, which is already installed in `recent-dash/bpftrace-tracer/Dockerfile`, then buckets TCP payload bytes with `gawk`.

`trace_container_net.sh` writes:

```text
timestamp_ms,proxy_rx_video_bytes,proxy_tx_video_bytes
```

Output path copied by the runner:

```text
<result_dir>/traces/trace.csv
```

### Trace Configuration

Defaults:

```bash
DASH_TRACE_INTERFACE=any
TRACE_INTERVAL_MS=10
```

`any` is the default capture interface because DASH traffic flows over Docker bridge interfaces while the tracer runs with host networking. Override only when you know the exact interface:

```bash
DASH_TRACE_INTERFACE=docker0 TRACE_INTERVAL_MS=50 ./run_experiment.sh
```

The filter is based on container IP and port direction:

```text
server_ip:80 -> proxy_ip
proxy_ip:80 -> client_ip
```

This is HTTP response payload filtering. If the same services later carry non-video HTTP responses on port 80, those response bytes will also match. Strict URL/path filtering such as `/video_...` would require HTTP-aware parsing instead of packet-header filtering.

## Readiness Checks

`run_experiment.sh` no longer relies on a fixed startup sleep. After starting `http_server`, `http_proxy`, and `http_client`, it waits for all three containers to exist and then checks the client manifest URL:

```text
http://localhost:<EXPOSED_HTTP_CLIENT_PORT>/manifest.mpd
```

Readiness knobs:

| Variable | Default | Meaning |
|---|---:|---|
| `READINESS_TIMEOUT_SECONDS` | `60` | Maximum wait for containers and manifest readiness. |
| `READINESS_POLL_SECONDS` | `2` | Delay between readiness attempts. |

The readiness helper uses `curl` when available, then `wget`, then a Bash `/dev/tcp` HTTP probe. This avoids adding a new host prerequisite.

## Resource Limits

`docker-compose.yml` applies conservative local Compose resource limits. Each limit can be overridden from the environment before running the experiment.

| Service | CPU env var | Default | Memory env var | Default |
|---|---|---:|---|---:|
| `http_server` | `HTTP_SERVER_CPU_LIMIT` | `0.5` | `HTTP_SERVER_MEMORY_LIMIT` | `512M` |
| `http_proxy` | `HTTP_PROXY_CPU_LIMIT` | `1.0` | `HTTP_PROXY_MEMORY_LIMIT` | `1G` |
| `http_client` | `HTTP_CLIENT_CPU_LIMIT` | `0.5` | `HTTP_CLIENT_MEMORY_LIMIT` | `512M` |
| `perf_monitor` | `PERF_MONITOR_CPU_LIMIT` | `0.25` | `PERF_MONITOR_MEMORY_LIMIT` | `256M` |
| `trace_container` | `TRACE_CONTAINER_CPU_LIMIT` | `0.5` | `TRACE_CONTAINER_MEMORY_LIMIT` | `256M` |

Example override:

```bash
HTTP_PROXY_CPU_LIMIT=2.0 HTTP_PROXY_MEMORY_LIMIT=2G ./run_experiment.sh
```

The proxy gets the largest default budget because it is the measured cache/ABR component. The tracer gets more CPU than `perf_monitor` because `tcpdump` plus `gawk` can burst during high-throughput periods.

`perf_monitor` also accepts:

| Variable | Default | Meaning |
|---|---:|---|
| `PERF_MONITOR_INTERVAL_SECONDS` | `0.5` | Sampling interval for `/proc` CPU deltas. |

The underlying monitor image is shared with `ffmpeg_hpe`; each rig passes its own `PID_FILE` so the shared script reads the correct process list.

## Result Files

Each run creates a timestamped directory with this shape:

```text
results_<label>_<cpu_model>_<timestamp>/
  container_timing.txt
  logs/
    http_server.log
    http_proxy.log
    http_client.log
    perf_monitor.log
    trace_container.log
  perf/
    perf_metrics.csv
  traces/
    trace.csv
  results.txt
```

Important files:

| File | Use |
|---|---|
| `perf/perf_metrics.csv` | Proxy CPU/RSS samples from `perf_monitor`, sampled from `/proc` at 500 ms by default. |
| `traces/trace.csv` | DASH-only proxy RX/TX TCP payload bytes. |
| `logs/*.log` | Container logs captured before teardown. |
| `container_timing.txt` | Container startup timing summary. |
| `results.txt` | Run metadata summary. |

## Manual Playback

During a run, open the printed URL in VLC or another DASH-capable player:

```text
http://localhost:<EXPOSED_HTTP_CLIENT_PORT>/manifest.mpd
```

Remote host form:

```text
http://<SERVER_IP>:<EXPOSED_HTTP_CLIENT_PORT>/manifest.mpd
```

## Notes and Limits

- This rig measures DASH/HTTP proxy behavior, not HPE inference.
- `trace_container` is intentionally privileged and host-networked so it can see Docker bridge traffic.
- Compose `depends_on` only guarantees container start order; `run_experiment.sh` adds a manifest readiness probe before starting monitors.
