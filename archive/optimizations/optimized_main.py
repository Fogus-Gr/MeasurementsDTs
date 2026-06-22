"""
Optimized main.py with CPU performance enhancements for EPIC 7551P

This script provides an enhanced version of main.py with intelligent CPU optimization
for x86_64 EPIC processors. It maintains compatibility with the original interface
while adding performance improvements.

Usage:
    python optimizations/optimized_main.py --method openpose --input video.mp4 --device CPU --enable-cpu-opt
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent.parent))

import argparse
import cv2
from movenet_hpe import MoveNetHPE
from alphapose_hpe import AlphaPoseHPE
import logging

# Import our optimized implementation
from optimizations.enhanced_openvino_hpe import OptimizedOpenVINOHPE, create_optimized_hpe

# Set OpenCV threads (will be overridden by optimization if enabled)
cv2.setNumThreads(1)

class _HideAspectWarn(logging.Filter):
    def filter(self, rec):
        msg = rec.getMessage()
        return "Chosen model aspect ratio doesn't match image aspect ratio" not in msg

logging.getLogger().addFilter(_HideAspectWarn())


def main():
    parser = parse_arguments()
    args = parser.parse_args()
    
    # Print system information and optimization status
    print_system_info(args)
    
    hpe = get_hpe_method(args)
    hpe.load_model()
    hpe.main_loop()


def print_system_info(args):
    """Print system information and optimization details."""
    
    print("\n" + "="*60)
    print("🚀 OPTIMIZED HPE PERFORMANCE SYSTEM")
    print("="*60)
    print(f"Model: {args.method}")
    print(f"Device: {args.device}")
    print(f"CPU Optimization: {'✓ Enabled' if args.enable_cpu_opt else '✗ Disabled'}")
    
    if args.enable_cpu_opt and args.device == "CPU":
        # Import here to avoid issues if optimization modules aren't available
        try:
            from optimizations.cpu_performance_optimizer import EPICCPUOptimizer
            
            optimizer = EPICCPUOptimizer(target_model=args.method)
            caps = optimizer.capabilities
            
            print(f"Detected CPU: {caps.physical_cores}C/{caps.logical_cores}T")
            print(f"Target Hardware: AMD EPIC 7551P optimizations")
            
            config = optimizer.optimal_config
            print(f"Optimal Threads: {config['inference_threads']}")
            print(f"Optimal Streams: {config.get('streams', 'auto')}")
            
        except Exception as e:
            print(f"⚠️  CPU optimization detection failed: {e}")
    
    print("="*60 + "\n")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Optimized HPE with CPU performance enhancements")
    
    # Original arguments
    parser.add_argument('--method', type=str, required=True, 
                       choices=['openpose', 'alphapose', 'movenet', 'hrnet', 'ae1', 'ae2', 'ae3'],
                       help="HPE method to use")
    parser.add_argument('--input', type=str, default='0', 
                       help="Path to video or image file to use as input (default=%(default)s)")
    parser.add_argument("--output_dir", type=str, 
                       help="Path to directory where output files will be saved")
    parser.add_argument("--json", action="store_true", 
                       help="Enable export keypoints to a single json file")
    parser.add_argument("--csv", action="store_true", 
                       help="Enable export keypoints to a single csv file")
    parser.add_argument("--measurement_interval_ms", type=int, default=100,
                       help="Interval in ms for measuring transmitted data volume per interval")
    parser.add_argument("--save_video", action="store_true", 
                       help="Save results into a video file")
    parser.add_argument("--save_image", action="store_true", 
                       help="Save image with keypoints")
    parser.add_argument('--device', type=str, default="CPU", choices=['GPU', 'CPU'], 
                       help="Device to run inference on. Options: CPU, GPU")
    parser.add_argument('--detbatch', type=int, default=5, 
                       help="Detection batch size (default=%(default)s)")
    
    # New optimization arguments
    parser.add_argument('--enable-cpu-opt', action='store_true', 
                       help="Enable CPU-specific optimizations for EPIC processors")
    parser.add_argument('--disable-sys-opt', action='store_true',
                       help="Disable system-level optimizations (CPU governor, etc.)")
    parser.add_argument('--benchmark', action='store_true',
                       help="Run performance benchmark comparing standard vs optimized")
    parser.add_argument('--benchmark-duration', type=int, default=60,
                       help="Benchmark duration in seconds (default: 60)")
    
    # Advanced tuning arguments
    parser.add_argument('--force-threads', type=int,
                       help="Force specific number of inference threads (overrides optimization)")
    parser.add_argument('--force-streams', type=int,
                       help="Force specific number of streams (overrides optimization)")
    
    return parser


def get_hpe_method(args):
    """Create HPE method instance with optional optimization."""
    
    base_args_dict = base_args(args)
    
    # Model mapping with optimization support
    if args.method in ['openpose', 'hrnet', 'ae1', 'ae2', 'ae3'] and args.device == "CPU":
        # OpenVINO models - can be optimized
        
        model_type_map = {
            'openpose': 'openpose',
            'hrnet': 'higherhrnet', 
            'ae1': 'efficienthrnet1',
            'ae2': 'efficienthrnet2',
            'ae3': 'efficienthrnet3'
        }
        
        model_type = model_type_map[args.method]
        
        if args.enable_cpu_opt:
            # Use optimized version
            extra_kwargs = {}
            
            # Override with manual settings if provided
            if args.force_threads:
                extra_kwargs['ov_threads'] = args.force_threads
            if args.force_streams:
                extra_kwargs['ov_streams'] = args.force_streams
            if args.disable_sys_opt:
                # This would need to be implemented in the optimizer
                pass
            
            return OptimizedOpenVINOHPE(
                model_type=model_type,
                device=args.device,
                enable_cpu_optimization=True,
                **base_args_dict,
                **extra_kwargs
            )
        else:
            # Use standard version
            from openvino_base_hpe import OpenVINOBaseHPE
            return OpenVINOBaseHPE(
                model_type=model_type,
                device=args.device,
                **base_args_dict
            )
    
    else:
        # Non-OpenVINO models or GPU - use standard implementations
        method_map = {
            'movenet': lambda: MoveNetHPE(device=args.device, detbatch=args.detbatch, **base_args_dict),
            'alphapose': lambda: AlphaPoseHPE(device=args.device, detbatch=args.detbatch, **base_args_dict),
        }
        
        if args.method in method_map:
            return method_map[args.method]()
        else:
            raise ValueError(f"Method {args.method} not supported or requires CPU optimization")


def base_args(args):
    """Extract base arguments for HPE constructors."""
    return {
        "input_src": args.input,
        "output_dir": args.output_dir,
        "enable_json": args.json,
        "enable_csv": args.csv,
        "measurement_interval_ms": args.measurement_interval_ms,
        "save_image": args.save_image,
        "save_video": args.save_video
    }


def run_benchmark(args):
    """Run performance benchmark."""
    
    print("🏁 Starting Performance Benchmark")
    print("="*50)
    
    if not (args.method in ['openpose', 'hrnet', 'ae1', 'ae2', 'ae3'] and args.device == "CPU"):
        print("❌ Benchmarking only supported for OpenVINO CPU models")
        return
    
    from optimizations.enhanced_openvino_hpe import benchmark_optimization
    
    model_type_map = {
        'openpose': 'openpose',
        'hrnet': 'higherhrnet',
        'ae1': 'efficienthrnet1',
        'ae2': 'efficienthrnet2', 
        'ae3': 'efficienthrnet3'
    }
    
    model_type = model_type_map[args.method]
    
    try:
        results = benchmark_optimization(
            model_type=model_type,
            input_source=args.input,
            duration_seconds=args.benchmark_duration
        )
        
        print("\n🎯 BENCHMARK RESULTS")
        print("="*30)
        print(f"Model: {args.method}")
        print(f"Duration: {args.benchmark_duration}s")
        print(f"Standard FPS: {results['standard_fps']:.2f}")
        print(f"Optimized FPS: {results['optimized_fps']:.2f}")
        print(f"Improvement: {results['improvement_percent']:.1f}%")
        
        if results['improvement_percent'] > 15:
            print("✅ Significant performance improvement detected!")
        elif results['improvement_percent'] > 5:
            print("✅ Moderate performance improvement")
        else:
            print("ℹ️  Limited performance improvement - check system configuration")
            
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")


if __name__ == "__main__":
    args_parser = parse_arguments()
    parsed_args = args_parser.parse_args()
    
    if parsed_args.benchmark:
        run_benchmark(parsed_args)
    else:
        main()
