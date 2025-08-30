from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import os

extensions = [
    Extension(
        "models.AlphaPose.detector.nms.soft_nms_cpu",
        ["models/AlphaPose/detector/nms/src/soft_nms_cpu.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=["-O3"]  # Optimizations
    )
]

if os.path.exists("models/AlphaPose/detector/nms/src/nms_kernel.cu"):
    extensions.append(
        Extension(
            "models.AlphaPose.detector.nms.nms_cuda",
            sources=[
                "models/AlphaPose/detector/nms/src/nms_kernel.cu",
                "models/AlphaPose/detector/nms/src/nms_cuda.pyx"  # Would need to be created
            ],
            library_dirs=['/usr/local/cuda/lib64'],
            libraries=['cudart'],
            extra_compile_args={
                'gcc': ['-O3'],
                'nvcc': ['-O3', '--ptxas-options=-v']
            }
        )
    )

setup(
    name="alphapose_custom",
    ext_modules=cythonize(extensions),
    script_args=["build_ext"],
    options={"build_ext": {"inplace": True}}
)