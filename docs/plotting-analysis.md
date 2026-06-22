# Plotting & Data Analysis — Deep Dive

## Overview
Reference for all plotting scripts, their input formats, output files, and usage.

## Plot Scripts Summary

| Script | Location | Input | Output | Usage |
|--------|----------|-------|--------|-------|
| `plot_smi_output.py` | `ffmpeg_hpe/` | `gpu_metrics.csv` | Single PNG (util + temp) | `python3 plot_smi_output.py <csv>` |
| `plot_smi_output.py` | `Measure_gpu_dcgm/` | `gpu_stats.csv` | 5 separate PNGs | `python3 plot_smi_output.py <csv>` |
| `plot_rx_bytes.py` | `ffmpeg_hpe/` | `video_rx.csv` | `rx_bytes_plot.png` | `python3 plot_rx_bytes.py <csv>` |
| `plot_rx_bytes_trimmed_reset.py` | `ffmpeg_hpe/` | `video_rx.csv` | `rx_bytes_trimmed_reset_plot.png` | `python3 plot_rx_bytes_trimmed_reset.py <csv>` |
| `plot_graph.py` | `ffmpeg_hpe/` | `perf_metrics.csv` or legacy `pid_metrics.csv` | `perf_metrics.png` / `pid_metrics.png` | `python3 plot_graph.py <csv>` |
| `plot_graph.py` | `monitor_hpe/` | `pid_metrics.csv` | `pid_metrics.png` | `python3 plot_graph.py <csv>` |
| `plot_perf_metrics.py` | `Measure_plot_cpu_perf/` (see [README](file:///home/lenovo/MeasurementsDTs/Measure_plot_cpu_perf/README.md)) | `perf stat` output | 2 plots + CSV | `python3 plot_perf_metrics.py <txt>` |

## Detailed Script Reference

> [!NOTE]
> **Design Philosophy (`ffmpeg_hpe` scripts)**
> Because these experiments often run on headless servers or inside Docker containers without a graphical interface, the `ffmpeg_hpe` plotting scripts share a common design philosophy: they take the target CSV file via a command-line argument, process it using Pandas, and silently output a `.png` file next to the original CSV. They explicitly avoid popping up interactive GUI windows (`plt.show()`) to prevent blocking execution or crashing in environments without an X-server.

### ffmpeg_hpe/plot_smi_output.py (Simple GPU Plotter)
**Input CSV columns**: timestamp, pstate, power.draw, temperature.gpu, utilization.gpu, utilization.memory, memory.total, memory.free, memory.used
**Processing**: Reads CSV with Pandas, converts timestamp to datetime. 
**Visualization**: Plots **GPU Utilization (%)** and **GPU Temperature (°C)** overlaid on the same axes over time, allowing you to easily see if the GPU was thermal-throttling during high utilization workloads.
**Output**: Saves a 15x5 `.png` file next to the input CSV.
**Usage**: `python3 plot_smi_output.py <csv>`

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

### ffmpeg_hpe/plot_rx_bytes.py (Network Stream Ingestion)
**Input**: BCC trace CSV (e.g., `video_rx.csv`)
**Processing & Trimming Logic**: When the container starts, there is usually a delay before the video stream actually connects. This script reads the CSV using Pandas and looks for the **first row with non-zero bytes** (`df.iloc[:,1].ne(0).idxmax()`). It automatically trims away all the idle time at the beginning.
**Visualization**: Uses `drawstyle='steps-post'` to plot the data. Instead of drawing a smooth interpolated curve, it draws rigid steps, which is much more accurate for visualizing the bursty nature of network packets arriving in 10ms intervals.
**Output**: `rx_bytes_plot.png` (saved next to the CSV).
**Usage**: `python3 plot_rx_bytes.py <csv>`

### ffmpeg_hpe/plot_rx_bytes_trimmed_reset.py (Zero-Aligned RX Plot)
**Input**: BCC trace CSV
**Processing**: Does the exact same trimming logic as `plot_rx_bytes.py`, but with one extra step: after trimming the idle time at the start, it **resets the timestamp column** so that the graph exactly begins at T = 0ms. This makes it much easier to compare the packet arrival times of two different runs side-by-side.
**Output**: `rx_bytes_trimmed_reset_plot.png`
**Usage**: `python3 plot_rx_bytes_trimmed_reset.py <csv>`

### monitor_hpe/plot_graph.py (59 lines)
**Input CSV columns**: timestamp (unix epoch seconds), pid, cpu_percent, mem_rss_kb, tx_bytes, rx_bytes
**Processing**: Converts timestamp to datetime, creates 2x1 subplot grid
**Plot 1 (Top)**: CPU Usage (%) over time, grid enabled
**Plot 2 (Bottom)**: Memory Usage (MB, converted from KB) over time, grid enabled
**X-axis**: Auto-formatted time (HH:MM:SS), shared between subplots, rotated labels
**Output**: Same path as input but .png extension, figure 15x10
**Suptitle**: 'Monitoring Metrics - {filename}'
**Usage**: `python3 plot_graph.py <csv_file>`

### ffmpeg_hpe/plot_graph.py (CPU & Memory Profiling)
**Input CSV columns**:
- `perf_metrics.csv`: timestamp, total_cpu_percent, total_mem_rss_kb, active_pids
- `pid_metrics.csv` (legacy): timestamp, pid, cpu_percent, mem_rss_kb, tx_bytes, rx_bytes
**Data Parsing**: Uses Pandas to parse the CSV, converting Unix timestamps into human-readable HH:MM:SS format. It automatically handles different column naming conventions.
**Headless Safety Guard**: It explicitly points `MPLCONFIGDIR` to `/tmp` to avoid Docker permission issues. It uses a clever `if os.environ.get("DISPLAY"):` guard to ensure interactive windows are never drawn unless an active X-server is present.
**Visualization**: Creates a two-tier stacked chart (CPU percentage on top, Memory converted to MB on bottom).
**Output**: Same path as input but .png extension, figure 15x9
**Usage**: `python3 plot_graph.py <csv_file>`

### Measure_plot_cpu_perf/plot_perf_metrics.py (146 lines) (see [README](file:///home/lenovo/MeasurementsDTs/Measure_plot_cpu_perf/README.md))
**Input**: Linux perf stat text output (comma-separated)
**Processing**:
- Creates output dir: `cpu_test_${timestamp}/`
- Can run perf stat directly: `sudo perf stat -a -e cpu-clock,cycles -I 100`
- Parses paired lines (cpu-clock + cycles events)
- Extracts: time, cpu_clock_value, cycles_value, cpu_util_percent
**Plot**: 1x2 subplot (CPU Utilization % and Cycles), figure 15x5
**Output**: `performance_metrics.png` and `perf_data.csv`
**Suptitle**: 'Performance Metrics Over Time'

## How to Use the Plotting Scripts

To run the plotting scripts, navigate to their respective directory (or use absolute paths) and execute them using Python 3. For scripts requiring external visualization libraries, ensure the `hpe-perf` Conda environment is active.

### 1. Plotting GPU Metrics (from `ffmpeg_hpe` run)
```bash
cd ffmpeg_hpe
conda run -n hpe-perf python3 plot_smi_output.py results_<run_name>/gpu/gpu_metrics.csv
```
*Creates `results_<run_name>/gpu/gpu_metrics.png`.*

### 2. Plotting GPU Metrics (from Standalone collector)
```bash
cd Measure_gpu_dcgm
conda run -n hpe-perf python3 plot_smi_output.py results_<run_name>/gpu_stats.csv
```
*Creates 5 detailed PNG charts in the `results_<run_name>/` directory.*

### 3. Plotting Network Ingress (RX) Bytes
```bash
cd ffmpeg_hpe
# Plot raw step graph:
conda run -n hpe-perf python3 plot_rx_bytes.py results_<run_name>/traces/bcc/video_rx.csv

# Plot trimmed graph with relative time zeroed:
conda run -n hpe-perf python3 plot_rx_bytes_trimmed_reset.py results_<run_name>/traces/bcc/video_rx.csv
```
*Creates `rx_bytes_plot.png` or `rx_bytes_trimmed_reset_plot.png` in the `traces/bcc/` directory of the run.*

### 4. Plotting CPU & Memory Usage
```bash
# For ffmpeg_hpe rig:
cd ffmpeg_hpe
conda run -n hpe-perf python3 plot_graph.py results_<run_name>/perf/perf_metrics.csv

# For monitor_hpe rig:
cd monitor_hpe
conda run -n hpe-perf python3 plot_graph.py results_<run_name>/pid_metrics.csv
```
*Creates a subplot PNG (`perf_metrics.png` / `pid_metrics.png`) in the folder of the target CSV file.*

### 5. Plotting Standalone CPU Cycles (Linux perf stat)
```bash
cd Measure_plot_cpu_perf
conda run -n hpe-perf python3 plot_perf_metrics.py <path_to_perf_output.txt>
```
*Creates `performance_metrics.png` and `perf_data.csv` in a new `cpu_test_<timestamp>` folder.*

---

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
