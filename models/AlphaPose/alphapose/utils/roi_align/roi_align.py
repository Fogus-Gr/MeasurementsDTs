# models/AlphaPose/alphapose/utils/roi_align/roi_align.py
# -----------------------------------------------------------------------------
# CPU-safe RoIAlign with automatic torchvision fallback, CUDA fast-path retained
# -----------------------------------------------------------------------------

import torch
import torch.nn as nn
from torch.autograd import Function
from torch.autograd.function import once_differentiable
from torch.nn.modules.utils import _pair

# Try torchvision's RoIAlign once (CPU-friendly, has autograd)
try:
    from torchvision.ops import roi_align as tv_roi_align
    _HAS_TV = True
except Exception:
    tv_roi_align = None
    _HAS_TV = False

# Prefer torchvision on CPU by default; keep CUDA path when actually on CUDA
_USE_TV_DEFAULT = (not torch.cuda.is_available()) and _HAS_TV

# Optional CUDA extension (only attempted on CUDA builds)
roi_align_cuda = None
if torch.cuda.is_available():
    try:
        from . import roi_align_cuda
    except ImportError:
        print("[WARNING] roi_align_cuda not found. "
              "AlphaPose CUDA extensions are not built; falling back when possible.")

# ---- Public function alias (legacy call-sites import this) -------------------

def _roi_align_tv(features, rois, out_size, spatial_scale=1.0, sample_num=0, aligned=False):
    """
    TorchVision RoIAlign wrapper mapping AlphaPose-style args:
      - out_size: int or (h, w)
      - sample_num -> sampling_ratio
      - aligned: keep default False to preserve original AlphaPose behavior
    """
    if not _HAS_TV:
        raise NotImplementedError("torchvision.ops.roi_align not available on this install.")
    return tv_roi_align(features, rois, _pair(out_size), spatial_scale, sample_num, aligned)

# Default to TV on CPU; will finalize after class defs if CUDA ext is usable
roi_align = _roi_align_tv if _USE_TV_DEFAULT else None

# ---- Custom CUDA-backed Function (kept for GPU builds with extension) --------

class RoIAlignFunction(Function):
    @staticmethod
    def forward(ctx, features, rois, out_size, spatial_scale, sample_num=0):
        out_h, out_w = _pair(out_size)
        assert isinstance(out_h, int) and isinstance(out_w, int)

        ctx.spatial_scale = float(spatial_scale)
        ctx.sample_num = int(sample_num)
        ctx.save_for_backward(rois)
        ctx.feature_size = features.size()

        if not (features.is_cuda and roi_align_cuda is not None):
            # Should not be hit if CPU is routed to torchvision above
            raise NotImplementedError(
                "RoIAlign CUDA extension not available. "
                "On CPU, install/enable torchvision and use its ROIAlign."
            )

        batch_size, num_channels, data_height, data_width = features.size()
        num_rois = rois.size(0)
        output = features.new_zeros(num_rois, num_channels, out_h, out_w)
        roi_align_cuda.forward(features, rois, out_h, out_w,
                               ctx.spatial_scale, ctx.sample_num, output)
        return output

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        # This custom backward is only valid on CUDA with the ROIAlign extension.
        if not grad_output.is_cuda or roi_align_cuda is None:
            raise NotImplementedError(
                "RoIAlign backward on CPU is not supported by the CUDA extension. "
                "On CPU, use torchvision.ops.roi_align (autograd supported)."
            )

        feature_size = ctx.feature_size
        rois, = ctx.saved_tensors
        spatial_scale = ctx.spatial_scale
        sample_num = ctx.sample_num

        batch_size, num_channels, data_height, data_width = feature_size
        out_h, out_w = grad_output.size(2), grad_output.size(3)

        grad_input = None
        if ctx.needs_input_grad[0]:
            grad_input = rois.new_zeros(batch_size, num_channels, data_height, data_width)
            roi_align_cuda.backward(
                grad_output.contiguous(), rois, out_h, out_w,
                spatial_scale, sample_num, grad_input
            )

        # grads correspond to: (features, rois, out_size, spatial_scale, sample_num)
        return grad_input, None, None, None, None

# ---- Module wrapper that chooses the right backend automatically --------------

class RoIAlign(nn.Module):
    def __init__(self,
                 out_size,
                 spatial_scale=1,
                 sample_num=0,
                 use_torchvision=None,
                 aligned=False):
        """
        Args:
            out_size: int or (h, w)
            spatial_scale: float
            sample_num: sampling_ratio for RoIAlign (int; -1/0 means adaptive)
            use_torchvision: None -> auto (TV on CPU, CUDA ext on GPU)
                              True -> force torchvision
                              False -> force CUDA Function (requires CUDA ext)
            aligned: pass-through to torchvision's 'aligned' flag (default False
                     to match historical AlphaPose numerics)
        """
        super().__init__()
        self.out_size = out_size
        self.spatial_scale = float(spatial_scale)
        self.sample_num = int(sample_num)
        self.aligned = bool(aligned)

        if use_torchvision is None:
            self.use_torchvision = _USE_TV_DEFAULT
        else:
            self.use_torchvision = bool(use_torchvision)

    def forward(self, features, rois):
        if self.use_torchvision:
            if not _HAS_TV:
                raise RuntimeError("torchvision.ops.roi_align not available. "
                                   "Install matching torchvision for your torch.")
            return tv_roi_align(features, rois, _pair(self.out_size),
                                self.spatial_scale, self.sample_num, self.aligned)
        else:
            return RoIAlignFunction.apply(features, rois, self.out_size,
                                          self.spatial_scale, self.sample_num)

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"out_size={self.out_size}, "
                f"spatial_scale={self.spatial_scale}, "
                f"sample_num={self.sample_num}, "
                f"use_torchvision={self.use_torchvision}, "
                f"aligned={self.aligned})")

# ---- Finalize legacy function alias ------------------------------------------

if roi_align is None and (torch.cuda.is_available() and roi_align_cuda is not None):
    # On CUDA with built extension: expose custom Function as the public symbol
    roi_align = RoIAlignFunction.apply

if roi_align is None:
    # Neither torchvision nor CUDA extension is usable
    def roi_align(*args, **kwargs):
        raise NotImplementedError(
            "No RoIAlign implementation available. "
            "Install torchvision (CPU) or build the CUDA extension (GPU)."
        )