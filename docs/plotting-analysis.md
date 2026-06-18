# Plotting & Data Analysis — Deep Dive

## Overview
Reference for all plotting scripts, their input formats, output files, and usage.

## Plot Scripts Summary

| Script | Location | Input | Output | Usage |
|--------|----------|-------|--------|-------|
| plot_smi_output.py | ffmpeg_hpe/ | gpu_metrics.csv | Single PNG (util + temp) | `python3 plot_smi_output.py <csv>` |
| plot_smi_output.py | Measure_gpu_dcgm/ | gpu_stats.csv | 5 separate PNGs | `python3 plot_smi_output.py <csv>` |
| plot_rx_bytes.py | ffmpeg_hpe/ | hpe_video_rx.csv | rx_bytes_plot.png | `python3 plot_rx_bytes.py` |
| plot_rx_bytes_trimmed_reset.py | ffmpeg_hpe/ | hpe_video_rx.csv | rx_bytes_plot.png | `python3 plot_rx_bytes_trimmed_reset.py` |
| plot_graph.py | ffmpeg_hpe/ | `perf_metrics.csv` or legacy `pid_metrics.csv` | `perf_metrics.png` / `pid_metrics.png` | `python3 plot_graph.py <csv>` |
| plot_graph.py | monitor_hpe/ | pid_metrics.csv | pid_metrics.png | `python3 plot_graph.py <csv>` |
| plot_perf_metrics.py | Measure_plot_cpu_perf/ | perf stat output | 2 plots + CSV | `python3 plot_perf_metrics.py <txt>` |

## Detailed Script Reference

### ffmpeg_hpe/plot_smi_output.py (Simple GPU Plotter)
**Input CSV columns**: timestamp, pstate, power.draw, temperature.gpu, utilization.gpu, utilization.memory, memory.total, memory.free, memory.used
**Processing**: Reads CSV, converts timestamp to datetime, plots GPU utilization % and temperature on same axes
**Output**: Replaces .csv extension with .png in same directory
**Figure**: 15x5, two series (GPU Utilization, GPU Temp), legend
**Note**: Simpler than Measure_gpu_dcgm version — produces single combined plot

### Measure_gpu_dcgm/plot_smi_output.py (Comprehensive GPU Plotter — 106 lines)
**Input CSV**: Same nvidia-smi format but with 3 header rows to skip
**Timestamp format**: `YYYY/MM/DD HH:MM:SS.fff`
**Unit stripping**: Removes ' W', ' %', ' MiB' from values
**Creates output directory**: `results_${timestamp}/`

**5 Output Plots** (all 12x4 or 12x5):
1. **gpu_util.png** — GPU & Memory Utilization (%), blue + red lines, grid
2. **gpu_temp.png** — Temperature (°C), orange line
3. **gpu_mem.png** — Memory Used vs Free (MiB), purple + green
4. **gpu_pstate.png** — Power State transitions (P0=Max Perf to P8=Idle), step plot
5. **gpu_power.png** — Power draw (Watts), magenta line

All plots: rotated x-labels (45°), grid enabled, tight layout

### ffmpeg_hpe/plot_rx_bytes.py (24 lines)
**Input**: BCC trace CSV (hpe_video_rx.csv)
**Processing**:
- Read CSV with pandas
- Trim to first non-zero RX value: `df.iloc[:,1].ne(0).idxmax()`
- Reset index after trimming
**Plot**: 15x5 figure, step function (`drawstyle='steps-post'`), "Timestamp (ms)" x-axis, "RX bytes per 10ms" y-axis
**Output**: `rx_bytes_plot.png` (current directory)
**Note**: May have hardcoded paths — check before running

### ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py
**Similar to plot_rx_bytes.py** but:
- X-axis reset to 0 (relative time from first non-zero)
- Trimmed view for cleaner presentation
- Same step-function visualization

### monitor_hpe/plot_graph.py (59 lines)
**Input CSV columns**: timestamp (unix epoch seconds), pid, cpu_percent, mem_rss_kb, tx_bytes, rx_bytes
**Processing**: Converts timestamp to datetime, creates 2x1 subplot grid
**Plot 1 (Top)**: CPU Usage (%) over time, grid enabled
**Plot 2 (Bottom)**: Memory Usage (MB, converted from KB) over time, grid enabled
**X-axis**: Auto-formatted time (HH:MM:SS), shared between subplots, rotated labels
**Output**: Same path as input but .png extension, figure 15x10
**Suptitle**: 'Monitoring Metrics - {filename}'
**Usage**: `python3 plot_graph.py <csv_file>`

### ffmpeg_hpe/plot_graph.py (61 lines)
**Input CSV columns**:
- `perf_metrics.csv`: timestamp, total_cpu_percent, total_mem_rss_kb, active_pids
- `pid_metrics.csv` (legacy): timestamp, pid, cpu_percent, mem_rss_kb, tx_bytes, rx_bytes
**Processing**: Converts timestamp to datetime, creates 2x1 subplot grid
**Plot 1 (Top)**: CPU Usage (%) over time, grid enabled
**Plot 2 (Bottom)**: Memory Usage (MB, converted from KB) over time, grid enabled
**X-axis**: Auto-formatted time (HH:MM:SS), shared between subplots, rotated labels
**Output**: Same path as input but .png extension, figure 15x9
**Suptitle**: 'Monitoring Metrics - {filename}'
**Usage**: `python3 plot_graph.py <csv_file>`

### Measure_plot_cpu_perf/plot_perf_metrics.py (146 lines)
**Input**: Linux perf stat text output (comma-separated)
**Processing**:
- Creates output dir: `cpu_test_${timestamp}/`
- Can run perf stat directly: `sudo perf stat -a -e cpu-clock,cycles -I 100`
- Parses paired lines (cpu-clock + cycles events)
- Extracts: time, cpu_clock_value, cycles_value, cpu_util_percent
**Plot**: 1x2 subplot (CPU Utilization % and Cycles), figure 15x5
**Output**: `performance_metrics.png` and `perf_data.csv`
**Suptitle**: 'Performance Metrics Over Time'

## CSV Format Reference

### gpu_metrics.csv (nvidia-smi output)
```csv
timestamp,pstate,power.draw,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used
2025/07/07 17:13:58.123,P0,150.00,65,85,45,24576,12000,12576
```

### pid_metrics.csv (bpftrace monitoring)
```csv
timestamp,pid,cpu_percent,mem_rss_kb,tx_bytes,rx_bytes
1689000000.123,12345,85.3,2048000,1234,567890
```

### hpe_video_rx.csv (BCC trace)
```csv
timestamp_ms,rx_video_bytes_delta,rx_video_bytes_current,rx_video_bytes_prev,dt_ms
1689000000000,1234,567890,566656,10.2
```

### perf_data.csv (perf stat parsed)
```csv
time,cpu_clock,cycles,cpu_util
0.100,99.50,3200000000,99.5
0.200,98.20,3150000000,98.2
```

## Quick Analysis Commands

```bash
# GPU: average utilization
awk -F, 'NR>1 {sum+=$5; n++} END {print sum/n "%"}' gpu_metrics.csv

# GPU: max temperature
awk -F, 'NR>1 {if($4>max) max=$4} END {print max "°C"}' gpu_metrics.csv

# Network: total MB received
awk -F, 'NR>1 {sum+=$2} END {print sum/1024/1024 " MB"}' hpe_video_rx.csv

# Network: average throughput (Mbit/s)
awk -F, 'NR>1 && $2>0 {sum+=$2; n++} END {print (sum/n)*8/1024/1024*100 " Mbit/s avg per active interval"}' hpe_video_rx.csv

# CPU: average usage
awk -F, 'NR>1 {sum+=$3; n++} END {print sum/n "%"}' pid_metrics.csv

# Memory: peak RSS (MB)
awk -F, 'NR>1 {if($4>max) max=$4} END {print max/1024 " MB"}' pid_metrics.csv
```
