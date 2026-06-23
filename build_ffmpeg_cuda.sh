#!/bin/bash
# Build FFmpeg with CUDA/NPP/NVENC support from source
# This script builds FFmpeg with hardware acceleration for your HPE pipeline

set -e

# Configuration
FFMPEG_VERSION="8.0"
BUILD_DIR="$HOME/ffmpeg_build"
INSTALL_PREFIX="/usr/local"
CUDA_HOME="/usr/local/cuda-12.2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building FFmpeg with CUDA/NPP/NVENC support${NC}"
echo -e "${YELLOW}FFmpeg Version: ${FFMPEG_VERSION}${NC}"
echo -e "${YELLOW}Build Directory: ${BUILD_DIR}${NC}"
echo -e "${YELLOW}Install Prefix: ${INSTALL_PREFIX}${NC}"

# Create build directory in user home
echo -e "${GREEN}📁 Creating build directory in user home: ${BUILD_DIR}${NC}"
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR}

# Install build dependencies (matching your requirements)
echo -e "${GREEN}📦 Installing build dependencies...${NC}"
sudo apt update
sudo apt install -y \
    build-essential \
    yasm \
    cmake \
    libtool \
    libc6 \
    libc6-dev \
    unzip \
    wget \
    libnuma1 \
    libnuma-dev \
    pkg-config \
    git \
    curl \
    nasm \
    autoconf \
    automake \
    make \
    gcc \
    g++ \
    ccache \
    zlib1g-dev \
    libssl-dev \
    libxml2-dev \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libopus-dev \
    libfdk-aac-dev \
    libmp3lame-dev \
    libass-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libfribidi-dev

# Detect CUDA installation
echo -e "${GREEN}🔍 Detecting CUDA installation...${NC}"
echo -e "${YELLOW}Driver supports CUDA 12.8, looking for compatible toolkit...${NC}"

# Check for CUDA 12.x installations first
if [ -d "/usr/local/cuda-12.8" ]; then
    CUDA_HOME="/usr/local/cuda-12.8"
    echo -e "${GREEN}✅ Found CUDA 12.8 at: ${CUDA_HOME}${NC}"
elif [ -d "/usr/local/cuda-12.2" ]; then
    CUDA_HOME="/usr/local/cuda-12.2"
    echo -e "${GREEN}✅ Found CUDA 12.2 at: ${CUDA_HOME}${NC}"
elif [ -d "/usr/local/cuda" ]; then
    CUDA_HOME="/usr/local/cuda"
    echo -e "${GREEN}✅ Found CUDA at: ${CUDA_HOME}${NC}"
elif command -v nvcc &> /dev/null; then
    # nvcc is in PATH, find its location
    NVCC_PATH=$(which nvcc)
    CUDA_HOME=$(dirname $(dirname $NVCC_PATH))
    echo -e "${GREEN}✅ Found nvcc at: ${NVCC_PATH}${NC}"
    echo -e "${GREEN}✅ CUDA home: ${CUDA_HOME}${NC}"
else
    echo -e "${RED}❌ CUDA toolkit not found!${NC}"
    echo -e "${YELLOW}Your driver supports CUDA 12.8, but no toolkit found.${NC}"
    echo -e "${YELLOW}Please install CUDA toolkit 12.2 or later.${NC}"
    echo -e "${YELLOW}You can install it with: sudo apt install nvidia-cuda-toolkit${NC}"
    exit 1
fi

# Verify nvcc is available
if ! command -v nvcc &> /dev/null; then
    echo -e "${YELLOW}⚠️  nvcc not in PATH, adding CUDA to PATH...${NC}"
    export PATH="${CUDA_HOME}/bin:${PATH}"
    export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"
fi

# Verify nvcc is now available
if ! command -v nvcc &> /dev/null; then
    echo -e "${RED}❌ nvcc still not found! Please check CUDA installation.${NC}"
    echo -e "${YELLOW}Trying to find nvcc in: ${CUDA_HOME}/bin/nvcc${NC}"
    if [ -f "${CUDA_HOME}/bin/nvcc" ]; then
        echo -e "${GREEN}✅ Found nvcc at: ${CUDA_HOME}/bin/nvcc${NC}"
        export PATH="${CUDA_HOME}/bin:${PATH}"
    else
        echo -e "${RED}❌ nvcc not found at expected location!${NC}"
        exit 1
    fi
fi

# Set compiler environment
export CC="ccache gcc"
export CXX="ccache g++"
export CUDAHOSTCXX="ccache g++"

# Test nvcc
echo -e "${GREEN}🧪 Testing nvcc...${NC}"
nvcc --version | head -3

# Check CUDA version compatibility
CUDA_VERSION=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]\+\.[0-9]\+\).*/\1/')
echo -e "${YELLOW}📊 CUDA Toolkit Version: ${CUDA_VERSION}${NC}"
echo -e "${YELLOW}📊 Driver supports: CUDA 12.8${NC}"

if [[ "$CUDA_VERSION" < "12.0" ]]; then
    echo -e "${YELLOW}⚠️  Using older CUDA toolkit (${CUDA_VERSION}) with newer driver (12.8)${NC}"
    echo -e "${YELLOW}💡 For optimal performance, consider upgrading to CUDA 12.2+${NC}"
    echo -e "${YELLOW}💡 This will enable compute capability 8.6 for your RTX A4000${NC}"
fi

# Download and build nv-codec-headers (using the correct repository)
echo -e "${GREEN}🔧 Building nv-codec-headers...${NC}"
if [ ! -d "nv-codec-headers" ]; then
    git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
fi
cd nv-codec-headers
sudo make install
cd ..

# Download FFmpeg source (using git as you specified)
echo -e "${GREEN}📥 Cloning FFmpeg source to user directory...${NC}"
if [ ! -d "ffmpeg" ]; then
    git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg/
    echo -e "${GREEN}✅ FFmpeg source cloned to: ${BUILD_DIR}/ffmpeg${NC}"
else
    echo -e "${YELLOW}⚠️  FFmpeg directory already exists, updating...${NC}"
    cd ffmpeg
    git pull
    cd ..
fi
cd ffmpeg

# Configure FFmpeg with CUDA support (matching your Docker configuration)
echo -e "${GREEN}⚙️  Configuring FFmpeg with CUDA support...${NC}"
PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:${CUDA_HOME}/lib64/pkgconfig" \
CC=gcc CXX=g++ \
./configure \
    --enable-nonfree \
    --enable-gpl \
    --enable-shared \
    --disable-static \
    --enable-cuda-nvcc \
    --enable-nvdec \
    --enable-nvenc \
    --enable-libnpp \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvpx \
    --enable-libopus \
    --enable-openssl \
    --extra-cflags="-I${INSTALL_PREFIX}/include -I${CUDA_HOME}/include -fPIC" \
    --extra-ldflags="-L${CUDA_HOME}/lib64 -L${CUDA_HOME}/lib64/stubs" \
    --nvccflags="-gencode=arch=compute_86,code=sm_86" \
    --extra-libs="-lcuda" \
    --enable-hardcoded-tables \
    --enable-optimizations \
    --disable-debug \
    --disable-doc \
    --disable-ffplay

# Build FFmpeg (using your specified make command)
echo -e "${GREEN}🔨 Building FFmpeg in user directory (this may take a while)...${NC}"
echo -e "${YELLOW}Building in: $(pwd)${NC}"
make -j8

# Install FFmpeg
echo -e "${GREEN}📦 Installing FFmpeg to system...${NC}"
sudo make install
sudo ldconfig

# Keep source code in user directory
echo -e "${GREEN}✅ FFmpeg source code preserved in: ${BUILD_DIR}/ffmpeg${NC}"
echo -e "${YELLOW}You can rebuild anytime by running 'make -j8' in the ffmpeg directory${NC}"

# Verify installation
echo -e "${GREEN}✅ Verifying FFmpeg installation...${NC}"
${INSTALL_PREFIX}/bin/ffmpeg -version | head -5

echo -e "${GREEN}🎉 FFmpeg with CUDA/NPP/NVENC support installed successfully!${NC}"
echo -e "${YELLOW}FFmpeg location: ${INSTALL_PREFIX}/bin/ffmpeg${NC}"
echo -e "${YELLOW}CUDA support: $(ffmpeg -hwaccels 2>/dev/null | grep -i cuda || echo 'Not detected')${NC}"
echo -e "${YELLOW}NVENC support: $(ffmpeg -encoders 2>/dev/null | grep -i nvenc || echo 'Not detected')${NC}"

# Test MJPEG encoding (required for your pipeline)
echo -e "${GREEN}🧪 Testing MJPEG encoding...${NC}"
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is available and ready for your pipeline!"
    echo "MJPEG support: $(ffmpeg -encoders 2>/dev/null | grep -i mjpeg || echo 'Not detected')"
else
    echo -e "${RED}❌ FFmpeg installation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 Your FFmpeg build is ready for the HPE pipeline!${NC}"
