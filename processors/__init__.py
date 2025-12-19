"""
Video processing modules
"""

from .inpainting import WatermarkRemover, CaptionRemover
from .stabilization import VideoStabilizer
from .denoising import NoiseReducer
from .color_correction import ColorCorrector
from .upscaling import VideoUpscaler
from .crop_pad import AspectAdjuster
from .utils import *

__all__ = [
    'WatermarkRemover',
    'CaptionRemover',
    'VideoStabilizer',
    'NoiseReducer',
    'ColorCorrector',
    'VideoUpscaler',
    'AspectAdjuster'
]