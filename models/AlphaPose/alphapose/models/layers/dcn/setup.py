# models/AlphaPose/alphapose/models/layers/dcn/setup.py

from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension

setup(
    name='dcn_cuda',
    ext_modules=[
        CUDAExtension(
            name='deform_conv_cuda',
            sources=[
                'src/deform_conv_cuda.cpp',
                'src/deform_conv_cuda_kernel.cu'
            ]
        ),
        CUDAExtension(
            name='deform_pool_cuda',
            sources=[
                'src/deform_pool_cuda.cpp',
                'src/deform_pool_cuda_kernel.cu'
            ]
        )
    ],
    cmdclass={
        'build_ext': BuildExtension
    }
)

