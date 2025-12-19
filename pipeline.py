"""
Video Processing Pipeline Orchestrator
Manages the execution of multiple processing steps
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ProcessingPipeline:
    """Orchestrates multiple video processing steps"""

    def __init__(self):
        self.steps = []
        self.config = {}

    def add_step(self, step_class, **kwargs):
        """Add a processing step to the pipeline"""
        self.steps.append({
            'class': step_class,
            'kwargs': kwargs
        })
        return self

    def set_config(self, config: Dict[str, Any]):
        """Set pipeline configuration"""
        self.config.update(config)

    def execute(self, input_path: str, output_path: str, progress_callback=None) -> bool:
        """
        Execute the full processing pipeline

        Args:
            input_path: Path to input video
            output_path: Path to output video
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        if not self.steps:
            logger.warning("No processing steps configured")
            return False

        try:
            # Import here to avoid circular imports
            from processors import utils

            # Load the video
            logger.info(f"Loading video: {input_path}")
            frames = utils.load_video_frames(input_path)

            if not frames:
                logger.error("Failed to load video frames")
                return False

            current_frames = frames
            total_steps = len(self.steps)

            for i, step_config in enumerate(self.steps):
                step_class = step_config['class']
                step_kwargs = step_config['kwargs']

                logger.info(f"Executing step {i+1}/{total_steps}: {step_class.__name__}")

                # Create processor instance
                processor = step_class()

                # Execute processing
                current_frames = processor.process(current_frames, step_kwargs)

                # Update progress
                if progress_callback:
                    progress = (i + 1) / total_steps
                    progress_callback(progress, f"Completed {step_class.__name__}")

            # Save the final result
            logger.info(f"Saving processed video: {output_path}")
            fps = self.config.get('fps', 30)
            utils.save_video_frames(current_frames, output_path, fps)

            logger.info("Pipeline execution completed successfully")
            return True

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return False

class PipelineBuilder:
    """Builder for creating processing pipelines"""

    def __init__(self):
        self.pipeline = ProcessingPipeline()

    def add_watermark_removal(self, **kwargs):
        """Add watermark removal step"""
        from processors.inpainting import WatermarkRemover
        self.pipeline.add_step(WatermarkRemover, **kwargs)
        return self

    def add_caption_removal(self, **kwargs):
        """Add caption removal step"""
        from processors.inpainting import CaptionRemover
        self.pipeline.add_step(CaptionRemover, **kwargs)
        return self

    def add_stabilization(self, **kwargs):
        """Add video stabilization step"""
        from processors.stabilization import VideoStabilizer
        self.pipeline.add_step(VideoStabilizer, **kwargs)
        return self

    def add_noise_reduction(self, **kwargs):
        """Add noise reduction step"""
        from processors.denoising import NoiseReducer
        self.pipeline.add_step(NoiseReducer, **kwargs)
        return self

    def add_color_correction(self, **kwargs):
        """Add color correction step"""
        from processors.color_correction import ColorCorrector
        self.pipeline.add_step(ColorCorrector, **kwargs)
        return self

    def add_upscaling(self, **kwargs):
        """Add resolution upscaling step"""
        from processors.upscaling import VideoUpscaler
        self.pipeline.add_step(VideoUpscaler, **kwargs)
        return self

    def add_crop_pad(self, **kwargs):
        """Add crop/pad step"""
        from processors.crop_pad import AspectAdjuster
        self.pipeline.add_step(AspectAdjuster, **kwargs)
        return self

    def set_config(self, **kwargs):
        """Set pipeline configuration"""
        self.pipeline.set_config(kwargs)
        return self

    def build(self):
        """Build and return the pipeline"""
        return self.pipeline

def create_full_pipeline(options: Dict[str, Any]) -> ProcessingPipeline:
    """
    Create a full processing pipeline based on user options

    Args:
        options: Dictionary of processing options

    Returns:
        Configured processing pipeline
    """
    builder = PipelineBuilder()

    # Add steps based on options
    if options.get('enable_watermarkremover', True):
        builder.add_watermark_removal()

    if options.get('enable_noisereducer', True):
        strength = options.get('strength', 10)
        builder.add_noise_reduction(strength=strength)

    if options.get('enable_colorcorrector', True):
        auto = options.get('auto', True)
        if auto:
            builder.add_color_correction(auto=True)
        else:
            builder.add_color_correction(
                auto=False,
                brightness=options.get('brightness', 0),
                contrast=options.get('contrast', 1.0),
                saturation=options.get('saturation', 1.0)
            )

    if options.get('enable_videoupscaler', True):
        target_resolution = options.get('target_resolution', '1080p')
        method = options.get('method', 'bicubic')
        builder.add_upscaling(
            target_resolution=target_resolution,
            method=method
        )

    if options.get('enable_videostabilizer', False):
        smoothness = options.get('smoothness', 0.5)
        builder.add_stabilization(smoothness=smoothness)

    if options.get('enable_aspectadjuster', False):
        target_aspect = options.get('target_aspect', '16:9')
        method = options.get('method', 'letterbox')
        builder.add_crop_pad(
            target_aspect=target_aspect,
            method=method
        )

    # Set default config
    builder.set_config(
        fps=options.get('fps', 30),
        quality=options.get('quality', 'high')
    )

    return builder.build()

def get_pipeline_info() -> Dict[str, Any]:
    """Get information about available pipeline steps"""
    return {
        'steps': [
            {
                'id': 'watermark_removal',
                'name': 'Watermark Removal',
                'description': 'Remove watermarks and overlays',
                'class': 'WatermarkRemover'
            },
            {
                'id': 'caption_removal',
                'name': 'Caption Removal',
                'description': 'Remove text captions and subtitles',
                'class': 'CaptionRemover'
            },
            {
                'id': 'stabilization',
                'name': 'Video Stabilization',
                'description': 'Smooth shaky footage',
                'class': 'VideoStabilizer'
            },
            {
                'id': 'noise_reduction',
                'name': 'Noise Reduction',
                'description': 'Remove compression artifacts',
                'class': 'NoiseReducer'
            },
            {
                'id': 'color_correction',
                'name': 'Color Correction',
                'description': 'Enhance colors and brightness',
                'class': 'ColorCorrector'
            },
            {
                'id': 'upscaling',
                'name': 'Resolution Upscaling',
                'description': 'Increase video resolution',
                'class': 'VideoUpscaler'
            },
            {
                'id': 'crop_pad',
                'name': 'Crop/Pad',
                'description': 'Adjust aspect ratio',
                'class': 'AspectAdjuster'
            }
        ],
        'presets': [
            {
                'id': 'basic',
                'name': 'Basic Enhancement',
                'description': 'Noise reduction and color correction',
                'steps': ['noise_reduction', 'color_correction']
            },
            {
                'id': 'full_hd',
                'name': 'Full HD Enhancement',
                'description': 'Complete processing pipeline for HD output',
                'steps': ['watermark_removal', 'noise_reduction', 'color_correction', 'upscaling']
            },
            {
                'id': 'social_media',
                'name': 'Social Media Ready',
                'description': 'Optimized for Instagram, TikTok, YouTube',
                'steps': ['watermark_removal', 'noise_reduction', 'color_correction', 'crop_pad']
            }
        ]
    }