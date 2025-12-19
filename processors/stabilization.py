"""
Video stabilization using optical flow
"""

import cv2
import numpy as np
from typing import List, Dict
import logging

from .utils import smooth_curve

logger = logging.getLogger(__name__)

class VideoStabilizer:
    """Stabilize shaky video using optical flow motion estimation"""

    def __init__(self):
        self.max_corners = 200
        self.quality_level = 0.01
        self.min_distance = 30
        self.block_size = 7

    def process(self, frames: List[np.ndarray], options: Dict = None) -> List[np.ndarray]:
        """
        Stabilize video frames

        Args:
            frames: List of video frames
            options: Processing options
                - smoothness: Stabilization strength (0.0-1.0, default: 0.5)

        Returns:
            Stabilized frames
        """
        if len(frames) < 2:
            return frames

        options = options or {}
        smoothness = options.get('smoothness', 0.5)

        # Convert first frame to grayscale
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

        # Calculate transforms between consecutive frames
        transforms = []

        for frame in frames[1:]:
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect good features to track
            prev_pts = cv2.goodFeaturesToTrack(
                prev_gray,
                maxCorners=self.max_corners,
                qualityLevel=self.quality_level,
                minDistance=self.min_distance,
                blockSize=self.block_size
            )

            if prev_pts is None or len(prev_pts) < 4:
                # Not enough points, skip stabilization for this frame
                transforms.append(np.eye(2, 3, dtype=np.float32))
                prev_gray = curr_gray
                continue

            # Calculate optical flow
            curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, prev_pts, None
            )

            # Filter valid points
            idx = np.where(status == 1)[0]
            if len(idx) < 4:
                transforms.append(np.eye(2, 3, dtype=np.float32))
                prev_gray = curr_gray
                continue

            prev_pts = prev_pts[idx]
            curr_pts = curr_pts[idx]

            # Estimate affine transform
            transform = cv2.estimateAffinePartial2D(prev_pts, curr_pts)[0]

            if transform is not None:
                transforms.append(transform)
            else:
                transforms.append(np.eye(2, 3, dtype=np.float32))

            prev_gray = curr_gray

        # Calculate trajectory
        trajectory = [np.eye(2, 3, dtype=np.float32)]  # First frame has no transform
        for transform in transforms:
            trajectory.append(trajectory[-1] @ transform)

        # Convert to cumulative transforms
        trajectory = np.array(trajectory)

        # Smooth trajectory
        smoothed_trajectory = []
        for i in range(trajectory.shape[1]):
            for j in range(trajectory.shape[2]):
                smoothed = smooth_curve(trajectory[:, i, j], smoothness)
                if len(smoothed_trajectory) <= i:
                    smoothed_trajectory.append([])
                if len(smoothed_trajectory[i]) <= j:
                    smoothed_trajectory[i].append([])
                smoothed_trajectory[i][j] = smoothed

        smoothed_trajectory = np.array(smoothed_trajectory).transpose(2, 0, 1)

        # Apply smoothed transforms
        stabilized_frames = [frames[0]]  # First frame unchanged

        for i, frame in enumerate(frames[1:]):
            # Calculate the transform to apply (smoothed - original)
            original_transform = trajectory[i + 1]
            smoothed_transform = smoothed_trajectory[i + 1]

            # The correction transform
            correction = smoothed_transform @ np.linalg.inv(original_transform)

            # Apply transform
            height, width = frame.shape[:2]
            stabilized = cv2.warpAffine(
                frame, correction,
                (width, height),
                borderMode=cv2.BORDER_REFLECT
            )

            stabilized_frames.append(stabilized)

        return stabilized_frames