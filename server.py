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

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

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
    """Background video processing task"""
    try:
        update_job_status(job_id, "processing", current_frame=0, total_frames=0)

        # Load video
        if not OPENCV_AVAILABLE:
            raise Exception("Video processing not available - OpenCV not installed")

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Failed to open video file")

        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        update_job_status(job_id, "processing", total_frames=total_frames)

        # Read all frames
        frames = []
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            frame_count += 1

            # Update progress every 10 frames
            if frame_count % 10 == 0:
                progress = frame_count / total_frames
                update_job_status(job_id, "processing",
                                current_frame=frame_count,
                                total_frames=total_frames,
                                percentage=int(progress * 100))

        cap.release()

        if not frames:
            raise Exception("No frames found in video")

        # Process based on tool
        processed_frames = frames

        if tool_name == "watermark-removal":
            processor = inpainting.WatermarkRemover()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "caption-removal":
            processor = inpainting.CaptionRemover()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "stabilization":
            processor = stabilization.VideoStabilizer()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "denoising":
            processor = denoising.NoiseReducer()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "color-correction":
            processor = color_correction.ColorCorrector()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "upscaling":
            processor = upscaling.VideoUpscaler()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "crop-pad":
            processor = crop_pad.AspectAdjuster()
            processed_frames = processor.process(frames, options or {})

        elif tool_name == "full-pipeline":
            # Full pipeline processing using pipeline orchestrator
            from pipeline import create_full_pipeline
            pipeline = create_full_pipeline(options or {})

            # Execute pipeline and write directly to output path to avoid storing frames
            output_dir = Path(CONFIG["processing"]["temp_dir"]) / "outputs"
            output_dir.mkdir(exist_ok=True)
            pipeline_output = output_dir / f"{job_id}_processed.mp4"

            success = pipeline.execute(input_path, str(pipeline_output), progress_callback=lambda p, msg: update_job_status(job_id, "processing", percentage=int(p * 100)))
            if not success:
                raise Exception("Pipeline execution failed")

            update_job_status(job_id, "completed",
                             output_path=str(pipeline_output),
                             file_size=pipeline_output.stat().st_size)

            logger.info(f"Processing completed for job {job_id} (full-pipeline)")
            return

        # Save processed video
        output_dir = Path(CONFIG["processing"]["temp_dir"]) / "outputs"
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / f"{job_id}_processed.mp4"

        # Write output video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps,
                            (processed_frames[0].shape[1], processed_frames[0].shape[0]))

        for i, frame in enumerate(processed_frames):
            out.write(frame)

            # Update progress during writing
            if i % 10 == 0:
                progress = 0.9 + (i / len(processed_frames)) * 0.1  # 90-100%
                update_job_status(job_id, "processing",
                                current_frame=total_frames,
                                total_frames=total_frames,
                                percentage=int(progress * 100))

        out.release()

        update_job_status(job_id, "completed",
                         output_path=str(output_path),
                         file_size=output_path.stat().st_size)

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
async def download_result(job_id: str):
    """Download processed video"""
    status = get_job_status(job_id)

    if status.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Processing not completed")

    output_path = status.get("output_path")
    if not output_path or not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    # Try to determine content type based on file extension
    return FileResponse(
        output_path,
        media_type='video/mp4',
        filename=f"sora_processed_{job_id}.mp4"
    )


@app.get('/upload/{job_id}/input')
async def get_uploaded_input(job_id: str):
    """Serve the original uploaded input video for preview/download"""
    status = get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    input_path = status.get("input_path") or status.get("inputPath")
    if not input_path or not Path(input_path).exists():
        raise HTTPException(status_code=404, detail="Input file not found")

    return FileResponse(
        input_path,
        media_type='video/mp4',
        filename=status.get('filename') or Path(input_path).name
    )

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