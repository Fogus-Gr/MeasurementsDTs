#!/bin/bash
set -e

export CPLUS_INCLUDE_PATH=$(python3 -c "import numpy; print(numpy.get_include())")

# Set GCC 9 for building
export CC=gcc-9
export CXX=g++-9

echo "🛠️  Using compiler: $CC / $CXX"

echo "🛠️  Building roi_align..."
cd models/AlphaPose/alphapose/utils/roi_align
python3 setup.py build_ext --inplace

echo "🛠️  Building deformable conv/pool (DCN)..."
cd ../../models/layers/dcn
python3 setup.py build_ext --inplace

echo "🛠️  Building NMS..."
cd ../../../../detector/nms
python3 setup.py build_ext --inplace

echo "✅ All extensions built successfully!"
