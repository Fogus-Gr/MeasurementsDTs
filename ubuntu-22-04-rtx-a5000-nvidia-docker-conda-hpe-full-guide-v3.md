# NVIDIA GPU Driver + Container Toolkit + Docker Guide

This document covers the working NVIDIA driver setup first, then the NVIDIA Container Toolkit and Docker setup.

# NVIDIA GPU Driver Installation on a GPU attached - Cloud VM

Target system:

```text
Ubuntu: 22.04 LTS
GPU: NVIDIA RTX A5000
Driver type: Standard NVIDIA proprietary driver
Driver version: 595.71.05
CUDA version reported by nvidia-smi: 13.2
```

## Important Finding

The checks confirm that the driver is not the vGPU variant:

- No `nvidia-vgpu` or `nvidia-grid` packages installed.
- `modinfo` shows no vGPU or GRID strings.
- `nvidia-smi -q` shows `Product Name: NVIDIA RTX A5000`, which is standard professional GPU naming, not GRID or vGPU naming.

Therefore, the final working driver is the standard NVIDIA driver version `595.71.05`, installed via `apt` with:

```bash
nvidia-driver-595
nvidia-utils-595
```

The provider likely resolved a lower-level VM or hypervisor configuration issue, such as PCIe passthrough flags, IOMMU settings, kernel parameters, or VM device mapping. After that fix, the standard driver initialized the GPU correctly.

## Final Working State

```text
Driver type: Standard NVIDIA proprietary driver, not vGPU
Driver version: 595.71.05
CUDA version: 13.2
GPU: NVIDIA RTX A5000
```

## Verified Outputs

### Loaded NVIDIA modules

```bash
lsmod | grep nvidia
```

Example output:

```text
nvidia_uvm           1708032  0
nvidia_drm            110592  0
nvidia_modeset       1519616  1 nvidia_drm
nvidia              98811904  2 nvidia_uvm,nvidia_modeset
drm_kms_helper        315392  6 bochs,drm_vram_helper,nvidia_drm
drm                   622592  8 drm_kms_helper,bochs,drm_vram_helper,nvidia,drm_ttm_helper,nvidia_drm,ttm
```

### NVIDIA SMI

```bash
nvidia-smi
```

Example output:

```text
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 595.71.05    Driver Version: 595.71.05    CUDA Version: 13.2     |
|-------------------------------+----------------------+----------------------+
| GPU  Name         Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf   Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  RTX A5000           On    | 00000000:01:00.0 Off |                  Off |
| 30%   42C    P0     60W / 250W |    0MiB / 24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

### Installed NVIDIA driver package

```bash
dpkg -l | grep nvidia-driver
```

Example output:

```text
ii  nvidia-driver-595  595.71.05-0ubuntu0.22.04.1  amd64  NVIDIA driver metapackage
```

## Driver Installation Steps

### 1. Purge previous NVIDIA and CUDA packages

```bash
sudo apt purge 'nvidia-*' 'cuda-*'
sudo apt autoremove --purge
sudo rm -rf /var/lib/dkms/nvidia* /usr/src/nvidia*
```

### 2. Install the standard NVIDIA 595 driver

```bash
sudo apt update
sudo apt install -y nvidia-driver-595 nvidia-utils-595
```

### 3. Reboot the VM

A cold reboot from the cloud console is preferred after driver changes.

```bash
sudo reboot
```

### 4. Provider intervention, if the GPU is still not detected

If the standard driver installs correctly but this command still fails:

```bash
nvidia-smi
```

And the error is:

```text
No devices were found
```

Then the issue may be outside the guest OS. Ask the provider to check the VM or hypervisor GPU configuration, especially:

- PCIe passthrough settings.
- IOMMU configuration.
- VM GPU attachment.
- Kernel boot parameters.
- Device permissions or isolation settings.

In this case, Blue Lobster support adjusted the VM or hypervisor settings. After their fix and a final reboot, the GPU became visible with the standard NVIDIA driver.

### 5. Verify the driver

```bash
nvidia-smi
```

Expected result:

```text
The RTX A5000 should appear in the nvidia-smi output.
```

## Verification Commands for Driver Type

| What to check | Command | Expected output for standard driver |
|---|---|---|
| Driver version | `nvidia-smi --version` | `595.71.05` |
| Product name | `nvidia-smi -q | grep "Product Name"` | `NVIDIA RTX A5000`, not GRID or vGPU |
| vGPU packages | `dpkg -l | grep -i vgpu` | No output |
| NVIDIA module info | `modinfo nvidia | grep -i vgpu` | No output |
| GRID strings | `modinfo nvidia | grep -i grid` | No output |

## Final Driver Details

```text
Source: Ubuntu repository
Package: nvidia-driver-595
Utilities package: nvidia-utils-595
Version: 595.71.05
Installation method: apt
Provider role: Fixed the VM or hypervisor configuration so the standard driver could detect the GPU
```

The working driver is the standard NVIDIA 595 driver. The provider fixed the environment so the VM could expose the RTX A5000 correctly.

---

# NVIDIA Container Toolkit + Docker Setup

Target system:

```text
Ubuntu: 22.04 LTS
NVIDIA driver: installed and working
Example driver output:
NVIDIA-SMI 595.71.05
Driver Version: 595.71.05
CUDA Version: 13.2
```

This guide installs the NVIDIA Container Toolkit and Docker Engine, then configures Docker so containers can access the NVIDIA GPU.

## 1. Verify the NVIDIA driver

Run:

```bash
nvidia-smi
```

Expected result:

```text
NVIDIA-SMI should print your GPU, driver version, and CUDA version.
```

Important note:

```text
The CUDA version shown by nvidia-smi is the maximum CUDA version supported by the installed driver.
It does not mean that CUDA containers or Docker are already installed.
```

## 2. Install the NVIDIA Container Toolkit

### 2.1 Install prerequisites

```bash
sudo apt-get update && sudo apt-get install -y --no-install-recommends \
   ca-certificates \
   curl \
   gnupg2
```

### 2.2 Configure the NVIDIA production repository

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

### 2.3 Optional: enable experimental packages

Use this only if you need experimental NVIDIA Container Toolkit packages.

```bash
sudo sed -i -e '/experimental/ s/^#//g' /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

### 2.4 Update the package list

```bash
sudo apt-get update
```

### 2.5 Install the NVIDIA Container Toolkit packages

```bash
export NVIDIA_CONTAINER_TOOLKIT_VERSION=1.19.1-1

sudo apt-get install -y \
    nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}
```

## 3. Install Docker Engine

The NVIDIA Container Toolkit does not install Docker. You need a supported container engine. For a simple local setup, use Docker Engine.

### 3.1 Check if Docker is already installed

```bash
docker --version
systemctl status docker
```

If Docker is already installed and running, you can continue to section 4.

### 3.2 Install Docker prerequisites

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
```

### 3.3 Add Docker's official GPG key

```bash
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc
```

### 3.4 Add the Docker repository

```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

### 3.5 Install Docker Engine and plugins

```bash
sudo apt-get update

sudo apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

### 3.6 Enable and start Docker

```bash
sudo systemctl enable --now docker
```

### 3.7 Verify Docker

```bash
sudo docker run hello-world
```

## 4. Configure Docker to use the NVIDIA runtime

Run:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

This updates Docker's daemon configuration so Docker can use the NVIDIA Container Runtime.

## 5. Verify GPU access inside Docker

Run:

```bash
sudo docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

Expected result:

```text
nvidia-smi should run inside the container and show your GPU.
```

You can also test with an NVIDIA CUDA image:

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu22.04 nvidia-smi
```

If the command prints the GPU table, the setup works.

## 6. Optional: run Docker without sudo

Add your user to the Docker group:

```bash
sudo usermod -aG docker $USER
```

Apply the group change:

```bash
newgrp docker
```

Test without sudo:

```bash
docker run hello-world
docker run --rm --gpus all ubuntu nvidia-smi
```

Security note:

```text
Users in the docker group can control Docker on the host.
Only add trusted users.
```

## 7. Useful checks

### Check NVIDIA Container Toolkit version

```bash
nvidia-ctk --version
```

### Check Docker daemon configuration

```bash
cat /etc/docker/daemon.json
```

A working NVIDIA runtime configuration usually contains an entry for the NVIDIA runtime.

### Check Docker info

```bash
docker info | grep -i runtime
```

## 8. Common problems

### Problem: docker command not found

Docker is not installed.

Fix:

```bash
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Problem: Cannot connect to the Docker daemon

Docker is not running.

Fix:

```bash
sudo systemctl start docker
sudo systemctl status docker
```

### Problem: unknown runtime nvidia

Docker has not been configured for the NVIDIA runtime.

Fix:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Problem: GPU does not appear inside the container

Check the host driver first:

```bash
nvidia-smi
```

Then check the container runtime:

```bash
sudo docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

If the host command fails, fix the NVIDIA driver first.

If the host command works but the container command fails, reconfigure Docker:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## 9. Summary

For a fresh Ubuntu 22.04 system, the flow is:

```text
1. Install and verify NVIDIA driver
2. Install NVIDIA Container Toolkit
3. Install Docker Engine
4. Configure Docker with nvidia-ctk
5. Restart Docker
6. Test with nvidia-smi inside a container
```

The NVIDIA Container Toolkit is not Docker. It connects your installed container engine to the NVIDIA driver and GPU devices.

---

# Conda HPE Environment Setup and Validation

This section records the Python environment used for the HPE workload and the validation scripts used to confirm that PyTorch, CUDA, cuDNN, OpenCV, Matplotlib, NumPy, and torchvision CUDA ops work correctly.

## 1. System Python note

Installing Ubuntu pip is fine:

```bash
sudo apt install python3-pip
```

Do not uninstall it. It can coexist with Conda.

Use this rule:

```text
apt: system packages, drivers, Docker, build tools
conda or mamba: isolated Python environments
pip: Python packages inside an activated conda environment
```

Avoid this:

```bash
sudo pip install ...
```

## 2. Install Miniforge

Use Miniforge instead of full Anaconda for a lighter setup.

```bash
cd /tmp

curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh

bash Miniforge3-Linux-x86_64.sh
```

During the installer:

```text
Accept license: yes
Install location: press Enter for default
Initialize conda: yes
```

Reload the shell:

```bash
source ~/.bashrc
```

Verify:

```bash
conda --version
mamba --version
```

## 3. Create the HPE conda environment

The environment used was:

```bash
conda create -n hpe-perf python=3.9.13 -y
conda activate hpe-perf
```

Update pip:

```bash
python -m pip install --upgrade pip
```

Install the project requirements:

```bash
python -m pip install -r requirements.txt
```

Important note:

```text
Use pip for a normal pip-style requirements.txt.
Do not use conda install --file requirements.txt for pip-style requirement pins such as matplotlib==3.7.5.
```

## 4. Matplotlib package resolution note

The project required:

```text
matplotlib==3.7.5
```

This was not available from conda-forge for the active Linux conda setup, but it installed correctly through pip inside the conda environment.

Confirmed installed package:

```text
matplotlib 3.7.5 pypi_0 pypi
```

## 5. Verify that Python and pip come from the conda environment

Run:

```bash
which python
which pip
python -m pip --version
```

Observed output:

```text
/home/lenovo/miniforge3/envs/hpe-perf/bin/python
/home/lenovo/miniforge3/envs/hpe-perf/bin/pip
pip 25.2 from /home/lenovo/miniforge3/envs/hpe-perf/lib/python3.9/site-packages/pip (python 3.9)
```

## 6. Verify Matplotlib

Run:

```bash
python -c "import matplotlib; print(matplotlib.__version__)"
```

Observed output:

```text
3.7.5
```

## 7. Check for broken Python dependencies

Run:

```bash
python -m pip check
```

Observed output:

```text
No broken requirements found.
```

## 8. Check important package versions

Run:

```bash
conda list matplotlib
conda list | grep -E "matplotlib|numpy|opencv|torch|python "
```

Observed output:

```text
# packages in environment at /home/lenovo/miniforge3/envs/hpe-perf:
#
# Name                      Version          Build                 Channel
matplotlib                  3.7.5            pypi_0                pypi
numpy                       1.24.3           pypi_0                pypi
opencv-python               4.10.0.84        pypi_0                pypi
python                      3.9.13           h2660328_0_cpython    conda-forge
torch                       2.4.1            pypi_0                pypi
torchvision                 0.19.1           pypi_0                pypi
```

## 9. Full Python import and CUDA availability check

Run:

```bash
python - <<'PY'
import torch
import cv2
import numpy as np
import matplotlib

print("Python OK")
print("NumPy:", np.__version__)
print("OpenCV:", cv2.__version__)
print("Matplotlib:", matplotlib.__version__)
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("CUDA runtime used by PyTorch:", torch.version.cuda)
    print("GPU:", torch.cuda.get_device_name(0))
PY
```

Observed output:

```text
Python OK
NumPy: 1.24.3
OpenCV: 4.10.0
Matplotlib: 3.7.5
Torch: 2.4.1+cu121
CUDA available: True
CUDA runtime used by PyTorch: 12.1
GPU: NVIDIA RTX A5000
```

## 10. Basic CUDA tensor compute test

Run:

```bash
python - <<'PY'
import torch

x = torch.randn(1024, 1024, device="cuda")
y = torch.matmul(x, x)

print("Tensor device:", y.device)
print("Memory allocated MB:", torch.cuda.memory_allocated() / 1024 / 1024)
print("Memory reserved MB:", torch.cuda.memory_reserved() / 1024 / 1024)
PY
```

Observed output:

```text
Tensor device: cuda:0
Memory allocated MB: 16.125
Memory reserved MB: 20.0
```

This confirms that PyTorch performs real CUDA compute, not only GPU detection.

## 11. Larger GPU matrix compute test

Run:

```bash
python - <<'PY'
import torch
import time

device = "cuda"
x = torch.randn(4096, 4096, device=device)
torch.cuda.synchronize()

start = time.time()
for _ in range(50):
    y = x @ x

torch.cuda.synchronize()
end = time.time()

print("GPU compute test OK")
print("Elapsed seconds:", round(end - start, 3))
print("Max memory allocated MB:", round(torch.cuda.max_memory_allocated() / 1024 / 1024, 2))
PY
```

Observed output:

```text
GPU compute test OK
Elapsed seconds: 0.461
Max memory allocated MB: 200.12
```

## 12. cuDNN validation

Run:

```bash
python - <<'PY'
import torch

print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("Torch CUDA:", torch.version.cuda)
print("cuDNN available:", torch.backends.cudnn.is_available())
print("cuDNN version:", torch.backends.cudnn.version())
print("cuDNN enabled:", torch.backends.cudnn.enabled)
print("GPU:", torch.cuda.get_device_name(0))
PY
```

Observed output:

```text
Torch: 2.4.1+cu121
CUDA available: True
Torch CUDA: 12.1
cuDNN available: True
cuDNN version: 90100
cuDNN enabled: True
GPU: NVIDIA RTX A5000
```

Interpretation:

```text
cuDNN version 90100 means cuDNN 9.1.0.
```

## 13. Optional convolution workload test

This test is useful for HPE and CNN-style inference workloads.

Run:

```bash
python - <<'PY'
import torch
import torch.nn as nn
import time

device = "cuda"

model = nn.Sequential(
    nn.Conv2d(3, 64, 7, stride=2, padding=3),
    nn.ReLU(),
    nn.Conv2d(64, 128, 3, padding=1),
    nn.ReLU(),
).to(device)

x = torch.randn(16, 3, 720, 1280, device=device)

torch.cuda.synchronize()
start = time.time()

for _ in range(20):
    y = model(x)

torch.cuda.synchronize()
end = time.time()

print("Conv test OK")
print("Output shape:", tuple(y.shape))
print("Elapsed seconds:", round(end - start, 3))
print("Max memory allocated MB:", round(torch.cuda.max_memory_allocated() / 1024 / 1024, 2))
PY
```

Expected important output:

```text
Conv test OK
```

## 14. PyTorch and torchvision version check

Run:

```bash
python -c "import torch; import torchvision; print(torch.__version__); print(torchvision.__version__)"
```

Observed output:

```text
2.4.1+cu121
0.19.1+cu121
```

## 15. torchvision CUDA NMS validation

This confirms that torchvision's compiled CUDA extension is compatible with the installed PyTorch CUDA build.

Run:

```bash
python - <<'PY'
import torch
import torchvision

boxes = torch.tensor([[0, 0, 100, 100], [10, 10, 110, 110]], dtype=torch.float32, device="cuda")
scores = torch.tensor([0.9, 0.8], device="cuda")

keep = torchvision.ops.nms(boxes, scores, 0.5)

print("torchvision CUDA NMS OK")
print("keep:", keep)
PY
```

Observed output:

```text
torchvision CUDA NMS OK
keep: tensor([0], device='cuda:0')
```

This is important for detector pipelines because it confirms torchvision CUDA ops are working.

## 16. Final HPE Environment Status

The final validated environment is:

```text
Conda environment: hpe-perf
Python: 3.9.13
PyTorch: 2.4.1+cu121
Torchvision: 0.19.1+cu121
PyTorch CUDA runtime: 12.1
cuDNN: 9.1.0
NumPy: 1.24.3
OpenCV: 4.10.0
Matplotlib: 3.7.5
GPU: NVIDIA RTX A5000
CUDA tensor compute: working
CUDA matrix compute: working
cuDNN: working
torchvision CUDA NMS: working
```

The HPE environment is ready for AlphaPose or similar PyTorch-based HPE workloads.

---

# CUDA Toolkit 12.4 and AlphaPose Extension Build Steps

This section records the extra steps added after the Conda HPE validation. These steps fixed the `CUDA_HOME` issue and the missing `g++-9` compiler issue when building AlphaPose native extensions.

## 1. Why CUDA Toolkit 12.4 was selected

The validated PyTorch installation uses CUDA 12.1:

```text
PyTorch: 2.4.1+cu121
Torchvision: 0.19.1+cu121
PyTorch CUDA runtime: 12.1
GPU: NVIDIA RTX A5000
```

The PyTorch pip wheel (2.4.1+cu121) bundles CUDA 12.1. The system CUDA Toolkit 12.4 is
installed for compiling native extensions (e.g. AlphaPose Cython/CUDA extensions) — it is
backward compatible with PyTorch's CUDA 12.1 runtime.

Install:

```text
cuda-toolkit-12-4
```

Do not install the generic packages:

```bash
sudo apt install cuda
sudo apt install cuda-toolkit
```

Those generic packages may move the system to the latest CUDA Toolkit version, which can cause mismatch issues when compiling PyTorch CUDA extensions.

## 2. Check if CUDA Toolkit is already installed

Run:

```bash
which nvcc || true
nvcc --version || true
ls -ld /usr/local/cuda* || true
```

Expected after CUDA Toolkit 12.4 is installed:

```text
/usr/local/cuda-12.4/bin/nvcc
nvcc release 12.4
/usr/local/cuda-12.4
```

## 3. Install CUDA Toolkit 12.4

Install build tools first:

```bash
sudo apt update
sudo apt install -y build-essential gcc g++
```

Add the NVIDIA CUDA repository keyring for Ubuntu 22.04:

```bash
cd /tmp

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb

sudo dpkg -i cuda-keyring_1.1-1_all.deb

sudo apt update
```

Install only the pinned CUDA 12.4 toolkit:

```bash
sudo apt install -y cuda-toolkit-12-4
```

## 3.1 Add CUDA to system PATH and library path (~/.bashrc)

After installing the CUDA Toolkit, add the CUDA `bin` and `lib64` directories
to your system `PATH` and `LD_LIBRARY_PATH` so that `nvcc`, CUDA libraries,
and other tools are available in every shell — not just inside the conda
environment:

```bash
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

Verify:

```bash
which nvcc
nvcc --version
```

Expected:

```text
/usr/local/cuda/bin/nvcc
nvcc release 12.4
```

> **Note:** `/usr/local/cuda` is a symlink that points to the installed
> version (e.g. `/usr/local/cuda-12.4`). Using the symlink in `PATH` and
> `LD_LIBRARY_PATH` means you do not need to update `~/.bashrc` if you later
> install a different CUDA version — the symlink updates automatically.

## 4. Set CUDA_HOME inside the hpe-perf conda environment

The system-wide `PATH` and `LD_LIBRARY_PATH` from Section 3.1 ensure CUDA
binaries and libraries are available in all shells. However, `CUDA_HOME` and
`CUDA_PATH` are only needed when building PyTorch extensions (e.g. AlphaPose
Cython/CUDA extensions), so they are scoped to the conda activation script
rather than set globally:

```bash
conda activate hpe-perf

mkdir -p $CONDA_PREFIX/etc/conda/activate.d

cat > $CONDA_PREFIX/etc/conda/activate.d/cuda_home.sh <<'EOF'
export CUDA_HOME=/usr/local/cuda-12.4
export CUDA_PATH=/usr/local/cuda-12.4
export PATH=$CUDA_HOME/bin:$PATH
EOF
```

Reload the environment:

```bash
conda deactivate
conda activate hpe-perf
```

Verify:

```bash
echo $CUDA_HOME
which nvcc
nvcc --version
```

Expected:

```text
CUDA_HOME: /usr/local/cuda-12.4
nvcc: /usr/local/cuda-12.4/bin/nvcc
nvcc release 12.4
```

## 5. Confirm PyTorch still works after CUDA Toolkit install

Run:

```bash
python - <<'PY'
import os
import torch

print("CUDA_HOME:", os.environ.get("CUDA_HOME"))
print("Torch CUDA:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0))
PY
```

Expected:

```text
CUDA_HOME: /usr/local/cuda-12.4
Torch CUDA: 12.1
CUDA available: True
GPU: NVIDIA RTX A5000
```

## 6. Missing compiler issue during AlphaPose extension build

The first AlphaPose build failed with:

```text
subprocess.CalledProcessError: Command '['which', 'g++-9']' returned non-zero exit status 1.
```

The build script printed:

```text
Using compiler: gcc-9 / g++-9
```

So the script expected `gcc-9` and `g++-9`, but `g++-9` was not installed or not in `PATH`.

## 7. Recommended order for gcc-9, g++-9, ninja, CUDA_HOME, and build

Run this order:

```bash
sudo apt update
sudo apt install -y gcc-9 g++-9 ninja-build

conda activate hpe-perf
python -m pip install ninja

which gcc-9
which g++-9
which nvcc
echo $CUDA_HOME
nvcc --version

bash models/AlphaPose/build_extensions.sh
```

This fixes:

```text
g++-9 not found
ninja not found
CUDA_HOME not set
nvcc not found
```

## 8. Set GPU architecture explicitly (TORCH_CUDA_ARCH_LIST)

The build showed this warning:

```text
TORCH_CUDA_ARCH_LIST is not set, all archs for visible cards are included for compilation.
```

The RTX A5000 uses NVIDIA Ampere compute capability 8.6.

This was not a blocker — the build auto-detected the GPU and compiled for
`compute_86, sm_86`. However, setting `TORCH_CUDA_ARCH_LIST` explicitly avoids
compiling for unnecessary architectures and makes builds faster and
reproducible.

### 8.1 Set it persistently in the conda activation script

Add `TORCH_CUDA_ARCH_LIST` to the same activation script created for
`CUDA_HOME` in Section 4:

```bash
conda activate hpe-perf

cat > $CONDA_PREFIX/etc/conda/activate.d/cuda_home.sh <<'EOF'
export CUDA_HOME=/usr/local/cuda-12.4
export CUDA_PATH=/usr/local/cuda-12.4
export PATH=$CUDA_HOME/bin:$PATH
export TORCH_CUDA_ARCH_LIST="8.6"
EOF
```

Reload the environment:

```bash
conda deactivate
conda activate hpe-perf
```

Verify:

```bash
echo $TORCH_CUDA_ARCH_LIST
```

Expected:

```text
8.6
```

Now every new shell that activates the `hpe-perf` environment will have
`TORCH_CUDA_ARCH_LIST` set automatically — no need to manually `export` it
before each build.

### 8.2 Docker containers

The project's Docker images already set this permanently via `ENV` in both
Dockerfiles:

```dockerfile
# Dockerfile_base (line 65)
# Dockerfile_cpu  (line 65)
ENV TORCH_CUDA_ARCH_LIST=8.6
```

So inside Docker containers the variable is always set. The conda activation
script above covers the host-side (non-Docker) workflow.

### 8.3 Rebuild with the explicit architecture

After setting the variable, rebuild only if needed:

```bash
bash models/AlphaPose/build_extensions.sh
```

## 9. Successful AlphaPose extension build

Final build command:

```bash
bash models/AlphaPose/build_extensions.sh
```

Observed build status:

```text
Using compiler: gcc-9 / g++-9
Building roi_align...
nvcc: /usr/local/cuda-12.4/bin/nvcc
CUDA arch: compute_86, sm_86
ccbin: gcc-9
```

Successful output:

```text
copying build/lib.linux-x86_64-cpython-39/nms_cuda.cpython-39-x86_64-linux-gnu.so ->
copying build/lib.linux-x86_64-cpython-39/nms_cpu.cpython-39-x86_64-linux-gnu.so ->
copying build/lib.linux-x86_64-cpython-39/soft_nms_cpu.cpython-39-x86_64-linux-gnu.so ->
All extensions built successfully!
```

This confirms:

```text
CUDA_HOME: working
nvcc: working
gcc-9: working
g++-9: working
ninja: working
roi_align: built
nms_cuda: built
nms_cpu: built
soft_nms_cpu: built
```

## 10. Warnings seen during successful build

### Compiler bounds warning

```text
There are no g++-9 version bounds defined for CUDA version 12.4
```

This was not a blocker. The extension built successfully.

### CUDA architecture warning

```text
TORCH_CUDA_ARCH_LIST is not set
```

This was not a blocker. The build detected the visible RTX A5000 and compiled for:

```text
compute_86
sm_86
```

This warning is resolved by setting `TORCH_CUDA_ARCH_LIST="8.6"` persistently
in the conda activation script — see Section 8 above.

## 11. AlphaPose extension import check

After a successful build, run:

```bash
conda activate hpe-perf

python - <<'PY'
from alphapose.utils.roi_align import RoIAlign
print("roi_align import OK")

from detector.nms.nms_wrapper import nms
print("nms import OK")
PY
```

Expected:

```text
roi_align import OK
nms import OK
```

## 12. Final native extension build status

The final AlphaPose native extension setup is:

```text
Conda environment: hpe-perf
Python: 3.9.13
PyTorch: 2.4.1+cu121
Torchvision: 0.19.1+cu121
PyTorch CUDA runtime: 12.1
System CUDA Toolkit: 12.4
CUDA_HOME: /usr/local/cuda-12.4
nvcc: /usr/local/cuda-12.4/bin/nvcc
Compiler: gcc-9 / g++-9
GPU architecture: sm_86
GPU: NVIDIA RTX A5000
AlphaPose roi_align: built
AlphaPose nms_cuda: built
AlphaPose nms_cpu: built
AlphaPose soft_nms_cpu: built
```

The environment is ready for AlphaPose CUDA inference and further HPE benchmarking.

---

# Final AlphaPose Runtime Fixes and Successful JSON Output

This section records the final runtime fixes after the native extension build succeeded.

## 1. Extra Python dependencies needed after extension build

After the CUDA extensions were built, some runtime imports still required extra Python packages.

Install:

```bash
conda activate hpe-perf

python -m pip install easydict
python -m pip install "pycocotools==2.0.7"

python -m pip check
```

Confirmed dependency:

```text
pycocotools==2.0.7
```

## 2. OpenVINO runtime dependency

Even when running AlphaPose, `main.py` imports `movenet_hpe.py` at startup. That file imports OpenVINO:

```python
from openvino.runtime import Core
```

Because the `hpe-perf` environment uses Python 3.9.13, use OpenVINO 2024.4.0.

Install:

```bash
conda activate hpe-perf

python -m pip install "openvino==2024.4.0"
python -m pip install "openvino-dev==2024.4.0"

python -m pip check
```

Runtime-only import test:

```bash
python - <<'PY'
from openvino.runtime import Core

core = Core()
print("OpenVINO import OK")
print("Available devices:", core.available_devices)
PY
```

Observed output:

```text
OpenVINO import OK
Available devices: ['CPU']
```

`['CPU']` is expected on this RTX A5000 VM. OpenVINO does not use the NVIDIA RTX A5000. The NVIDIA GPU path is handled through PyTorch CUDA.

## 3. Note about eager imports in main.py

The current `main.py` imports all HPE backends at startup. This means:

```text
Running --method alphapose can still require OpenVINO.
Running --method movenet can still require AlphaPose dependencies.
```

A cleaner future code change is to lazy-load only the selected backend.

Example:

```python
if args.method == "movenet":
    from movenet_hpe import MoveNetHPE
    hpe = MoveNetHPE()

elif args.method == "alphapose":
    from alphapose_hpe import AlphaPoseHPE
    hpe = AlphaPoseHPE()

else:
    raise ValueError(f"Unsupported method: {args.method}")
```

## 4. YOLO detector weights error

AlphaPose loaded the pose model successfully, but failed when loading the YOLO detector model:

```text
RuntimeError: shape '[32, 3, 3, 3]' is invalid for input of size 475
```

This means the YOLO detector weights file was missing, corrupted, truncated, or not the real Darknet binary weights file.

The expected detector weights file is:

```text
models/AlphaPose/detector/yolo/data/yolov3-spp.weights
```

## 5. Check YOLO weights file

Run:

```bash
cd ~/MeasurementsDTs

ls -lh models/AlphaPose/detector/yolo/data/
file models/AlphaPose/detector/yolo/data/yolov3-spp.weights
du -h models/AlphaPose/detector/yolo/data/yolov3-spp.weights

head -c 200 models/AlphaPose/detector/yolo/data/yolov3-spp.weights | strings
```

Bad signs:

```text
version https://git-lfs.github.com/spec/v1
<html>
```

If either appears, the file is not the real weights file.

## 6. Redownload YOLOv3-SPP detector weights

Install `gdown`:

```bash
conda activate hpe-perf
python -m pip install -U gdown
```

Remove the bad file and create the expected directory:

```bash
cd ~/MeasurementsDTs

rm -f models/AlphaPose/detector/yolo/data/yolov3-spp.weights
mkdir -p models/AlphaPose/detector/yolo/data
```

Download the YOLOv3-SPP weights:

```bash
gdown "https://drive.google.com/uc?id=1D47msNOOiJKvPOXlnpyzdKA3k6E97NTC" \
  -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights
```

Verify:

```bash
ls -lh models/AlphaPose/detector/yolo/data/yolov3-spp.weights
file models/AlphaPose/detector/yolo/data/yolov3-spp.weights
head -c 200 models/AlphaPose/detector/yolo/data/yolov3-spp.weights | strings
```

The file should be a large binary file. It should not contain HTML or Git LFS text.

## 7. Run AlphaPose JSON inference

Command:

```bash
python3 main.py --method alphapose --input unit_tests/images/ --json
```

Observed runtime behavior:

```text
[INFO] Running AlphaPose on cuda:0
Loading pose model from models/AlphaPose/pretrained_models/fast_res50_256x192.pth...
Found 3 images in unit_tests/images/
Processing 1/3
```

The ResNet50 backbone download was normal:

```text
Downloading: "https://download.pytorch.org/models/resnet50-0676ba61.pth"
100% complete
```

The pose checkpoint loaded correctly:

```text
models/AlphaPose/pretrained_models/fast_res50_256x192.pth
```

## 8. Warnings seen during successful run

These warnings are not blockers:

```text
pretrained is deprecated
weights is deprecated
torch.load weights_only=False FutureWarning
```

They come from newer PyTorch and torchvision APIs. They can be cleaned up later, but they do not block inference.

## 9. Final AlphaPose JSON output summary

The successful JSON output used the standard COCO keypoint format:

```text
image_id
category_id
keypoints
score
univ_time
```

Each detection contains 17 COCO keypoints. Each keypoint is stored as:

```text
x, y, visibility
```

Final output summary:

```text
Total detections: 17
Images processed: 3
Image 0 detections: 7
Image 1 detections: 5
Image 2 detections: 5
Score range: 0.2499 to 0.8946
Average score: 0.7835
```

## 10. Final validated AlphaPose runtime status

The full AlphaPose runtime status is now:

```text
Driver: NVIDIA 595.71.05
GPU: NVIDIA RTX A5000
Conda environment: hpe-perf
Python: 3.9.13
PyTorch: 2.4.1+cu121
Torchvision: 0.19.1+cu121
PyTorch CUDA runtime: 12.1
System CUDA Toolkit: 12.4
CUDA_HOME: /usr/local/cuda-12.4
cuDNN: 9.1.0
OpenVINO: 2024.4.0
OpenVINO device: CPU
easydict: installed
pycocotools: 2.0.7
AlphaPose native extensions: built
YOLOv3-SPP detector weights: valid
Pose model: fast_res50_256x192.pth
JSON inference output: generated
```

The environment is now validated for AlphaPose CUDA inference on the RTX A5000.

