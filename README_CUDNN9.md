#How to install cuDNN for CUDA 12.1 on Ubuntu 20.04

##Download cuDNN for CUDA 12.x

Go to: NVIDIA cuDNN Download
Log in with your NVIDIA account.

Select:
Operating System: Linux
Architecture: x86_64
Version: 9.x (or latest for CUDA 12.1)
CUDA Version: 12.x
Distribution: Ubuntu20.04-x86_64

Navigate to the directory where you downloaded the .deb files and run:

##Install cuDNN

Run the following commands to install the downloaded .deb files:

```bash
sudo dpkg -i libcudnn9_*_amd64.deb
sudo dpkg -i libcudnn9-dev_*_amd64.deb
sudo dpkg -i libcudnn9-samples_*_amd64.deb

```bash
sudo ldconfig


export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH


##Verify the installation
ls /usr/local/cuda-12.1/lib64/libcudnn*










