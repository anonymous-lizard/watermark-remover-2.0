"""
Color correction and enhancement
"""

import cv2
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ColorCorrector:
    """Enhance video colors using CLAHE and manual adjustments"""

    def __init__(self):
        self.clahe_clip_limit = 2.0
        self.clahe_grid_size = (8, 8)

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Correct colors in video frames

        Args:
            frames: List of video frames
            options: Processing options
                - auto: Use automatic CLAHE (default: True)
                - brightness: Manual brightness adjustment (-100 to 100)
                - contrast: Manual contrast adjustment (0.5 to 2.0)
                - saturation: Manual saturation adjustment (0.5 to 2.0)

        Returns:
            Color-corrected frames
        """
        if not frames:
            return frames

        options = options or {}
        auto_mode = options.get('auto', True)

        corrected_frames = []

        for frame in frames:
            if auto_mode:
                # Automatic mode: CLAHE on luminance channel
                corrected = self._apply_clahe(frame)
            else:
                # Manual adjustments
                corrected = self._apply_manual_corrections(
                    frame,
                    brightness=options.get('brightness', 0),
                    contrast=options.get('contrast', 1.0),
                    saturation=options.get('saturation', 1.0)
                )

            corrected_frames.append(corrected)

        return corrected_frames

    def _apply_clahe(self, frame: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)"""
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

        # Split channels
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=self.clahe_grid_size
        )
        l_corrected = clahe.apply(l)

        # Merge channels back
        lab_corrected = cv2.merge([l_corrected, a, b])

        # Convert back to BGR
        corrected = cv2.cvtColor(lab_corrected, cv2.COLOR_LAB2BGR)

        return corrected

    def _apply_manual_corrections(self, frame: np.ndarray,
                                brightness: float = 0,
                                contrast: float = 1.0,
                                saturation: float = 1.0) -> np.ndarray:
        """Apply manual color corrections"""
        # Clamp values to reasonable ranges
        brightness = max(-100, min(100, brightness))
        contrast = max(0.5, min(2.0, contrast))
        saturation = max(0.5, min(2.0, saturation))

        corrected = frame.astype(np.float32)

        # Brightness adjustment
        if brightness != 0:
            corrected += brightness

        # Contrast adjustment
        if contrast != 1.0:
            corrected = (corrected - 127.5) * contrast + 127.5

        # Saturation adjustment
        if saturation != 1.0:
            # Convert to HSV for saturation adjustment
            hsv = cv2.cvtColor(corrected.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            h, s, v = cv2.split(hsv)

            s *= saturation
            s = np.clip(s, 0, 255)

            hsv_corrected = cv2.merge([h, s, v])
            corrected = cv2.cvtColor(hsv_corrected.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

        # Clip to valid range and convert back
        corrected = np.clip(corrected, 0, 255).astype(np.uint8)

        return corrected