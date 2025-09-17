#!/bin/bash
# Upgrade CUDA from 10.1 to 12.2 for RTX A4000 optimization
# This script safely removes old CUDA and installs the latest

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Upgrading CUDA from 10.1 to 12.2 for RTX A4000${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Don't run this script as root! Run as regular user.${NC}"
    exit 1
fi

# Check current CUDA installation
echo -e "${GREEN}🔍 Checking current CUDA installation...${NC}"
if command -v nvcc &> /dev/null; then
    CURRENT_VERSION=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]\+\.[0-9]\+\).*/\1/')
    echo -e "${YELLOW}Current CUDA version: ${CURRENT_VERSION}${NC}"
else
    echo -e "${YELLOW}No CUDA toolkit found${NC}"
fi

# Check NVIDIA driver
echo -e "${GREEN}🔍 Checking NVIDIA driver...${NC}"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader,nounits
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)
    echo -e "${GREEN}✅ Driver version: ${DRIVER_VERSION}${NC}"
else
    echo -e "${RED}❌ NVIDIA driver not found!${NC}"
    exit 1
fi

# Confirm upgrade
echo -e "${YELLOW}⚠️  This will remove CUDA 10.1 and install CUDA 12.2${NC}"
echo -e "${YELLOW}⚠️  This may take 30-60 minutes${NC}"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Upgrade cancelled${NC}"
    exit 1
fi

# Step 1: Remove old CUDA packages
echo -e "${GREEN}🗑️  Removing old CUDA packages...${NC}"
sudo apt remove --purge -y \
    cuda-toolkit-12-1-config-common \
    cuda-toolkit-12-config-common \
    cuda-toolkit-config-common \
    cuda-visual-tools-12-1 \
    nvidia-cuda-dev \
    nvidia-cuda-doc \
    nvidia-cuda-gdb \
    nvidia-cuda-toolkit \
    libcudart10.1:amd64

# Remove old CUDA directories
echo -e "${GREEN}🗑️  Cleaning up old CUDA directories...${NC}"
sudo rm -rf /usr/local/cuda*
sudo rm -rf /var/cuda-repo-*

# Clean up package cache
sudo apt autoremove -y
sudo apt autoclean

# Step 2: Add NVIDIA CUDA repository
echo -e "${GREEN}📦 Adding NVIDIA CUDA 12.2 repository...${NC}"

# Import NVIDIA GPG key
curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-drivers.gpg

# Add CUDA repository
echo 'deb [signed-by=/usr/share/keyrings/nvidia-drivers.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /' | sudo tee /etc/apt/sources.list.d/nvidia-drivers.list

# Update package list
sudo apt update

# Step 3: Install CUDA 12.2
echo -e "${GREEN}📦 Installing CUDA 12.2 toolkit...${NC}"
sudo apt install -y cuda-12-2

# Step 4: Set up environment
echo -e "${GREEN}⚙️  Setting up CUDA environment...${NC}"

# Add CUDA to PATH in .bashrc
if ! grep -q "CUDA_HOME" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# CUDA 12.2" >> ~/.bashrc
    echo "export CUDA_HOME=/usr/local/cuda" >> ~/.bashrc
    echo "export PATH=\$CUDA_HOME/bin:\$PATH" >> ~/.bashrc
    echo "export LD_LIBRARY_PATH=\$CUDA_HOME/lib64:\$LD_LIBRARY_PATH" >> ~/.bashrc
fi

# Source the environment
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# Step 5: Verify installation
echo -e "${GREEN}✅ Verifying CUDA 12.2 installation...${NC}"
if command -v nvcc &> /dev/null; then
    NEW_VERSION=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]\+\.[0-9]\+\).*/\1/')
    echo -e "${GREEN}✅ CUDA version: ${NEW_VERSION}${NC}"
    
    # Test compilation
    echo -e "${GREEN}🧪 Testing CUDA compilation...${NC}"
    cat > /tmp/test_cuda.cu << 'EOF'
#include <cuda_runtime.h>
#include <stdio.h>

int main() {
    int deviceCount;
    cudaGetDeviceCount(&deviceCount);
    printf("CUDA devices: %d\n", deviceCount);
    
    for (int i = 0; i < deviceCount; i++) {
        cudaDeviceProp prop;
        cudaGetDeviceProperties(&prop, i);
        printf("Device %d: %s (Compute %d.%d)\n", i, prop.name, prop.major, prop.minor);
    }
    return 0;
}
EOF
    
    nvcc /tmp/test_cuda.cu -o /tmp/test_cuda
    /tmp/test_cuda
    rm /tmp/test_cuda.cu /tmp/test_cuda
    
    echo -e "${GREEN}🎉 CUDA 12.2 installation successful!${NC}"
    echo -e "${YELLOW}💡 Please restart your terminal or run: source ~/.bashrc${NC}"
    echo -e "${YELLOW}💡 Now you can build FFmpeg with compute capability 8.6!${NC}"
    
else
    echo -e "${RED}❌ CUDA installation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 CUDA upgrade complete! Ready for optimal RTX A4000 performance!${NC}"
