# Measure FLOPS Benchmark

This directory contains `measure_flops.sh`, a hardware-level benchmarking tool designed to profile the exact hardware limits pushed by your HPE inference workloads. 

## What it does

The script runs your Python workload while simultaneously capturing low-level hardware metrics. It does three things:

1. **Background Utilization Monitoring:** It launches two background processes. One uses `nvidia-smi` to poll GPU utilization and memory every 500ms, and the other uses `ps` to poll CPU and RAM usage.
2. **NVIDIA Nsight Compute Profiling:** It wraps the execution of your script in `ncu` (NVIDIA Nsight Compute). It instructs the GPU to trace highly specific, low-level hardware counters like:
   - Fused Multiply-Add (FMA) instructions (`sm__inst_executed_pipe_fma.sum`)
   - Tensor core operations (`sm__inst_executed_pipe_tensor.sum`)
   - DRAM read/write bytes
   - Warp latencies and elapsed cycles
3. **Log Normalization:** After the workload finishes, it uses `awk` to process the raw timestamps into zero-aligned relative seconds, making them easy to plot.

> [!NOTE]
> There is a block of code in `measure_flops.sh` (lines 63 to 97) that parses the `ncu` output using Python to mathematically calculate real-world GFLOPS, TOPS, and Memory Bandwidth. In this archived version of the script, that calculation block is currently disabled/commented out using a bash `<<'END_COMMENT'` block.

## Prerequisites
- A physical NVIDIA GPU
- `ncu` (NVIDIA Nsight Compute) installed and available in your system PATH
- `nvidia-smi`
- Standard Linux utilities (`awk`, `bc`)

## Usage

Pass your normal Python execution command as arguments to the script:

```bash
# General syntax:
./measure_flops.sh python3 <your_script> <args>

# Example usage for HPE:
./measure_flops.sh python3 ../../main.py --method alphapose --input ../../unit_tests/video/giphy.gif --device GPU
```

## Output Files

When it finishes, it will generate several files in your current directory:
- `perf.ncu-rep` — The raw NVIDIA profiler report that can be opened in the Nsight Compute UI.
- `cpu_mem_log.csv` — Raw CPU and Memory utilization with UNIX timestamps.
- `cpu_mem_log_elapsed.csv` — CPU and Memory utilization with zero-aligned relative time (for plotting).
- `gpu_log.csv` — Raw GPU utilization with UNIX timestamps.
- `gpu_log_elapsed.csv` — GPU utilization with zero-aligned relative time (for plotting).
