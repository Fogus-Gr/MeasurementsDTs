FROM  openvino/ubuntu20_dev:latest
# Set the working directory
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . /app
# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libfontconfig1 \
    libice6

RUN pip3 install --no-cache-dir -r requirements.txt

# Install gdown for Google Drive downloads
RUN pip3 install --no-cache-dir gdown

# Create directories if they don't exist and download AlphaPose models
RUN mkdir -p models/AlphaPose/pretrained_models && \
    mkdir -p models/AlphaPose/detector/yolo/data && \
    gdown --id 1p6bi10UybpUIcq5D2XDsgQRLPJIr2RyI -O models/AlphaPose/pretrained_models/fast_res50_256x192.pth && \
    gdown --id 1k-9cUGcdH5ZFN1NcMvZrO0ApW241tboD -O models/AlphaPose/detector/yolo/data/yolov3-spp.weights

# Run app.py when the container launches
CMD ["python3", "main.py", "--method", "alphapose", "--input", "testImage.jpg", "--save_image"]