# models/AlphaPose/detector/nms/setup.py

from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension, CppExtension

setup(
    name='nms_extensions',
    ext_modules=[
        CUDAExtension(
            name='nms_cuda',
            sources=[
                'src/nms_cuda.cpp',
                'src/nms_kernel.cu'
            ]
        ),
        CppExtension(
            name='nms_cpu',
            sources=[
                'src/nms_cpu.cpp'
            ]
        ),
        CppExtension(
            name='soft_nms_cpu',
            sources=[
                'src/soft_nms_cpu.cpp'
            ]
        )
    ],
    cmdclass={
        'build_ext': BuildExtension
    }
)

