# Sora Video Processor

A local, private video processing server for removing watermarks, enhancing quality, and processing Sora-generated videos. Runs entirely on your PC with a clean web interface accessible from your phone.

## Features

- 🎯 **Watermark Removal**: Dynamic inpainting for moving Sora watermarks
- 📝 **Caption Removal**: Remove text overlays and subtitles
- 🎥 **Video Stabilization**: Smooth shaky footage
- ✨ **Noise Reduction**: Remove compression artifacts
- 🎨 **Color Correction**: Enhance brightness, contrast, saturation
- 📐 **Resolution Upscaling**: Scale to 720p/1080p
- ✂️ **Crop/Pad**: Adjust aspect ratios for platforms
- ⚡ **Full Pipeline**: All-in-one processing

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python server.py
```

### 3. Access from Your Phone

1. Find your PC's local IP address:
   - **Windows**: `ipconfig` (look for IPv4 Address)
   - **macOS/Linux**: `ifconfig` or `ip addr`

2. On your phone, open a browser and go to:
   ```
   http://[YOUR_PC_IP]:8000
   ```

3. Select a tool and upload your video!

## System Requirements

- **OS**: Windows 10/11, macOS 10.15+, or Linux
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Network**: Local Wi-Fi network

## Architecture

```
Phone (Browser) ← Wi-Fi → PC Server (FastAPI)
                              ↓
                       Python/OpenCV Pipeline
                              ↓
                       Processed Video → Download
```

## Privacy & Security

- ✅ **Fully Local**: No cloud uploads or external APIs
- ✅ **No Tracking**: No analytics or user data collection
- ✅ **Temporary Files**: Auto-cleanup after 24 hours
- ✅ **Wi-Fi Only**: No internet exposure required

## Processing Tools

### Watermark Removal
- Dynamic inpainting with temporal blending
- Handles moving watermarks automatically
- Manual bounding box option available

### Caption Removal
- Detects and removes text overlays
- Variable size caption support
- Preserves video content

### Video Stabilization
- Optical flow motion estimation
- Configurable smoothing strength
- Minimal cropping

### Noise Reduction
- Non-local Means denoising
- Adjustable strength (1-30)
- Removes compression artifacts

### Color Correction
- Automatic CLAHE enhancement
- Manual brightness/contrast/saturation
- LAB color space processing

### Resolution Upscaling
- Bicubic interpolation (fast)
- DNN super resolution (optional)
- 720p/1080p targets

### Crop/Pad/Letterbox
- Platform presets (YouTube, Instagram, etc.)
- Center crop or letterbox options
- Maintains aspect ratios

### Full Pipeline
- Toggle individual processing steps
- Customizable processing order
- All tools in one pass

## Performance

- **720p 30s video**: < 1 minute
- **1080p 2min video**: < 10 minutes
- Memory usage: < 4GB peak
- Scales linearly with video length

## Troubleshooting

### Server Won't Start
- Check Python version: `python --version`
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 availability

### Can't Access from Phone
- Ensure both devices on same Wi-Fi network
- Check firewall settings
- Try different IP address
- Disable mobile data (use Wi-Fi only)

### Processing Fails
- Check video format (MP4/MOV/AVI/MKV)
- Ensure video < 500MB
- Check available disk space
- Try smaller video first

### Slow Processing
- Close other applications
- Ensure 8GB+ RAM available
- Process shorter videos
- Use lower resolution input

## Development

### Project Structure
```
sora-video-processor/
├── server.py              # FastAPI server
├── pipeline.py            # Processing orchestration
├── processors/            # Individual processing modules
│   ├── inpainting.py      # Watermark/caption removal
│   ├── stabilization.py   # Video stabilization
│   ├── upscaling.py       # Resolution enhancement
│   ├── denoising.py       # Noise reduction
│   ├── color_correction.py # Color enhancements
│   ├── crop_pad.py        # Aspect ratio adjustment
│   ├── utils.py           # Helper functions
│   └── __init__.py        # Package initialization
├── static/                # Web interface
│   ├── index.html         # Home page
│   ├── watermark-removal.html
│   ├── caption-removal.html
│   ├── stabilization.html
│   ├── denoising.html
│   ├── color-correction.html
│   ├── upscaling.html
│   ├── crop-pad.html
│   ├── full-pipeline.html
│   ├── css/
│   │   └── style.css      # ViewMax.io inspired styles
│   └── js/
│       └── app.js         # Frontend JavaScript
├── temp/                  # Temporary files
│   ├── uploads/           # Upload directory
│   └── outputs/           # Processed videos
├── requirements.txt       # Python dependencies
└── README.md              # This documentation
```

### Adding New Tools

1. Create processor in `processors/`
2. Add route in `server.py`
3. Create HTML page in `static/`
4. Update home page grid

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in terminal
3. Test with sample videos
4. Open an issue on GitHub

---

**Built with:** FastAPI, OpenCV, NumPy  
**Theme:** ViewMax.io inspired (White & Blue)  
**Philosophy:** Local, Private, Powerful 🚀