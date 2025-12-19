"""
Inpainting-based watermark and caption removal
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

from .utils import create_mask, auto_detect_watermark, temporal_blend, get_neighbor_frames

logger = logging.getLogger(__name__)

class BaseInpainter:
    """Base class for inpainting processors"""

    def __init__(self):
        self.inpaint_radius = 3
        self.inpaint_method = cv2.INPAINT_TELEA

    def process_frame(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Process single frame with inpainting"""
        return cv2.inpaint(frame, mask, self.inpaint_radius, self.inpaint_method)

    def get_bbox(self, frame: np.ndarray, options: Dict) -> Optional[Tuple[int, int, int, int]]:
        """Get bounding box for inpainting"""
        if options.get('manual_bbox'):
            return tuple(options['manual_bbox'])  # [x, y, w, h]

        # Auto-detect
        return auto_detect_watermark(frame)

class WatermarkRemover(BaseInpainter):
    """Remove moving watermarks using dynamic inpainting + temporal blending"""

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Remove watermarks from video frames

        Args:
            frames: List of video frames
            options: Processing options
                - manual_bbox: [x, y, w, h] for manual selection
                - temporal_blend_frames: Number of frames for temporal blending (default: 5)

        Returns:
            Processed frames
        """
        if not frames:
            return frames

        options = options or {}
        n_frames = options.get('temporal_blend_frames', 5)

        processed_frames = []

        for i, frame in enumerate(frames):
            bbox = self.get_bbox(frame, options)

            if bbox is None:
                # No watermark detected, keep frame as-is
                processed_frames.append(frame)
                continue

            # Create mask
            mask = create_mask(frame, bbox)

            # Inpaint current frame
            inpainted = self.process_frame(frame, mask)

            # Temporal blending if enabled and enough neighbors
            if n_frames > 0 and len(frames) > n_frames:
                neighbors = get_neighbor_frames(frames, i, n_frames // 2)
                if neighbors:
                    inpainted = temporal_blend(inpainted, neighbors, bbox)

            processed_frames.append(inpainted)

        return processed_frames

class CaptionRemover(BaseInpainter):
    """Remove text captions/overlays"""

    def __init__(self):
        super().__init__()
        # Captions often need different settings
        self.inpaint_radius = 2  # Smaller radius for text
        self.inpaint_method = cv2.INPAINT_NS  # Navier-Stokes often better for text

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Remove captions from video frames

        Args:
            frames: List of video frames
            options: Processing options
                - manual_bbox: [x, y, w, h] for manual selection
                - variable_size: Whether captions change size (default: True)

        Returns:
            Processed frames
        """
        if not frames:
            return frames

        options = options or {}
        variable_size = options.get('variable_size', True)

        processed_frames = []

        for frame in frames:
            bbox = self.get_bbox(frame, options)

            if bbox is None:
                # No caption detected
                processed_frames.append(frame)
                continue

            # For variable size captions, we might need to detect per frame
            if variable_size:
                bbox = auto_detect_watermark(frame)  # Re-detect for each frame

            if bbox:
                mask = create_mask(frame, bbox)
                inpainted = self.process_frame(frame, mask)
                processed_frames.append(inpainted)
            else:
                processed_frames.append(frame)

        return processed_frames