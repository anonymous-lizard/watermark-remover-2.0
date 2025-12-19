"""
Sora Video Processor - Local PC Server
FastAPI backend for video processing tools
"""

import asyncio
import json
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    OPENCV_AVAILABLE = False
    print("Warning: OpenCV not available. Video processing will be disabled.")

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import math
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": False
    },
    "processing": {
        "max_file_size_mb": 500,
        "temp_dir": "./temp",
        "cleanup_hours": 24,
        "default_workers": 4
    },
    "quality": {
        "default_resolution": "1080p",
        "default_bitrate": "8M",
        "default_fps": 30
    }
}

# Global job status tracking
job_statuses: Dict[str, Dict] = {}

app = FastAPI(title="Sora Video Processor", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import processors
try:
    from processors import (
        inpainting,
        stabilization,
        upscaling,
        denoising,
        color_correction,
        crop_pad,
        utils
    )
    OPENCV_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OpenCV modules not available: {e}")
    print("Server will start but video processing will not work.")
    OPENCV_AVAILABLE = False

def get_job_status(job_id: str) -> Dict:
    """Get current job status"""
    return job_statuses.get(job_id, {"status": "not_found"})

def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status"""
    if job_id not in job_statuses:
        job_statuses[job_id] = {}

    job_statuses[job_id].update({
        "status": status,
        "updated_at": time.time(),
        **kwargs
    })

def generate_file_id() -> str:
    """Generate unique file ID"""
    timestamp = int(time.time() * 1000)
    random_part = str(uuid.uuid4())[:8]
    return f"{timestamp}_{random_part}"

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file and return file path"""
    file_id = generate_file_id()
    file_extension = Path(upload_file.filename).suffix.lower()

    # Validate file extension
    allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    upload_dir = Path(CONFIG["processing"]["temp_dir"]) / "uploads"
    upload_dir.mkdir(exist_ok=True)

    file_path = upload_dir / f"{file_id}{file_extension}"

    try:
        # Stream write to disk (don't keep entire upload in memory)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    return str(file_path)

async def cleanup_old_files():
    """Clean up files older than configured hours"""
    cutoff_time = time.time() - (CONFIG["processing"]["cleanup_hours"] * 3600)

    temp_dir = Path(CONFIG["processing"]["temp_dir"])
    for dir_path in [temp_dir / "uploads", temp_dir / "outputs"]:
        if dir_path.exists():
            for file_path in dir_path.glob("*"):
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        logger.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup {file_path}: {e}")

# Background task for processing
async def process_video_task(job_id: str, tool_name: str, input_path: str, options: Dict = None):
    """Background video processing task with streaming support"""
    try:
        update_job_status(job_id, "processing", current_frame=0, total_frames=0)

        # Load video
        if not OPENCV_AVAILABLE:
            raise Exception("Video processing not available - OpenCV not installed")

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Failed to open video file")

        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        update_job_status(job_id, "processing", total_frames=total_frames)

        # Output setup
        output_dir = Path(CONFIG["processing"]["temp_dir"]) / "outputs"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{job_id}_processed.mp4"

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        options = options or {}

        # Streaming-supported tools (process frames without loading all into memory)
        streaming_tools = {"watermark-removal", "caption-removal", "denoising", "color-correction", "upscaling", "crop-pad"}

        if tool_name in streaming_tools:
            # Instantiate processor
            if tool_name == "watermark-removal":
                processor = inpainting.WatermarkRemover()
            elif tool_name == "caption-removal":
                processor = inpainting.CaptionRemover()
            elif tool_name == "denoising":
                processor = denoising.NoiseReducer()
            elif tool_name == "color-correction":
                processor = color_correction.ColorCorrector()
            elif tool_name == "upscaling":
                processor = upscaling.VideoUpscaler()
            elif tool_name == "crop-pad":
                processor = crop_pad.AspectAdjuster()
            else:
                processor = None

            # For temporal operations (watermark/caption), maintain sliding window
            temporal_n = int(options.get('temporal_blend_frames', 5)) if tool_name in ["watermark-removal", "caption-removal"] else 0
            half = max(0, temporal_n // 2)

            from collections import deque
            window = deque()
            frame_idx = 0

            # Pre-fill window with first frames
            while len(window) < half and True:
                ret, frame = cap.read()
                if not ret:
                    break
                window.append(frame)

            # Now read and process frames one by one
            while True:
                ret, frame = cap.read()
                if ret:
                    window.append(frame)
                else:
                    # No more frames, process remaining in window
                    if not window:
                        break
                    # pad with None at the end
                    window.append(None)

                # Process center frame when we have enough context
                if len(window) >= (half + 1):
                    center_idx = half
                    center_frame = window[0] if len(window) == 1 and frame is None else window[center_idx]

                    if center_frame is None:
                        # pop and continue
                        window.popleft()
                        frame_idx += 1
                        continue

                    processed_frame = center_frame

                    # If processor supports get_bbox/process_roi use those for watermark/caption
                    if tool_name in ["watermark-removal", "caption-removal"]:
                        bbox = processor.get_bbox(center_frame, options)
                        if bbox is not None:
                            mask = create_mask(center_frame, bbox)
                            # perform ROI inpainting
                            processed_frame = processor.process_roi(center_frame, mask, bbox)

                            # temporal blending using neighbor frames in window (excluding center)
                            neighbors = []
                            # Collect neighbor frames from window excluding None and center index
                            for i, f in enumerate(list(window)):
                                if i != center_idx and f is not None:
                                    neighbors.append(f)
                            if neighbors:
                                processed_frame = temporal_blend(processed_frame, neighbors, bbox)

                    else:
                        # Per-frame processors: try to use process_frame or fall back to process([frame])[0]
                        if hasattr(processor, 'process_frame'):
                            try:
                                processed_frame = processor.process_frame(center_frame, options)  # type: ignore
                            except Exception:
                                # fallback
                                processed_frame = processor.process([center_frame], options)[0]
                        else:
                            processed_frame = processor.process([center_frame], options)[0]

                    # Write processed frame
                    out.write(processed_frame)

                    frame_idx += 1

                    # Update progress every few frames
                    if frame_idx % 5 == 0 and total_frames > 0:
                        percentage = int((frame_idx / total_frames) * 100)
                        update_job_status(job_id, "processing", current_frame=frame_idx, total_frames=total_frames, percentage=percentage)

                    # Pop left to slide window
                    window.popleft()

                # Break when we've exhausted frames and window empties
                if not ret and not window:
                    break

            cap.release()
            out.release()

            # Finalize job
            if output_path.exists():
                update_job_status(job_id, "completed", output_path=str(output_path), file_size=output_path.stat().st_size)
                logger.info(f"Processing completed for job {job_id} (streaming)")
                return
            else:
                raise Exception("Processing failed - output not written")

        # Non-streaming tools (stabilization/full-pipeline) - load all frames
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)

        cap.release()

        if not frames:
            raise Exception("No frames found in video")

        processed_frames = frames

        if tool_name == "stabilization":
            processor = stabilization.VideoStabilizer()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "full-pipeline":
            from pipeline import create_full_pipeline
            pipeline = create_full_pipeline(options or {})

            # Execute pipeline and write directly to output path
            success = pipeline.execute(input_path, str(output_path), progress_callback=lambda p, msg: update_job_status(job_id, "processing", percentage=int(p * 100)))
            if not success:
                raise Exception("Pipeline execution failed")

            update_job_status(job_id, "completed", output_path=str(output_path), file_size=output_path.stat().st_size)
            logger.info(f"Processing completed for job {job_id} (full-pipeline)")
            return

        # Write processed_frames to output
        for i, frame in enumerate(processed_frames):
            out.write(frame)
            if i % 10 == 0 and total_frames > 0:
                percentage = int((i / total_frames) * 100)
                update_job_status(job_id, "processing", current_frame=i, total_frames=total_frames, percentage=percentage)

        out.release()

        update_job_status(job_id, "completed", output_path=str(output_path), file_size=output_path.stat().st_size)
        logger.info(f"Processing completed for job {job_id}")

    except Exception as e:
        logger.error(f"Processing failed for job {job_id}: {e}")
        update_job_status(job_id, "failed", error=str(e))

# Routes

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve home page"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Sora Video Processor</h1><p>Home page not found</p>"

@app.get("/tool/{tool_name}", response_class=HTMLResponse)
async def tool_page(tool_name: str):
    """Serve tool pages"""
    tool_files = {
        "watermark-removal": "watermark-removal.html",
        "caption-removal": "caption-removal.html",
        "stabilization": "stabilization.html",
        "denoising": "denoising.html",
        "color-correction": "color-correction.html",
        "upscaling": "upscaling.html",
        "crop-pad": "crop-pad.html",
        "full-pipeline": "full-pipeline.html"
    }

    if tool_name not in tool_files:
        raise HTTPException(status_code=404, detail="Tool not found")

    try:
        with open(f"static/{tool_files[tool_name]}", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>{tool_name.replace('-', ' ').title()}</h1><p>Tool page not found</p>"

@app.post("/process/{tool_name}")
async def process_video(
    tool_name: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = None
):
    """Process video with specified tool"""
    try:
        # Validate tool
        valid_tools = [
            "watermark-removal", "caption-removal", "stabilization",
            "denoising", "color-correction", "upscaling", "crop-pad", "full-pipeline"
        ]
        if tool_name not in valid_tools:
            raise HTTPException(status_code=400, detail="Invalid tool")

        # Save uploaded file
        input_path = await save_upload_file(file)

        # Parse options
        parsed_options = {}
        if options:
            try:
                parsed_options = json.loads(options)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid options format")

        # Create job
        job_id = generate_file_id()
        # Store upload metadata so clients can preview or download the uploaded file
        update_job_status(job_id, "uploading",
                          input_path=str(input_path),
                          input_url=f"/upload/{job_id}/input",
                          filename=Path(input_path).name,
                          file_size=Path(input_path).stat().st_size)

        # Start background processing
        background_tasks.add_task(process_video_task, job_id, tool_name, input_path, parsed_options)

        return {"job_id": job_id, "status": "processing", "input_url": f"/upload/{job_id}/input"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to start processing")

@app.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """Get processing progress"""
    status = get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    return status

@app.get("/download/{job_id}")
async def download_result(job_id: str, request: Request):
    """Download processed video (supports Range requests)"""
    status = get_job_status(job_id)

    if status.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Processing not completed")

    output_path = status.get("output_path")
    if not output_path or not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return _file_response_with_range(output_path, request, filename=f"sora_processed_{job_id}.mp4")


def _file_response_with_range(file_path: str, request: Request, filename: str = None, content_type: str = 'video/mp4'):
    """Return a StreamingResponse that supports HTTP Range requests for efficient seeking"""
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = path.stat().st_size
    range_header = request.headers.get('range')

    if range_header:
        # Parse range header: bytes=start-end
        try:
            range_val = range_header.strip().split('=')[1]
            start_s, end_s = range_val.split('-')
            start = int(start_s) if start_s != '' else 0
            end = int(end_s) if end_s != '' else file_size - 1
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid Range header')

        if start >= file_size or end >= file_size:
            return Response(status_code=416)

        length = end - start + 1

        def iter_range(path, start, length, chunk_size=8192):
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length)
        }
        return StreamingResponse(iter_range(path, start, length), status_code=206, media_type=content_type, headers=headers)
    else:
        return FileResponse(str(path), media_type=content_type, filename=filename)


@app.get('/upload/{job_id}/input')
async def get_uploaded_input(job_id: str, request: Request):
    """Serve the original uploaded input video for preview/download (supports range)"""
    status = get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    input_path = status.get("input_path") or status.get("inputPath")
    if not input_path or not Path(input_path).exists():
        raise HTTPException(status_code=404, detail="Input file not found")

    return _file_response_with_range(input_path, request, filename=status.get('filename') or Path(input_path).name)

@app.delete("/cleanup/{job_id}")
async def cleanup_job(job_id: str):
    """Manual cleanup of job files"""
    status = get_job_status(job_id)
    if status.get("status") == "completed":
        output_path = status.get("output_path")
        if output_path and Path(output_path).exists():
            try:
                Path(output_path).unlink()
                logger.info(f"Manually cleaned up job {job_id}")
                return {"status": "cleaned"}
            except Exception as e:
                logger.error(f"Failed to cleanup job {job_id}: {e}")
                raise HTTPException(status_code=500, detail="Cleanup failed")

    raise HTTPException(status_code=404, detail="Job not found or not completed")

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    # Create temp directories
    Path(CONFIG["processing"]["temp_dir"]).mkdir(exist_ok=True)
    Path(CONFIG["processing"]["temp_dir"], "uploads").mkdir(exist_ok=True)
    Path(CONFIG["processing"]["temp_dir"], "outputs").mkdir(exist_ok=True)

    # Start cleanup task
    asyncio.create_task(cleanup_scheduler())

async def cleanup_scheduler():
    """Periodic cleanup scheduler"""
    while True:
        await cleanup_old_files()
        await asyncio.sleep(3600)  # Run every hour

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=CONFIG["server"]["host"],
        port=CONFIG["server"]["port"],
        reload=CONFIG["server"]["debug"]
    )