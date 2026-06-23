# CPU Performance Measurement & Plotting Tool

This directory contains a standalone profiling tool suite designed to measure, parse, and visualize CPU performance metrics (utilization and CPU cycles) using Linux `perf`. It can be run either locally on the host machine or inside a containerized Docker environment.

## Directory Contents

* **`Dockerfile`**: Sets up a containerized Ubuntu 22.04 environment pre-configured with the required Linux profiling utilities (`linux-tools`), Python 3, and data visualization libraries (`pandas`, `matplotlib`, `numpy`).
* **`run_perf_plot.sh`**: The orchestrator shell script. It parses target process IDs (PIDs) from `/pids/dash.pid`, measures their CPU clock and cycles in parallel using `perf stat` for 10 seconds, and passes the output to the Python script for visualization.
* **`plot_perf_metrics.py`**: The parsing and visualization script. It extracts timing, CPU utilization percentage, and cycles from the `perf` output, saves them as a structured CSV (`perf_data.csv`), and generates plots (`performance_metrics.png`) in a timestamped output directory.

---

## What is Being Measured?

The tool records two primary kernel and hardware events using `perf stat`:

1. **`cpu-clock` (Software Event)**:
   * Measures the actual execution time spent by the CPU on the targeted process (or system-wide) in milliseconds.
   * Unlike wall-clock time, this clock only increments when the CPU is actively executing instructions for the process (i.e. it doesn't count time spent waiting on disk/network I/O or sleeping).

2. **`cycles` (Hardware Event)**:
   * Measures the raw hardware instruction clock cycles executed by the CPU cores.
   * Handled by the CPU's PMU (Performance Monitoring Unit), this counts the actual clock transitions (e.g., on a 3.0 GHz processor core, a fully saturated thread uses 3 billion cycles per second). It indicates the raw computational pressure on the physical CPU.

3. **`CPU Utilization`**:
   * Derived from the duty cycle of the active CPU cores during the sampling interval. 
   * Fully utilizing a single core yields `100%`, while a multi-threaded workload utilizing multiple cores can scale up to `N * 100%` (where `N` is the number of cores).

---

## Architecture & Workflows

### 1. Target PID Profiling (Orchestrated by `run_perf_plot.sh`)
This is the default mode used when running the Docker container.
1. The script reads active process PIDs from a volume-mounted file `/pids/dash.pid`.
2. It executes `perf stat` specifically for each target PID:
   ```bash
   sudo perf stat -p <PID> -e cpu-clock,cycles -I 100 --interval-count 100 -x ,
   ```
   * `-p <PID>`: Targets the specific process.
   * `-e cpu-clock,cycles`: Measures CPU clock and processor cycles.
   * `-I 100`: Captures samples every 100ms.
   * `--interval-count 100`: Collects 100 intervals (total profiling duration is 10 seconds).
   * `-x ,`: Outputs data in comma-separated value (CSV) format.
3. The raw logs are written to `perf_output_<PID>.txt`.
4. `plot_perf_metrics.py` parses each raw text file and generates visualization graphs and clean CSV outputs.

### 2. Live System-wide Profiling (Fallback / Direct Python Run)
If you execute the Python script directly on the host without any command-line arguments:
```bash
python3 plot_perf_metrics.py
```
1. It automatically runs a live system-wide capture for 10 seconds:
   ```bash
   sudo perf stat -a -e cpu-clock,cycles -I 100 --interval-count 100 -x ,
   ```
   * `-a`: Captures performance metrics across all CPUs system-wide.
2. Parses the live stdout and saves the visualization graphs and raw CSV.

---

## Getting Started

### Prerequisites
* **Linux Kernel Profiler**: `perf` must be installed on your host machine.
* **Sudo Permissions**: Running `perf` commands requires root privileges.
* **Kernel Configuration**: Depending on your system security configuration, you may need to allow non-privileged perf events:
  ```bash
  sudo sysctl -w kernel.perf_event_paranoid=-1
  ```

### Running Locally

To profile a custom file already captured by `perf`:
```bash
python3 plot_perf_metrics.py <path_to_perf_output.txt>
```

To run a live system-wide capture and plot:
```bash
sudo python3 plot_perf_metrics.py
```

### Running with Docker

1. **Build the Docker Image**:
   ```bash
   docker build -t measure-cpu-perf .
   ```

2. **Run the Container**:
   Ensure you mount the directory containing your target PIDs file (`dash.pid`) to `/pids` in the container, and give the container `SYS_ADMIN` capability (or run as privileged) so `perf` can hook into host processes:
   ```bash
   docker run --privileged -v /path/to/pids:/pids measure-cpu-perf
   ```

## Integrating with Experiment Rigs (`recent-dash` and `ffmpeg_hpe`)

This profiling tool can easily run alongside the repository's main experiment rigs to analyze target processes.

### 1. Using with `recent-dash` (Proxy PIDs)
The `recent-dash` rig writes the proxy container process IDs to `recent-dash/pids/dash.pid`.

* **Option A: Containerized Execution**
  Build the CPU perf image, then mount the `recent-dash/pids` directory to the container:
  ```bash
  docker build -t measure-cpu-perf ./Measure_plot_cpu_perf
  docker run --privileged -v /home/lenovo/MeasurementsDTs/recent-dash/pids:/pids measure-cpu-perf
  ```

* **Option B: Local Script Execution**
  Run the profiler manually for each PID:
  ```bash
  for PID in $(cat /home/lenovo/MeasurementsDTs/recent-dash/pids/dash.pid); do
    sudo perf stat -p "$PID" -e cpu-clock,cycles -I 100 --interval-count 100 -x , 2> "perf_proxy_${PID}.txt"
    conda run -n hpe-perf python3 plot_perf_metrics.py "perf_proxy_${PID}.txt"
  done
  ```

### 2. Using with `ffmpeg_hpe` (HPE Process PID)
The `ffmpeg_hpe` rig writes the HPE container's host process ID to `ffmpeg_hpe/pids/hpe.pid`.

* **Option A: Containerized Execution**
  Since the container expects a `dash.pid` file, map the host `hpe.pid` directly as `dash.pid` inside the container:
  ```bash
  docker build -t measure-cpu-perf ./Measure_plot_cpu_perf
  docker run --privileged -v /home/lenovo/MeasurementsDTs/ffmpeg_hpe/pids/hpe.pid:/pids/dash.pid measure-cpu-perf
  ```

* **Option B: Local Script Execution**
  Run `perf` on the active HPE process PID, then plot the resulting file:
  ```bash
  HPE_PID=$(cat /home/lenovo/MeasurementsDTs/ffmpeg_hpe/pids/hpe.pid)
  sudo perf stat -p "$HPE_PID" -e cpu-clock,cycles -I 100 --interval-count 100 -x , 2> hpe_perf_raw.txt
  conda run -n hpe-perf python3 plot_perf_metrics.py hpe_perf_raw.txt
  ```
