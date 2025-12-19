"""
Video resolution upscaling
"""

import cv2
import numpy as np
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class VideoUpscaler:
    """Upscale video resolution using interpolation or DNN models"""

    def __init__(self):
        self.resolutions = {
            "720p": (1280, 720),
            "1080p": (1920, 1080)
        }

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Upscale video frames

        Args:
            frames: List of video frames
            options: Processing options
                - target_resolution: "720p" or "1080p" (default: "1080p")
                - method: "bicubic" or "dnn" (default: "bicubic")

        Returns:
            Upscaled frames
        """
        if not frames:
            return frames

        options = options or {}
        target_res = options.get('target_resolution', '1080p')
        method = options.get('method', 'bicubic')

        if target_res not in self.resolutions:
            logger.warning(f"Unknown resolution {target_res}, using 1080p")
            target_res = "1080p"

        target_w, target_h = self.resolutions[target_res]

        upscaled_frames = []

        for frame in frames:
            current_h, current_w = frame.shape[:2]

            # Skip if already at target resolution or larger
            if current_w >= target_w and current_h >= target_h:
                upscaled_frames.append(frame)
                continue

            if method == "bicubic":
                # Bicubic interpolation
                upscaled = cv2.resize(frame, (target_w, target_h),
                                    interpolation=cv2.INTER_CUBIC)
            elif method == "dnn":
                # DNN-based upscaling (if available)
                upscaled = self._dnn_upscale(frame, target_w, target_h)
            else:
                # Default to bicubic
                upscaled = cv2.resize(frame, (target_w, target_h),
                                    interpolation=cv2.INTER_CUBIC)

            upscaled_frames.append(upscaled)

        return upscaled_frames

    def _dnn_upscale(self, frame: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """DNN-based upscaling using OpenCV's DNN super resolution"""
        try:
            # Try to use OpenCV DNN super resolution
            sr = cv2.dnn_superres.DnnSuperResImpl_create()

            # Use ESPCN model (efficient sub-pixel convolutional neural network)
            # Note: This requires model files to be present
            model_path = "models/ESPCN_x2.pb"  # 2x upscaling model

            if not os.path.exists(model_path):
                logger.warning("DNN model not found, falling back to bicubic")
                return cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

            sr.readModel(model_path)
            sr.setModel("espcn", 2)  # 2x scale factor

            # Upscale
            upscaled = sr.upsample(frame)

            # Resize to exact target dimensions if needed
            current_h, current_w = upscaled.shape[:2]
            if current_w != target_w or current_h != target_h:
                upscaled = cv2.resize(upscaled, (target_w, target_h))

            return upscaled

        except Exception as e:
            logger.warning(f"DNN upscaling failed: {e}, falling back to bicubic")
            return cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)