"""Reproduction script to run a short watermark removal job synchronously

Usage: python -m tests.reproduce_processing
"""
import asyncio
import time
import os
from pathlib import Path
import cv2

from server import process_video_task, CONFIG, generate_file_id, update_job_status, get_job_status


def create_test_video(path: str, n_frames: int = 12, size=(160, 120), fps=10):
    """Create a synthetic test video with a simple watermark rectangle"""
    width, height = size
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))

    for i in range(n_frames):
        frame = (np.zeros((height, width, 3), dtype=np.uint8) + 100).astype('uint8')
        # Draw watermark rectangle at bottom-right
        x1, y1 = width - 40, height - 20
        cv2.rectangle(frame, (x1, y1), (x1+30, y1+15), (255,255,255), -1)
        out.write(frame)

    out.release()


async def run_job(tool_name='watermark-removal'):
    temp_dir = Path(CONFIG['processing']['temp_dir'])
    temp_dir.mkdir(exist_ok=True)
    (temp_dir / 'uploads').mkdir(exist_ok=True)
    (temp_dir / 'outputs').mkdir(exist_ok=True)

    input_path = str(temp_dir / 'uploads' / 'test_input.mp4')
    output_expected_prefix = str(temp_dir / 'outputs')

    # Create test video
    # Avoid importing numpy at top-level to keep script lightweight
    import numpy as np
    create_test_video(input_path)

    job_id = generate_file_id()
    update_job_status(job_id, 'uploading')

    print(f"Starting sync job {job_id} for {tool_name} with input {input_path}")
    start = time.time()

    # Run processing synchronously
    await process_video_task(job_id, tool_name, input_path, options={})

    elapsed = time.time() - start
    print(f"Job {job_id} finished in {elapsed:.2f}s")

    status = get_job_status(job_id)
    print('Status:', status)
    if status.get('status') == 'completed':
        print('Output file:', status.get('output_path'))
    else:
        print('Processing failed. Check logs')


if __name__ == '__main__':
    asyncio.run(run_job())
