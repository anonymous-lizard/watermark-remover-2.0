"""
Utility functions for video processing
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def load_video_frames(video_path: str) -> List[np.ndarray]:
    """Load all frames from video file"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

    cap.release()

    if not frames:
        raise ValueError("No frames found in video")

    return frames

def save_video_frames(frames: List[np.ndarray], output_path: str, fps: float = 30.0):
    """Save frames to video file"""
    if not frames:
        raise ValueError("No frames to save")

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        out.write(frame)

    out.release()

def get_video_properties(video_path: str) -> dict:
    """Get video properties"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    props = {
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    }

    cap.release()
    return props

def create_mask(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """Create binary mask from bounding box"""
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    x, y, w, h = bbox
    mask[y:y+h, x:x+w] = 255
    return mask

def auto_detect_watermark(frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """
    Auto-detect watermark in frame using edge detection and morphology
    This is a simplified implementation - in production, you'd use ML models
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)

    # Morphological operations to find potential overlay regions
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Find largest contour (likely the watermark)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)

    # Filter by size (watermarks are typically not too large)
    frame_area = frame.shape[0] * frame.shape[1]
    bbox_area = w * h

    if bbox_area / frame_area > 0.5:  # Too large, probably not a watermark
        return None

    if bbox_area / frame_area < 0.001:  # Too small
        return None

    return (x, y, w, h)

def temporal_blend(current_frame: np.ndarray, neighbor_frames: List[np.ndarray],
                  bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """Blend current frame region with temporal neighbors"""
    x, y, w, h = bbox

    # Collect region from all frames
    regions = []
    for frame in [current_frame] + neighbor_frames:
        region = frame[y:y+h, x:x+w]
        regions.append(region)

    # Median blend across time
    blended_region = np.median(regions, axis=0).astype(np.uint8)

    # Apply back to frame
    result = current_frame.copy()
    result[y:y+h, x:x+w] = blended_region

    return result

def get_neighbor_frames(frames: List[np.ndarray], current_idx: int,
                       n_neighbors: int) -> List[np.ndarray]:
    """Get neighboring frames for temporal processing"""
    neighbors = []
    start_idx = max(0, current_idx - n_neighbors)
    end_idx = min(len(frames), current_idx + n_neighbors + 1)

    for i in range(start_idx, end_idx):
        if i != current_idx:
            neighbors.append(frames[i])

    return neighbors[:n_neighbors * 2]  # Limit to n_neighbors on each side

def smooth_curve(points: np.ndarray, smoothness: float = 0.5) -> np.ndarray:
    """Smooth trajectory using moving average"""
    if smoothness <= 0:
        return points

    window_size = max(3, int(len(points) * smoothness))
    if window_size % 2 == 0:
        window_size += 1

    # Simple moving average
    smoothed = np.convolve(points, np.ones(window_size)/window_size, mode='same')

    return smoothed

def validate_video_file(file_path: str) -> bool:
    """Validate video file by checking if it can be opened"""
    try:
        cap = cv2.VideoCapture(file_path)
        ret = cap.isOpened()
        cap.release()
        return ret
    except:
        return False

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    from pathlib import Path
    return Path(file_path).stat().st_size / (1024 * 1024)