# models/AlphaPose/alphapose/utils/roi_align/setup.py

from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension

setup(
    name='roi_align_cuda',
    ext_modules=[
        CUDAExtension(
            name='roi_align_cuda',
            sources=[
                'src/roi_align_cuda.cpp',
                'src/roi_align_kernel.cu'
            ]
        )
    ],
    cmdclass={
        'build_ext': BuildExtension
    }
)

