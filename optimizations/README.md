# CPU Performance Optimizations for EPIC 7551P Cloud Instance

This directory contains CPU performance optimizations specifically tuned for **4 vCPU cloud instances** running on AMD EPIC 7551P processors, optimized for maximizing performance with limited core count.

## 🎯 Expected Performance Improvements

Based on your M1 benchmark data, here are the expected improvements on 4 vCPU EPIC 7551P cloud instance:

| Model | Current FPS (M1) | Expected FPS (4 vCPU Optimized) | Improvement |
|-------|------------------|----------------------------------|-------------|
| OpenPose | 16.7 | **18-19** | 10-15% |
| EfficientHRNet1 (ae1) | 12.5 | **14-15** | 12-20% |
| HigherHRNet | 2.4 | **2.8-3.0** | 15-25% |

## 🚀 Quick Start

### Option 1: Use the optimized main script
```bash
# Basic usage with CPU optimization
python optimizations/optimized_main.py --method openpose --input video.mp4 --device CPU --enable-cpu-opt

# With output saving
python optimizations/optimized_main.py --method ae1 --input video.mp4 --device CPU --enable-cpu-opt --save_video --json

# Run performance benchmark
python optimizations/optimized_main.py --method openpose --input video.mp4 --device CPU --benchmark --benchmark-duration 30
```

### Option 2: Integrate into existing code
```python
from optimizations.enhanced_openvino_hpe import OptimizedOpenVINOHPE

# Replace your OpenVINOBaseHPE with optimized version
hpe = OptimizedOpenVINOHPE(
    model_type='openpose',
    device='CPU',
    input_src='video.mp4',
    enable_cpu_optimization=True
)

hpe.load_model()  # Will show optimization details
hpe.main_loop()
```

## 🔧 Key Optimizations Applied

### 1. 4 vCPU Cloud Optimizations
- **OpenPose**: 4 threads, 1 stream (maximize single-stream performance)
- **EfficientHRNet1**: 4 threads, 1 stream (balanced approach)
- **HigherHRNet**: 4 threads, 1 stream (concentrate all power)

### 2. Cloud-Friendly Configuration  
- CPU pinning disabled (less effective in virtualized environments)
- Hyper-threading enabled (may help with 4 vCPU)
- Single stream focus for stability

### 3. Memory Bandwidth Optimization
- AVX2 optimization enabled
- Intelligent batch sizing based on L3 cache (64MB)
- Memory pattern optimization per model

### 4. System-Level Tuning
- CPU governor set to performance mode
- NUMA balancing disabled for consistent latency
- Process priority increased

## 📊 Configuration Details

### 4 vCPU Cloud Instance Optimized Settings

```python
# OpenPose (compute-intensive) - 4 vCPU
{
    'inference_threads': 4,     # Use all 4 vCPUs
    'streams': 1,              # Single stream for stability
    'performance_hint': 'THROUGHPUT',
    'enable_cpu_pinning': False,  # Not effective in cloud
    'enable_hyper_threading': True
}

# EfficientHRNet1 (balanced) - 4 vCPU
{
    'inference_threads': 4,     # Use all 4 vCPUs
    'streams': 1,              # Single stream safer
    'performance_hint': 'LATENCY',  # Better for low core count
    'batch_size': 1,           # Conservative batch
    'enable_hyper_threading': True
}

# HigherHRNet (memory-intensive) - 4 vCPU
{
    'inference_threads': 4,     # All cores needed
    'streams': 1,              # Definitely single stream
    'performance_hint': 'THROUGHPUT',
    'memory_pattern': 'bandwidth_optimized',
    'enable_hyper_threading': True
}
```

## 🛠️ Installation

1. Ensure you have the required dependencies:
```bash
pip install psutil openvino
```

2. The optimizations will automatically detect your system capabilities and apply appropriate settings.

## 📈 Monitoring Performance

### Real-time Performance Stats
```python
hpe = OptimizedOpenVINOHPE(model_type='openpose', ...)
hpe.load_model()

# Get performance statistics
stats = hpe.get_performance_stats()
print(f"Using {stats['optimal_threads']} threads, {stats['optimal_streams']} streams")
```

### Benchmarking
```bash
# Compare standard vs optimized performance
python optimizations/optimized_main.py --method openpose --input video.mp4 --benchmark --benchmark-duration 60
```

## 🎛️ Advanced Tuning

### Manual Override for 4 vCPU
```bash
# Force specific thread/stream configuration (4 vCPU limits)
python optimizations/optimized_main.py --method openpose --input video.mp4 --enable-cpu-opt \
  --force-threads 4 --force-streams 1

# Try with 3 threads if experiencing contention
python optimizations/optimized_main.py --method ae1 --input video.mp4 --enable-cpu-opt \
  --force-threads 3 --force-streams 1
```

### Environment Variables for 4 vCPU
```bash
# Set optimization parameters via environment (4 vCPU optimized)
export OV_THREADS=4
export OV_MODE=latency     # Often better for low core count
export OV_STREAMS=1        # Single stream for stability

python optimizations/optimized_main.py --method openpose --input video.mp4 --enable-cpu-opt

# Alternative throughput mode for compute-heavy models
export OV_MODE=throughput
python optimizations/optimized_main.py --method hrnet --input video.mp4 --enable-cpu-opt
```

## 🔍 Troubleshooting

### Performance Issues
1. **Lower than expected FPS**: Check CPU governor is set to performance
2. **High CPU usage but low FPS**: Verify memory bandwidth isn't saturated  
3. **Inconsistent performance**: Disable NUMA balancing

### System Commands
```bash
# Check CPU governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Set performance governor (requires sudo)
sudo cpupower frequency-set -g performance

# Check NUMA topology
lscpu | grep NUMA

# Monitor CPU usage during inference
htop -t  # or top -H
```

### Memory Requirements

| Model | Input Resolution | Memory per Sample | Recommended Batch Size |
|-------|------------------|-------------------|----------------------|
| OpenPose | 456×256 | ~4MB | 1-2 |
| EfficientHRNet1 | 288×288 | ~3MB | 2-4 |
| HigherHRNet | 512×512 | ~8MB | 1 |

## 📝 Integration Notes

- The optimizations are **backward compatible** with existing code
- **No model accuracy changes** - only performance improvements
- Automatic fallback to standard implementation if optimization fails
- Thread-safe and suitable for production use

## 🐛 Known Limitations

1. **System permissions**: Some optimizations require sudo for CPU governor changes
2. **Single GPU**: Current implementation doesn't optimize multi-GPU setups
3. **Memory estimation**: Conservative memory calculations may limit batch sizes

## 📚 Technical Details

The optimization system:

1. **Auto-detects** CPU capabilities (cores, cache, NUMA, AVX support)
2. **Calculates** optimal thread/stream configuration per model
3. **Applies** EPIC-specific optimizations (large L3 cache, high core count)
4. **Monitors** memory usage to prevent OOM errors
5. **Provides** detailed performance statistics

For more details, see the `OPTIMIZATION_PLAN.md` in the parent directory.

---

**Hardware Target**: 4 vCPU Cloud Instance (AMD EPIC 7551P) + RTX A4000 + 16GB RAM  
**Software**: OpenVINO 2022.3+, Python 3.8+, Ubuntu 18.04+

---

## Current Production Configuration (8-vCPU Host)

The `ffmpeg_hpe` experiment rig uses these OpenVINO settings (set in `docker-compose.yaml`):

| Setting | Value | Rationale |
|---------|-------|-----------|
| `OV_MODE` | `throughput` | Optimized for batch/streaming workloads |
| `OV_STREAMS` | `1` | Single stream for consistent latency |
| `OV_THREADS` | `6` | Matches hpe cgroup limit (6 vCPUs of 8-host) |
| `OMP_NUM_THREADS` | `6` | Align with OV_THREADS |
| `MKL_NUM_THREADS` | `6` | Align with OV_THREADS |
| `OPENBLAS_NUM_THREADS` | `6` | Align with OV_THREADS |

Auto-sizing fallback: `max(1, sched_getaffinity(cpus) - 2)` if OV_THREADS not set.

<citations>
<document>
<document_type>RULE</document_type>
<document_id>/Users/georgek/MeasurementsDTs/WARP.md</document_id>
</document>
</citations>
