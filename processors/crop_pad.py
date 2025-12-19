"""
Crop, pad, and letterbox for aspect ratio adjustment
"""

import cv2
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class AspectAdjuster:
    """Adjust video aspect ratio using crop, pad, or letterbox"""

    def __init__(self):
        self.aspect_ratios = {
            "16:9": 16/9,
            "9:16": 9/16,
            "1:1": 1.0,
            "4:3": 4/3
        }

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Adjust aspect ratio of video frames

        Args:
            frames: List of video frames
            options: Processing options
                - target_aspect: "16:9", "9:16", "1:1", "4:3" (default: "16:9")
                - method: "crop", "pad", "letterbox" (default: "letterbox")

        Returns:
            Adjusted frames
        """
        if not frames:
            return frames

        options = options or {}
        target_aspect = options.get('target_aspect', '16:9')
        method = options.get('method', 'letterbox')

        if target_aspect not in self.aspect_ratios:
            logger.warning(f"Unknown aspect ratio {target_aspect}, using 16:9")
            target_aspect = "16:9"

        target_ratio = self.aspect_ratios[target_aspect]

        adjusted_frames = []

        for frame in frames:
            adjusted = self._adjust_frame_aspect(frame, target_ratio, method)
            adjusted_frames.append(adjusted)

        return adjusted_frames

    def _adjust_frame_aspect(self, frame: np.ndarray, target_ratio: float, method: str) -> np.ndarray:
        """Adjust single frame aspect ratio"""
        h, w = frame.shape[:2]
        current_ratio = w / h

        if method == "crop":
            return self._crop_to_aspect(frame, target_ratio)
        elif method == "pad" or method == "letterbox":
            return self._letterbox_to_aspect(frame, target_ratio)
        else:
            logger.warning(f"Unknown method {method}, using letterbox")
            return self._letterbox_to_aspect(frame, target_ratio)

    def _crop_to_aspect(self, frame: np.ndarray, target_ratio: float) -> np.ndarray:
        """Crop frame to target aspect ratio (center crop)"""
        h, w = frame.shape[:2]
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Too wide, crop width
            new_w = int(h * target_ratio)
            x_offset = (w - new_w) // 2
            cropped = frame[:, x_offset:x_offset + new_w]
        else:
            # Too tall, crop height
            new_h = int(w / target_ratio)
            y_offset = (h - new_h) // 2
            cropped = frame[y_offset:y_offset + new_h, :]

        return cropped

    def _letterbox_to_aspect(self, frame: np.ndarray, target_ratio: float) -> np.ndarray:
        """Add black bars to match target aspect ratio"""
        h, w = frame.shape[:2]
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Add bars top/bottom (pillarbox)
            new_h = int(w / target_ratio)
            pad = (new_h - h) // 2
            letterboxed = cv2.copyMakeBorder(
                frame, pad, pad, 0, 0,
                cv2.BORDER_CONSTANT, value=[0, 0, 0]
            )
        else:
            # Add bars left/right (letterbox)
            new_w = int(h * target_ratio)
            pad = (new_w - w) // 2
            letterboxed = cv2.copyMakeBorder(
                frame, 0, 0, pad, pad,
                cv2.BORDER_CONSTANT, value=[0, 0, 0]
            )

        return letterboxed