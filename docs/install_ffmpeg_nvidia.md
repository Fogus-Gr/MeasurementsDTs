# How to Compile and Install FFmpeg with NVIDIA Hardware Acceleration

This document outlines the steps to build FFmpeg from source with `cuda-nvcc` and `nvenc` enabled on a Linux host system. It follows the [NVIDIA Video Codec SDK documentation](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/ffmpeg-with-nvidia-gpu/index.html).

## Prerequisites

You need `sudo` privileges to install dependencies and system binaries.
Ensure that the CUDA toolkit is installed (usually located at `/usr/local/cuda`).

## 1. Install Build Dependencies

Install essential build tools, compilers, and libraries via `apt-get`:

```bash
sudo apt-get update
sudo apt-get install -y build-essential yasm nasm cmake libtool libc6 libc6-dev unzip wget libnuma1 libnuma-dev
```

## 2. Install NVIDIA Codec Headers

FFmpeg requires the `nv-codec-headers` repository to interface with NVIDIA hardware acceleration APIs.

```bash
cd /home/lenovo/
git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
cd nv-codec-headers
sudo make install
```

## 3. Clone FFmpeg Repository

Download the official FFmpeg source code.

```bash
cd /home/lenovo/
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg
```

## 4. Configure the Build

Configure the build process to enable CUDA (`--enable-cuda-nvcc`) and other non-free options. Ensure the `extra-cflags` and `extra-ldflags` point to your CUDA toolkit location.

```bash
./configure --enable-nonfree --enable-cuda-nvcc --enable-libnpp \
    --extra-cflags=-I/usr/local/cuda/include \
    --extra-ldflags=-L/usr/local/cuda/lib64 \
    --disable-static --enable-shared
```

## 5. Compile and Install

Compile FFmpeg utilizing multiple CPU cores (`-j 8`), then install it onto the system.

```bash
make -j 8
sudo make install
```

## 6. Verification

Verify the installation was successful and the hardware acceleration modules are available:

```bash
# Check version and enabled config flags
ffmpeg -version

# Ensure NVIDIA encoders are present
ffmpeg -encoders | grep nvenc

# Verify CUDA hardware acceleration support
ffmpeg -hwaccels | grep cuda
```
