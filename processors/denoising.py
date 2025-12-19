"""
Noise reduction using Non-local Means denoising
"""

import cv2
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class NoiseReducer:
    """Reduce noise and compression artifacts"""

    def __init__(self):
        self.template_window_size = 7
        self.search_window_size = 21

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Reduce noise in video frames

        Args:
            frames: List of video frames
            options: Processing options
                - strength: Denoising strength (1-30, default: 10)

        Returns:
            Denoised frames
        """
        if not frames:
            return frames

        options = options or {}
        strength = options.get('strength', 10)

        # Clamp strength to valid range
        strength = max(1, min(30, strength))

        denoised_frames = []

        for frame in frames:
            # Apply Non-local Means Denoising Colored
            clean_frame = cv2.fastNlMeansDenoisingColored(
                frame,
                None,
                h=strength,
                hColor=strength,
                templateWindowSize=self.template_window_size,
                searchWindowSize=self.search_window_size
            )

            denoised_frames.append(clean_frame)

        return denoised_frames