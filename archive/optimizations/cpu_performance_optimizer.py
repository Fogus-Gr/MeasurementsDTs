"""
CPU Performance Optimizer for x86_64 EPIC 7551P (32C/64T)

This module provides intelligent CPU optimization for OpenVINO models on high-core-count
x86_64 systems, with specific tuning for AMD EPIC processors.

Target Hardware: AMD EPIC 7551P (32 cores, 64 threads, 2.0-3.0 GHz)
"""

import os
import psutil
import platform
import subprocess
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import openvino as ov
from openvino import properties as props


@dataclass
class CPUCapabilities:
    """System CPU capabilities and characteristics."""
    physical_cores: int
    logical_cores: int
    base_frequency: float  # GHz
    max_frequency: float   # GHz
    cache_l3_mb: int
    numa_nodes: int
    architecture: str
    supports_avx2: bool
    supports_avx512: bool


class EPICCPUOptimizer:
    """
    CPU optimizer specifically tuned for AMD EPIC processors.
    
    Key optimizations:
    - NUMA-aware thread allocation
    - Cache-optimized batch sizing
    - Workload-specific thread management
    - Memory bandwidth optimization
    """
    
    def __init__(self, target_model: str = None):
        self.capabilities = self._detect_cpu_capabilities()
        self.target_model = target_model
        self.optimal_config = self._calculate_optimal_config()
    
    def _detect_cpu_capabilities(self) -> CPUCapabilities:
        """Detect detailed CPU capabilities for optimization."""
        
        # Get basic CPU info
        # In virtualized environments, use logical cores as the primary count
        # since vCPUs are what we can actually use
        logical_cores = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        
        # For virtualized environments, treat logical cores as available cores
        # since that's what the VM can actually use
        available_cores = logical_cores
        
        # Try to get CPU frequency info
        try:
            freq_info = psutil.cpu_freq()
            base_freq = freq_info.current / 1000.0 if freq_info else 2.0
            max_freq = freq_info.max / 1000.0 if freq_info else 3.0
        except:
            base_freq, max_freq = 2.0, 3.0
        
        # Detect CPU features
        try:
            # Check for AVX support
            result = subprocess.run(['lscpu'], capture_output=True, text=True)
            cpu_info = result.stdout.lower()
            supports_avx2 = 'avx2' in cpu_info
            supports_avx512 = 'avx512' in cpu_info
        except:
            supports_avx2, supports_avx512 = True, False  # Conservative defaults
        
        # NUMA detection
        try:
            numa_nodes = len([d for d in os.listdir('/sys/devices/system/node/') 
                            if d.startswith('node')])
        except:
            numa_nodes = 1
        
        return CPUCapabilities(
            physical_cores=available_cores,  # Use available cores for virtualized environments
            logical_cores=logical_cores,
            base_frequency=base_freq,
            max_frequency=max_freq,
            cache_l3_mb=64,  # EPIC 7551P has 64MB L3
            numa_nodes=numa_nodes,
            architecture=platform.machine(),
            supports_avx2=supports_avx2,
            supports_avx512=supports_avx512
        )
    
    def _calculate_optimal_config(self) -> Dict:
        """Calculate optimal OpenVINO configuration for EPIC processor."""
        
        # Cloud instance optimizations based on available cores
        available_cores = self.capabilities.physical_cores
        
        if available_cores <= 4:
            # Low core count cloud optimizations - maximize utilization
            
            # Use all available cores for inference (cloud instances are dedicated)
            available_cores = self.capabilities.physical_cores
            
            # For different workload patterns on 4 vCPU
            configs = {
                'throughput_heavy': {
                    'inference_threads': available_cores,  # Use all 4 cores
                    'streams': 1,  # Single stream for consistency
                    'performance_hint': 'THROUGHPUT',
                    'enable_cpu_pinning': False,  # Less effective in cloud
                    'enable_hyper_threading': True,  # May help on 4 vCPU
                },
                'latency_optimized': {
                    'inference_threads': max(2, available_cores - 1),  # Leave 1 for OS
                    'streams': 1,
                    'performance_hint': 'LATENCY',
                    'enable_cpu_pinning': False,
                    'enable_hyper_threading': True,
                },
                'balanced': {
                    'inference_threads': available_cores,  # Use all cores
                    'streams': 1,  # Single stream optimal for 4 vCPU
                    'performance_hint': 'LATENCY',  # Better for low core count
                    'enable_cpu_pinning': False,
                    'enable_hyper_threading': True,
                }
            }
            
            # Model-specific tuning based on your benchmark data
            if self.target_model:
                return self._tune_for_model(configs)
            else:
                return configs['balanced']
        
        elif available_cores == 8:
            # 8 vCPU cloud instance optimizations - fine-tuned for 5.0 FPS
            configs = {
                'throughput_heavy': {
                    'inference_threads': 8,  # Use all 8 vCPUs
                    'streams': 1,  # Single stream for AE1 model
                    'performance_hint': 'THROUGHPUT',
                    'enable_cpu_pinning': False,  # Less effective in cloud
                    'enable_hyper_threading': False,  # EPYC 7551P doesn't have hyper-threading
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized',  # Better memory access
                },
                'latency_optimized': {
                    'inference_threads': 7,  # Leave 1 for OS (like your manual setup)
                    'streams': 1,
                    'performance_hint': 'LATENCY',
                    'enable_cpu_pinning': False,
                    'enable_hyper_threading': False,
                    'batch_size': 1,
                    'memory_pattern': 'latency_optimized',  # Match your manual setup
                },
                'balanced': {
                    'inference_threads': 7,  # Use 7 threads like your manual setup
                    'streams': 1,  # Single stream optimal for AE1
                    'performance_hint': 'LATENCY',  # Match your manual setup
                    'enable_cpu_pinning': False,
                    'enable_hyper_threading': False,
                    'batch_size': 1,
                    'memory_pattern': 'latency_optimized',  # Match your manual setup
                }
            }
            
            # Model-specific tuning
            if self.target_model:
                return self._tune_for_model(configs)
            else:
                return configs['balanced']
        
        elif self.capabilities.physical_cores >= 32:
            # High core count optimizations (original EPIC 7551P)
            
            # Leave 2-4 cores for OS and other tasks
            available_cores = max(1, self.capabilities.physical_cores - 4)
            
            # For different workload patterns
            configs = {
                'throughput_heavy': {
                    'inference_threads': available_cores,
                    'streams': min(8, available_cores // 4),
                    'performance_hint': 'THROUGHPUT',
                    'enable_cpu_pinning': True,
                    'enable_hyper_threading': False,  # Better for inference
                },
                'latency_optimized': {
                    'inference_threads': min(8, available_cores // 4),
                    'streams': 1,
                    'performance_hint': 'LATENCY',
                    'enable_cpu_pinning': True,
                    'enable_hyper_threading': False,
                },
                'balanced': {
                    'inference_threads': min(16, available_cores // 2),
                    'streams': min(4, available_cores // 8),
                    'performance_hint': 'THROUGHPUT',
                    'enable_cpu_pinning': True,
                    'enable_hyper_threading': False,
                }
            }
            
            # Model-specific tuning based on your benchmark data
            if self.target_model:
                return self._tune_for_model(configs)
            else:
                return configs['balanced']
        
        else:
            # Medium core count systems (8-16 cores)
            return {
                'inference_threads': max(1, self.capabilities.physical_cores - 1),
                'streams': 1,
                'performance_hint': 'LATENCY',
                'enable_cpu_pinning': True,
                'enable_hyper_threading': True,
            }
    
    def _tune_for_model(self, base_configs: Dict) -> Dict:
        """Fine-tune configuration based on specific model requirements."""
        
        # Different optimizations based on core count
        if self.capabilities.physical_cores <= 4:
            # 4 vCPU cloud optimizations - conservative settings
            model_optimizations = {
                'openpose': {
                    # OpenPose on 4 vCPU - use all cores, single stream
                    'preferred_config': 'throughput_heavy',
                    'inference_threads': 4,  # Use all 4 vCPUs
                    'streams': 1,  # Single stream for stability
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized'
                },
                
                'efficienthrnet1': {  # ae1
                    # Lighter model - can try 2 streams
                    'preferred_config': 'balanced', 
                    'inference_threads': 4,  # Use all cores
                    'streams': 1,  # Single stream safer
                    'batch_size': 1,  # Conservative batch
                    'memory_pattern': 'cache_optimized'
                },
                
                'higherhrnet': {
                    # Heavy model - maximum single-threaded performance
                    'preferred_config': 'throughput_heavy',
                    'inference_threads': 4,  # All cores needed
                    'streams': 1,  # Definitely single stream
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized'
                }
            }
        elif self.capabilities.physical_cores == 8:
            # 8 vCPU optimizations - your current setup
            model_optimizations = {
                'openpose': {
                    'preferred_config': 'throughput_heavy',
                    'inference_threads': 8,  # Use all 8 vCPUs
                    'streams': 1,  # Single stream for stability
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized'
                },
                
                'efficienthrnet1': {  # ae1 - your main model
                    'preferred_config': 'latency_optimized',  # Use latency config for better FPS
                    'inference_threads': 7,  # Match your manual setup (7 threads)
                    'streams': 1,  # Single stream optimal for AE1
                    'batch_size': 1,
                    'memory_pattern': 'latency_optimized',  # Match your manual setup
                    'performance_hint': 'LATENCY'  # Explicitly set latency mode
                },
                
                'higherhrnet': {
                    'preferred_config': 'throughput_heavy',
                    'inference_threads': 8,  # Use all 8 vCPUs
                    'streams': 1,  # Single stream for heavy model
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized'
                }
            }
        else:
            # High core count optimizations (original settings)
            model_optimizations = {
                'openpose': {
                    # Based on your benchmark: 16.71 FPS with latency/1/6
                    # OpenPose is compute-intensive, benefits from more cores
                    'preferred_config': 'throughput_heavy',
                    'inference_threads': 24,  # Increased from base
                    'streams': 6,  # Matches your best result
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized'
                },
                
                'efficienthrnet1': {  # ae1
                    # Based on your benchmark: 12.51 FPS with latency/1/4
                    # Smaller model, can benefit from higher parallelism
                    'preferred_config': 'balanced',
                    'inference_threads': 16,
                    'streams': 4,  # Matches your better result
                    'batch_size': 2,
                    'memory_pattern': 'cache_optimized'
                },
                
                'higherhrnet': {
                    # Based on your benchmark: 2.39 FPS - very compute heavy
                    # Needs maximum compute resources
                    'preferred_config': 'throughput_heavy',
                    'inference_threads': 28,  # Nearly all cores
                    'streams': 2,  # Limited streams for heavy model
                    'batch_size': 1,
                    'memory_pattern': 'bandwidth_optimized'
                }
            }
        
        if self.target_model in model_optimizations:
            model_config = model_optimizations[self.target_model]
            base_config = base_configs[model_config['preferred_config']].copy()
            
            # Override with model-specific settings
            base_config.update({k: v for k, v in model_config.items() 
                              if k != 'preferred_config'})
            
            return base_config
        
        return base_configs['balanced']
    
    def configure_openvino_core(self, core: ov.Core) -> ov.Core:
        """Apply optimal CPU configuration to OpenVINO core."""
        
        config = self.optimal_config
        
        # Core CPU properties - fine-tuned for 5.0 FPS
        cpu_props = {
            props.inference_num_threads: config['inference_threads'],
            props.hint.performance_mode: (
                props.hint.PerformanceMode.THROUGHPUT 
                if config['performance_hint'] == 'THROUGHPUT'
                else props.hint.PerformanceMode.LATENCY
            ),
            props.hint.enable_cpu_pinning: config['enable_cpu_pinning'],
            props.hint.enable_hyper_threading: config['enable_hyper_threading'],
        }
        
        # Fine-tuning parameters for better FPS
        if config.get('memory_pattern') == 'latency_optimized':
            cpu_props.update({
                props.hint.num_requests: 1,  # Single request for latency
            })
        elif config.get('memory_pattern') == 'bandwidth_optimized':
            cpu_props.update({
                props.hint.num_requests: 1,  # Single request
            })
        
        # Additional fine-tuning for 8 vCPU setup
        if self.capabilities.physical_cores == 8:
            cpu_props.update({
                props.hint.scheduling_core_type: props.hint.SchedulingCoreType.ANY_CORE,
            })
        
        # Add streams configuration if specified
        if 'streams' in config:
            cpu_props[props.num_streams] = config['streams']
        
        # EPIC-specific optimizations
        if self.capabilities.physical_cores >= 32:
            # High core count optimizations
            cpu_props.update({
                # Optimize for NUMA on multi-socket systems
                props.affinity: "NUMA",
                # Enable parallel execution across NUMA nodes
                props.hint.num_requests: config.get('streams', 1) * 2,
            })
        
        # AVX optimizations
        if self.capabilities.supports_avx512:
            # Enable AVX-512 if available (rare on EPIC, but check)
            os.environ['OMP_NUM_THREADS'] = str(config['inference_threads'])
            os.environ['MKL_NUM_THREADS'] = str(config['inference_threads'])
        elif self.capabilities.supports_avx2:
            # Optimize for AVX2 (standard on EPIC)
            os.environ['OMP_NUM_THREADS'] = str(config['inference_threads'])
            os.environ['MKL_NUM_THREADS'] = str(config['inference_threads'])
        
        # Apply configuration
        core.set_property("CPU", cpu_props)
        
        print(f"[CPU Optimizer] Applied configuration for {self.capabilities.physical_cores}C/{self.capabilities.logical_cores}T system:")
        print(f"  - Inference threads: {config['inference_threads']}")
        print(f"  - Streams: {config.get('streams', 'auto')}")
        print(f"  - Performance hint: {config['performance_hint']}")
        print(f"  - CPU pinning: {config['enable_cpu_pinning']}")
        print(f"  - Hyper-threading: {config['enable_hyper_threading']}")
        
        return core
    
    def get_recommended_batch_size(self, model_name: str, input_resolution: Tuple[int, int]) -> int:
        """Get recommended batch size based on model and system capabilities."""
        
        # Estimate memory usage per sample
        h, w = input_resolution
        memory_per_sample_mb = (h * w * 3 * 4) / (1024 * 1024)  # Float32 RGB
        
        # Available memory estimation (leave 4GB for system)
        available_memory_gb = 12  # Conservative for 16GB system
        available_memory_mb = available_memory_gb * 1024
        
        # Model-specific memory multipliers based on complexity
        model_memory_multipliers = {
            'openpose': 3.0,      # Memory intensive
            'efficienthrnet1': 2.0,
            'efficienthrnet2': 2.5,
            'efficienthrnet3': 3.5,
            'higherhrnet': 4.0,   # Very memory intensive
            'movenet': 1.5,
        }
        
        multiplier = model_memory_multipliers.get(model_name, 2.0)
        estimated_memory_per_sample = memory_per_sample_mb * multiplier
        
        # Calculate maximum batch size
        max_batch_from_memory = int(available_memory_mb / estimated_memory_per_sample)
        
        # CPU-based limitations
        cores_available = self.optimal_config['inference_threads']
        max_batch_from_cpu = max(1, cores_available // 4)
        
        # Take the minimum but ensure at least 1
        recommended_batch = max(1, min(max_batch_from_memory, max_batch_from_cpu, 8))
        
        print(f"[Batch Optimizer] Recommended batch size for {model_name}: {recommended_batch}")
        print(f"  - Memory limit: {max_batch_from_memory}")
        print(f"  - CPU limit: {max_batch_from_cpu}")
        
        return recommended_batch
    
    def optimize_system_settings(self):
        """Apply system-level optimizations for inference performance."""
        
        optimizations_applied = []
        
        # CPU governor optimization (if available)
        try:
            # Set CPU governor to performance mode
            subprocess.run(['sudo', 'cpupower', 'frequency-set', '-g', 'performance'], 
                         check=True, capture_output=True)
            optimizations_applied.append("CPU governor set to performance")
        except:
            pass
        
        # Disable CPU power management features that can cause latency spikes
        power_optimizations = [
            "echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true",
            "echo 0 | sudo tee /proc/sys/kernel/numa_balancing 2>/dev/null || true",
        ]
        
        for cmd in power_optimizations:
            try:
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                optimizations_applied.append(f"Applied: {cmd.split('|')[0].strip()}")
            except:
                continue
        
        # Set process priority
        try:
            os.nice(-10)  # Higher priority for inference process
            optimizations_applied.append("Process priority increased")
        except:
            pass
        
        if optimizations_applied:
            print(f"[System Optimizer] Applied {len(optimizations_applied)} system optimizations")
            for opt in optimizations_applied:
                print(f"  - {opt}")
        
        return optimizations_applied


def create_optimized_openvino_core(model_name: str) -> ov.Core:
    """
    Create an optimized OpenVINO core for EPIC 7551P processor.
    
    Args:
        model_name: Name of the model to optimize for
        
    Returns:
        Configured OpenVINO core
    """
    optimizer = EPICCPUOptimizer(target_model=model_name)
    
    # Apply system optimizations
    optimizer.optimize_system_settings()
    
    # Create and configure core
    core = ov.Core()
    optimized_core = optimizer.configure_openvino_core(core)
    
    return optimized_core


# Convenience functions for direct use
def get_optimal_threads_for_model(model_name: str) -> int:
    """Get optimal thread count for specific model."""
    optimizer = EPICCPUOptimizer(target_model=model_name)
    return optimizer.optimal_config['inference_threads']


def get_optimal_streams_for_model(model_name: str) -> int:
    """Get optimal stream count for specific model."""
    optimizer = EPICCPUOptimizer(target_model=model_name)
    return optimizer.optimal_config.get('streams', 1)


if __name__ == "__main__":
    # Test the optimizer
    print("=== CPU Performance Optimizer Test ===")
    
    # Test different models
    test_models = ['openpose', 'efficienthrnet1', 'higherhrnet']
    
    for model in test_models:
        print(f"\n--- Optimization for {model} ---")
        optimizer = EPICCPUOptimizer(target_model=model)
        
        print("Optimal configuration:")
        for key, value in optimizer.optimal_config.items():
            print(f"  {key}: {value}")
        
        batch_size = optimizer.get_recommended_batch_size(model, (512, 512))
        print(f"Recommended batch size: {batch_size}")
