# recent-dash Validation Notes - 2026-06-23

## What Changed

- Rewired the experiment runner to use the active `cvlc` DASH player service.
- Restored the default experiment to the unrestricted full MPD
  (`DASH_MANIFEST=manifest.mpd`).
- Added a Compose env file per result directory so runtime overrides such as
  `DASH_MANIFEST=manifest_2160.mpd` reliably reach Docker Compose, including
  when Docker is called through a sudo wrapper.
- Raised the proxy request-count termination limit from `-n 65` to `-n 1000`.
  The `-n` option is a total request limit, not a resolution selector.
- Added fixed-resolution single-representation MPDs for 1080p, 1440p, and
  2160p controlled runs.
- Changed `served_segments.log` to include explicit resolution IDs:

```text
timestamp_ms,resolution,segment
```

## Validated Runs

Full-MPD ABR path:

- Result directory:
  `results_dash_IntelR_XeonR_Gold_6254_CPU_@_3.10GHz_20260623_215712`
- Command shape:
  `DASH_MANIFEST=manifest.mpd EXPERIMENT_DURATION_SECONDS=660 ./run_experiment.sh`
- Observed requested video resolutions: `360` and `2160`.
- Observed request mix in `served_segments.log`: 37 audio rows, 2 360p rows,
  and 37 2160p rows.
- Observed DASH proxy byte totals in `trace.csv`: 409,524,945 RX bytes and
  409,523,101 TX bytes.
- Interpretation: with the full MPD exposed, the player started low and then
  requested 2160p segments, so the unrestricted MPD path can reach the maximum
  available representation.

Fixed 2160p path:

- Result directory:
  `results_dash_IntelR_XeonR_Gold_6254_CPU_@_3.10GHz_20260623_222802`
- Command shape:
  `DASH_MANIFEST=manifest_2160.mpd EXPERIMENT_DURATION_SECONDS=120 ./run_experiment.sh`
- `compose.env` confirms `DASH_MANIFEST=manifest_2160.mpd`.
- `served_segments.log` contained 8 rows, all with resolution `2160`.
- Observed DASH proxy byte totals in `trace.csv`: 75,223,853 RX bytes and
  75,212,517 TX bytes.
- No HTTP 404 or segment-read failure was found in the collected service logs.
- Interpretation: this validates the fixed-resolution, no multi-representation
  ABR control path.

## What Remains

- VLC still logs non-fatal headless DBus/globalhotkey interface warnings before
  falling back to the dummy interface.
- 2160p playback can emit late-frame/drop warnings under the current proxy and
  CPU limits. Those warnings do not by themselves mean segment requests failed.
- The full 660-second full-MPD run validated sustained max-resolution traffic,
  not complete playback of every 2160p segment. With current proxy/server rate
  settings, consuming the entire 2160p media would require a longer run or
  higher service rates.
- The `http_client` service itself does not log the selected resolutions. The
  authoritative resolution/request artifact is `traces/served_segments.log`,
  written by `trace_container`.
