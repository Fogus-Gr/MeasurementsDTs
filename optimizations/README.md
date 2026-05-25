# CPU Performance Optimizations for EPIC 7551P Cloud Instance

This directory contains CPU performance optimizations specifically tuned for **4 vCPU cloud instances** running on AMD EPIC 7551P processors, optimized for maximizing performance with limited core count.

> **Current handoff host (May 2026):** the platform is now deployed on an **8 vCPU EPYC 7551P** cloud GPU VM. The example settings below (`inference_threads: 4`) reflect the *original* 4-vCPU calibration. The runtime auto-detector in `cpu_performance_optimizer.py` adapts to whatever core count is present — on the 8-vCPU host it picks `inference_threads = 8` (Throughput) or `7` (Latency). Bump the manual-override examples accordingly if you want full host utilisation; keep them at 4 if you want continuity with historic `results_*_4cores_CPU_*` benchmark data.

## ⚠️ Hardware Applicability

**Calibrated target:** 4 vCPU cloud GPU VM running on AMD EPYC 7551P (Zen 1, AVX2, 64 MB L3 die) + RTX A4000 + 16 GB RAM. **This is a virtualised instance, not bare metal** — the author already accounts for hypervisor constraints (CPU pinning disabled, NUMA pinning disabled). Some assumptions remain CPU-model-specific.

| Optimization knob | Source | Cloud VM (EPYC 7551P) | Cloud VM (other x86) | Bare metal |
|---|---|---|---|---|
| `inference_threads = 4` | matches 4 vCPU SKU | ✅ calibrated | ✅ transfers (any 4 vCPU) | ⚠️ re-derive for actual core count |
| `streams = 1`, `LATENCY` hint | conservative for low core count | ✅ calibrated | ✅ transfers | ⚠️ re-tune; bare metal often benefits from more streams |
| `enable_cpu_pinning = False` | virt-aware default | ✅ correct | ✅ correct | ❌ **flip to True on bare metal** — pinning is effective there |
| AVX2 path | EPYC 7551P (Zen 1) supports AVX2 | ✅ | ✅ (every modern x86 cloud VM has AVX2; AVX-512 hosts could benefit further) | ✅ (or AVX-512 on Intel SP/Sapphire Rapids) |
| 64 MB L3 batch sizing | EPYC 7551P die L3 | ✅ | ⚠️ hypervisor masks real L3; sub-optimal but not broken | ⚠️ override based on actual L3 |
| NUMA balancing disabled | host-side hint | ✅ (single vNUMA) | ✅ | ✅ (multi-socket bare metal benefits) |
| ARM / Graviton | n/a | ❌ not supported | ❌ AVX2 path breaks; would need port | ❌ |

**Decision rule for new deployments:**
- **Same VM class (4 vCPU + EPYC + 16 GB)** — use as-is.
- **Different x86 cloud VM** — use as-is; auto-detection (`psutil` + OpenVINO `ie.available_devices`) adapts thread count; L3-cache batch sizing may pick a sub-optimal-but-safe value.
- **Bare metal** — set `enable_cpu_pinning=True`, re-tune `streams` and `inference_threads` to actual core count; consider NUMA-aware `taskset` and SMT pinning that this script intentionally skips for VMs.
- **ARM / non-x86** — not supported; AVX2 assumption breaks.

## 🎯 Expected Performance Improvements

Based on M1 benchmark data, expected improvements on the EPIC 7551P cloud GPU VM. The **4 vCPU** column is the original calibration; the **8 vCPU** column is a *projection* (~1.6× scaling on inference-thread-bound workloads, capped near 1.7× by memory-bandwidth saturation) — measure on the live host and replace the projection with actual numbers as part of handoff bring-up.

| Model | Current FPS (M1) | Expected FPS (4 vCPU calibration) | Projected FPS (8 vCPU host) | Improvement vs M1 (4 vCPU / 8 vCPU) |
|-------|------------------|------------------------------------|------------------------------|--------------------------------------|
| OpenPose | 16.7 | **18-19** | **28-32** *(projected)* | 10-15% / ~70-90% |
| EfficientHRNet1 (ae1) | 12.5 | **14-15** | **22-26** *(projected)* | 12-20% / ~75-105% |
| HigherHRNet | 2.4 | **2.8-3.0** | **4.2-5.0** *(projected)* | 15-25% / ~75-110% |

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

### 1a. 4 vCPU calibration baseline (historic — matches `results_*_4cores_CPU_*` runs)
- **OpenPose**: 4 threads, 1 stream (maximize single-stream performance)
- **EfficientHRNet1**: 4 threads, 1 stream (balanced approach)
- **HigherHRNet**: 4 threads, 1 stream (concentrate all power)

### 1b. 8 vCPU current host (what the auto-detector picks on the live VM)
- **OpenPose** (Throughput): 8 threads, 1 stream — full host inference
- **EfficientHRNet1** (Latency): 7 threads, 1 stream — leaves 1 vCPU free for OS/sidecars to reduce jitter
- **HigherHRNet** (Throughput): 8 threads, 1 stream — memory-bandwidth bound; more streams unhelpful

### 2. Cloud-Friendly Configuration  
- CPU pinning disabled (ineffective in virtualised environments — vCPU↔pCore mapping is unstable)
- Hyper-threading: enabled on 4 vCPU (every thread helps); auto-detector disables it on 8 vCPU to reduce inference contention
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

### 4 vCPU calibration baseline settings (historic)

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

### 8 vCPU current host settings (auto-detected on the live VM)

```python
# OpenPose (compute-intensive) - 8 vCPU
{
    'inference_threads': 8,     # All vCPUs
    'streams': 1,              # Single stream — pose estimators are latency-sensitive
    'performance_hint': 'THROUGHPUT',
    'enable_cpu_pinning': False,  # Still ineffective in cloud
    'enable_hyper_threading': False,  # Auto-detector turns SMT OFF on 8 vCPU
}

# EfficientHRNet1 (balanced) - 8 vCPU
{
    'inference_threads': 7,     # Leave 1 vCPU for OS / sidecars
    'streams': 1,
    'performance_hint': 'LATENCY',
    'batch_size': 1,
    'enable_hyper_threading': False,
}

# HigherHRNet (memory-intensive) - 8 vCPU
{
    'inference_threads': 8,     # Memory-bandwidth bound; more threads still help
    'streams': 1,
    'performance_hint': 'THROUGHPUT',
    'memory_pattern': 'bandwidth_optimized',
    'enable_hyper_threading': False,
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

### Manual Override
```bash
# 4 vCPU calibration baseline (matches historic `results_*_4cores_CPU_*`)
python optimizations/optimized_main.py --method openpose --input video.mp4 --enable-cpu-opt \
  --force-threads 4 --force-streams 1

# 8 vCPU current host — full utilization
python optimizations/optimized_main.py --method openpose --input video.mp4 --enable-cpu-opt \
  --force-threads 8 --force-streams 1

# Conservative on 8 vCPU host (Latency hint, leaves 1 vCPU for OS/sidecars)
python optimizations/optimized_main.py --method ae1 --input video.mp4 --enable-cpu-opt \
  --force-threads 7 --force-streams 1

# Try 3 threads if you suspect 4 vCPU contention (legacy debugging)
python optimizations/optimized_main.py --method ae1 --input video.mp4 --enable-cpu-opt \
  --force-threads 3 --force-streams 1
```

### Environment Variables
```bash
# --- 4 vCPU calibration baseline ---
export OV_THREADS=4
export OV_MODE=latency     # Often better for low core count
export OV_STREAMS=1        # Single stream for stability

# --- 8 vCPU current host ---
export OV_THREADS=8
export OV_MODE=throughput  # Compute-heavy models on 8 vCPU benefit from throughput hint
export OV_STREAMS=1

python optimizations/optimized_main.py --method openpose --input video.mp4 --enable-cpu-opt

# Alternative on 8 vCPU: Latency hint with 7 threads for jitter-sensitive workloads
export OV_THREADS=7
export OV_MODE=latency
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

**Hardware Targets:**  
- *Original calibration*: 4 vCPU Cloud Instance (AMD EPIC 7551P) + RTX A4000 + 16 GB RAM  
- *Current handoff host (May 2026)*: 8 vCPU Cloud Instance (AMD EPYC 7551P) + RTX A4000 + 16 GB RAM  

**Software**: OpenVINO 2022.3+, Python 3.8+, Ubuntu 20.04+

<citations>
<document>
<document_type>RULE</document_type>
</document>
</citations>
