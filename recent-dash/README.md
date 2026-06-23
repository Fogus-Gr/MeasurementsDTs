# recent-dash Experiment Rig

`recent-dash` is a DASH/HTTP adaptive bitrate caching experiment rig. It is
separate from the HPE/RTSP rigs: no HPE model runs here, no pose-estimation
output is produced, and the measured component is the HTTP proxy/cache path
between the DASH server and the DASH player.

## Prerequisites

Install these on the host before running the rig:

- Docker with Compose v2
- `bc`, used by `run_experiment.sh` for startup/timestamp timing
- Linux host support for privileged packet capture when using `trace_container`

The tracer image includes `tcpdump`, `gawk`, `iproute2`, `procps`, and
`net-tools`.

## DASH Segments

The DASH assets are intentionally not committed. Restore the migrated assets
into:

```text
recent-dash/segments/
```

The runner and HTTP server image expect at least:

```text
recent-dash/segments/manifest.mpd
```

`recent-dash/segments/.gitkeep` is tracked only to preserve the restore
location after clone or migration. Do not commit the actual segment files.

## Services

`docker-compose.yml` starts six services:

| Service | Purpose |
|---|---|
| `http_server` | Origin HTTP server for DASH content. |
| `http_proxy` | DASH caching/ABR proxy under measurement. |
| `http_client` | Player-facing HTTP endpoint that exposes the DASH manifest. |
| `mpv` | Headless DASH player container that fetches the manifest from `http_client` and drives traffic. |
| `perf_monitor` | Reads proxy PIDs from `./pids/dash.pid` and writes CPU/RSS samples to `perf_metrics.csv`. |
| `trace_container` | Captures DASH-only TCP payload bytes and writes `trace.csv`. |

## Run

```bash
cd recent-dash
./run_experiment.sh
```

The default run duration is 500 seconds. Override it with:

```bash
EXPERIMENT_DURATION_SECONDS=120 ./run_experiment.sh
```

Readiness checks wait up to 60 seconds by default and poll every 2 seconds:

```bash
READINESS_TIMEOUT_SECONDS=90 READINESS_POLL_SECONDS=3 ./run_experiment.sh
```

Optional first argument changes the result-directory label:

```bash
./run_experiment.sh dash
```

## Runner Flow

The runner performs one complete experiment lifecycle:

1. Checks host prerequisites and verifies `segments/manifest.mpd` exists.
2. Creates a timestamped result directory.
3. Cleans previous transient CSV files from local output folders.
4. Runs `docker compose down --remove-orphans`.
5. Starts `http_server`, `http_proxy`, and `http_client`.
6. Waits for the published proxy and client manifest URLs to become ready.
7. Detects proxy host PIDs and writes `./pids/dash.pid`.
8. Resolves Docker-network IPs for server, proxy, and client.
9. Starts `perf_monitor`.
10. Starts the containerized `mpv` player unless `ENABLE_DASH_PLAYER=0`.
11. Resolves the player container IP, starts `trace_container`, and records `proxy -> http_client` traffic.
12. Prints the proxy URL and player URL.
13. Sleeps for `EXPERIMENT_DURATION_SECONDS`.
14. Copies CSVs and logs into the timestamped result directory.
15. Stops the compose stack and writes `results.txt`.

## Traffic Generation

The rig does not generate DASH traffic by itself. The player is what requests
the manifest and segment files, which is why the tracer stays empty if no player
connects.

Do not mount the full `segments/` tree into `http_client`. That makes the player
serve the DASH assets locally and bypasses the proxy. The experiment needs the
player to fetch the manifest from `http_client` and the media segments through
`http_proxy`.

Use one of these:

- Let the default containerized `mpv` service fetch the manifest and segments
  from `http_client`.
- Set `ENABLE_DASH_PLAYER=0` if you want to use a host player against
  `http://localhost:8881/manifest.mpd`.

## DASH-Only Network Tracing

The rig traces DASH video bytes by filtering TCP payloads on the DASH HTTP
response paths. It does not count all interface traffic.

| Direction | Meaning | CSV column |
|---|---|---|
| origin server `:80` -> proxy | bytes received by proxy from origin | `proxy_rx_video_bytes` |
| proxy `:80` -> player | bytes sent by proxy to the DASH player | `proxy_tx_video_bytes` |

The tracer writes:

```text
timestamp_ms,proxy_rx_video_bytes,proxy_tx_video_bytes
```

Defaults:

```bash
DASH_TRACE_INTERFACE=any
TRACE_INTERVAL_MS=10
```

`any` is the default because DASH traffic flows over Docker bridge interfaces
while the tracer runs with host networking. Override only when you know the
exact interface:

```bash
DASH_TRACE_INTERFACE=docker0 TRACE_INTERVAL_MS=50 ./run_experiment.sh
```

## Resource Limits

Compose applies conservative local resource limits. Each can be overridden from
the environment.

| Service | CPU env var | Default | Memory env var | Default |
|---|---|---:|---|---:|
| `http_server` | `HTTP_SERVER_CPU_LIMIT` | `0.5` | `HTTP_SERVER_MEMORY_LIMIT` | `512M` |
| `http_proxy` | `HTTP_PROXY_CPU_LIMIT` | `1.0` | `HTTP_PROXY_MEMORY_LIMIT` | `1G` |
| `http_client` | `HTTP_CLIENT_CPU_LIMIT` | `0.5` | `HTTP_CLIENT_MEMORY_LIMIT` | `512M` |
| `perf_monitor` | `PERF_MONITOR_CPU_LIMIT` | `0.25` | `PERF_MONITOR_MEMORY_LIMIT` | `256M` |
| `trace_container` | `TRACE_CONTAINER_CPU_LIMIT` | `0.5` | `TRACE_CONTAINER_MEMORY_LIMIT` | `256M` |

`perf_monitor` also accepts:

| Variable | Default | Meaning |
|---|---:|---|
| `PERF_MONITOR_INTERVAL_SECONDS` | `0.5` | Sampling interval for `/proc` CPU deltas. |

The trace output also includes `served_segments.log`, a request log with the
segment names observed during the run. `results.txt` derives the unique
resolution IDs from that same log.

### Interpreting CPU Utilization

Docker reports CPU usage as a percentage of a single host core:
- **100%** = 1 full host core
- A container with `cpus: "0.5"` can use up to **50%**
- A container with `cpus: "1.0"` can use up to **100%**

The `perf_monitor` CSV column `total_cpu_percent` always represents
percentage of **1 host core**. To calculate saturation of the container's
CPU budget:

```
saturation_pct = reported_cpu / (container_cpu_limit × 100) × 100
```

**Example:** `perf_monitor` reports `40%` for a 0.5-CPU container.
The container is using 0.4 cores (80% of its 0.5 budget, 20% headroom).

## Result Files

Each run creates:

```text
results_<label>_<cpu_model>_<timestamp>/
  container_timing.txt
  logs/
  perf/
    perf_metrics.csv
  traces/
    trace.csv
    served_segments.log
  results.txt
```

If you disable the containerized player, open the printed URL in VLC, `mpv`,
or another DASH-capable player:

```text
http://localhost:8881/manifest.mpd
```
