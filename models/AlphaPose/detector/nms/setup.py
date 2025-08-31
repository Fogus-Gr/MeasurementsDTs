# models/AlphaPose/detector/nms/setup.py

from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension, CppExtension
import torch
import numpy

ext_modules = [
    CppExtension(
        name='nms_cpu',
        sources=[
            'src/nms_cpu.cpp'
        ],
        include_dirs=[numpy.get_include()]
    ),
    CppExtension(
        name='soft_nms_cpu',
        sources=[
            'src/soft_nms_cpu.cpp'
        ],
        include_dirs=[numpy.get_include()]
    )
]

if torch.cuda.is_available():
    ext_modules.append(
        CUDAExtension(
            name='nms_cuda',
        sources=[
            'src/nms_cuda.cpp',
            'src/nms_kernel.cu'
        ],
        extra_compile_args=['-DDEBUG']
    )
    )

setup(
    name='nms_extensions',
    ext_modules=ext_modules,
    cmdclass={
        'build_ext': BuildExtension
    }
)
