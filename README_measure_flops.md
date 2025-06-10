The script measure_flops.sh runs your entire workload (e.g., python3 [main.py](http://_vscodecontentref_/1) --method alphapose --input video.mp4) under full Nsight Compute profiling. Nsight Compute (ncu) attaches to every kernel launch, collects detailed metrics, and this can slow down execution by 10x or more compared to normal runs.

Reasons for slowness:

Nsight Compute adds significant overhead to every CUDA kernel call.
Profiling the whole script (especially video processing or deep learning inference) can take a very long time.
--target-processes all attaches to all child processes, increasing overhead.

How to speed up profiling
Profile only a small input or a short run (e.g., a few frames or a small batch).
Profile only the performance-critical section (not the whole script).
Use ncu's --launch-skip and --launch-count to profile only a specific kernel launch.

```bash
ncu --launch-skip 10 --launch-count 1 ...
```

Start nvidia-smi in Logging Mode
Open a terminal and run the following command before you launch your Python script:

```bash
nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,utilization.memory,memory.total,memory.used,temperature.gpu,power.draw --format=csv -l 1 > gpu_log.csv





If you encounter the following error while profiling and running measure_flops.sh: 

```
==ERROR== ERR_NVGPUCTRPERM - The user does not have permission to access NVIDIA GPU Performance Counters on the target device 0. For instructions on enabling permissions and to get more information see https://developer.nvidia.com/ERR_NVGPUCTRPERM
```

# How to install cuDNN for CUDA 12.1 on Ubuntu 20.04

## Download cuDNN for CUDA 12.x

Go to: NVIDIA cuDNN Download
Log in with your NVIDIA account.

Select:
Operating System: Linux
Architecture: x86_64
Version: 9.x (or latest for CUDA 12.1)
CUDA Version: 12.x
Distribution: Ubuntu20.04-x86_64

## Navigate to the directory where you downloaded the .deb files and run:

## Install cuDNN

Run the following commands to install the downloaded .deb files:

```bash
sudo dpkg -i libcudnn9_*_amd64.deb
sudo dpkg -i libcudnn9-dev_*_amd64.deb
sudo dpkg -i libcudnn9-samples_*_amd64.deb
```

```bash
sudo ldconfig


export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH


## Verify the installation
```bash
ls /usr/local/cuda-12.1/lib64/libcudnn*


## Grant access to performance counters for all users
Run this as root:

sudo nvidia-smi -pm 1
sudo nvidia-smi -acp 0

Or, for newer drivers (NVIDIA 450+), set the permissions with:

sudo nvidia-smi --gpu-reset -i 0
sudo nvidia-smi -pm 1
sudo nvidia-smi -acp 0

Option 3: Set the kernel module parameter (persistent fix)
Add this to your /etc/modprobe.d/nvidia-perf.conf:

options nvidia NVreg_RestrictProfilingToAdminUsers=0

sudo apt-get purge nvidia-driver-* libnvidia-*
sudo apt-get autoremove
sudo apt-get clean
## Then reboot or reload the NVIDIA kernel module:

sudo update-initramfs -u
sudo reboot

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker






