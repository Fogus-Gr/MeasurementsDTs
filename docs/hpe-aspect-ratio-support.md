# HPE Model Aspect Ratio Support

This document summarizes supported aspect ratio behavior for the HPE models in this codebase.

## Overview

Each HPE method has its own preprocessing path and input handling. Some models accept arbitrary input aspect ratios by resizing and padding, while others are tied to a specific aspect ratio shape and may fail for portrait-oriented video.

## Supported aspect ratios by model

Model | Supported input aspect ratio | Notes
---|---|---
`openpose` | Limited / landscape-oriented only in current pipeline | The OpenVINO OpenPose wrapper reshapes the model based on input aspect ratio and currently raises a hard error for portrait inputs such as `1080x1920`.
`ae1`, `ae2`, `ae3` (`EfficientHRNet`) | Broad / any ratio | Uses keep-aspect-ratio resizing and padding, so portrait and landscape inputs are supported.
`higherhrnet` | Broad / any ratio | Same general support as EfficientHRNet, with optional center padding to preserve image alignment.
`movenet` | Broad / any ratio | Uses square `256x256` input via padding, so all input aspect ratios are accepted.
`alphapose` | Broad / any ratio | Uses original image resolution preprocessing and does not depend on the same fixed input aspect ratio constraints.

## Current issue

- The only failing case in the current codebase is `openpose` when the input video is portrait (taller than wide).
- `1920x1080` is not the issue; landscape 16:9 should work normally.
- The portrait failure is caused by the OpenPose wrapper in `models/OpenVINO/model_api/models/open_pose.py`, which enforces an aspect-ratio compatibility check during preprocessing.

## Recommended fix area

If this issue is addressed, the fix should be applied in the OpenPose preprocessing path rather than the evaluator or CLI layers.
