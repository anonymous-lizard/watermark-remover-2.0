/**
 * Sora Video Processor - Frontend JavaScript
 * Handles file uploads, processing, and downloads
 */

class VideoProcessor {
    constructor() {
        this.jobId = null;
        this.progressInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateUI();
    }

    bindEvents() {
        // File upload
        const fileInput = document.getElementById('file-input');
        const uploadArea = document.getElementById('upload-area');
        const uploadBtn = document.getElementById('upload-btn');

        if (fileInput && uploadArea) {
            // Drag and drop
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileSelect(files[0]);
                }
            });

            // Click to browse
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelect(e.target.files[0]);
                }
            });
        }

        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                fileInput.click();
            });
        }

        // Process button
        const processBtn = document.getElementById('process-btn');
        if (processBtn) {
            processBtn.addEventListener('click', () => {
                this.startProcessing();
            });
        }

        // Sliders
        this.bindSliderEvents();
    }

    bindSliderEvents() {
        const sliders = document.querySelectorAll('input[type="range"]');
        sliders.forEach(slider => {
            const valueDisplay = slider.parentElement.querySelector('.value');
            if (valueDisplay) {
                slider.addEventListener('input', () => {
                    valueDisplay.textContent = slider.value;
                });
                // Initial value
                valueDisplay.textContent = slider.value;
            }
        });
    }

    handleFileSelect(file) {
        // Validate file
        const allowedTypes = ['video/mp4', 'video/mov', 'video/avi', 'video/mkv'];
        const maxSize = 500 * 1024 * 1024; // 500MB

        if (!allowedTypes.some(type => file.type === type || file.name.toLowerCase().endsWith(type.split('/')[1]))) {
            this.showStatus('Unsupported file format. Please use MP4, MOV, AVI, or MKV.', 'error');
            return;
        }

        if (file.size > maxSize) {
            this.showStatus('File too large. Maximum size is 500MB.', 'error');
            return;
        }

        // Show selected file
        const uploadArea = document.getElementById('upload-area');
        if (uploadArea) {
            uploadArea.innerHTML = `
                <div style="font-size: 2rem; margin-bottom: 1rem;">📁</div>
                <h3>Selected: ${file.name}</h3>
                <p>Size: ${(file.size / (1024 * 1024)).toFixed(1)} MB</p>
                <button class="upload-btn" onclick="location.reload()">Choose Different File</button>
            `;
        }

        this.selectedFile = file;
        this.updateUI();
    }

    async startProcessing() {
        if (!this.selectedFile) {
            this.showStatus('Please select a video file first.', 'error');
            return;
        }

        const toolName = this.getCurrentTool();
        if (!toolName) {
            this.showStatus('Unable to determine tool.', 'error');
            return;
        }

        // Get options
        const options = this.getProcessingOptions();

        // Create form data
        const formData = new FormData();
        formData.append('file', this.selectedFile);

        // Add options as JSON string
        if (Object.keys(options).length > 0) {
            formData.append('options', JSON.stringify(options));
        }

        try {
            // Start processing
            this.showStatus('Starting processing...', 'info');
            this.setProcessingState(true);

            const response = await fetch(`/process/${toolName}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            this.jobId = result.job_id;

            // Start progress monitoring
            this.startProgressMonitoring();

        } catch (error) {
            console.error('Processing error:', error);
            this.showStatus('Failed to start processing. Please try again.', 'error');
            this.setProcessingState(false);
        }
    }

    getCurrentTool() {
        // Extract tool name from URL or page content
        const path = window.location.pathname;
        const toolMatch = path.match(/\/tool\/(.+)/);
        if (toolMatch) {
            return toolMatch[1];
        }

        // Fallback: check for tool-specific elements
        if (document.getElementById('watermark-options')) return 'watermark-removal';
        if (document.getElementById('caption-options')) return 'caption-removal';
        if (document.getElementById('stabilization-options')) return 'stabilization';
        if (document.getElementById('denoising-options')) return 'denoising';
        if (document.getElementById('color-options')) return 'color-correction';
        if (document.getElementById('upscaling-options')) return 'upscaling';
        if (document.getElementById('crop-options')) return 'crop-pad';
        if (document.getElementById('pipeline-options')) return 'full-pipeline';

        return null;
    }

    getProcessingOptions() {
        const options = {};

        // Get checkbox values
        const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            options[checkbox.name] = true;
        });

        // Get slider values
        const sliders = document.querySelectorAll('input[type="range"]');
        sliders.forEach(slider => {
            const value = parseFloat(slider.value);
            if (!isNaN(value)) {
                options[slider.name] = value;
            }
        });

        // Get select values
        const selects = document.querySelectorAll('select');
        selects.forEach(select => {
            if (select.value) {
                options[select.name] = select.value;
            }
        });

        return options;
    }

    async startProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/progress/${this.jobId}`);
                if (!response.ok) {
                    throw new Error('Failed to get progress');
                }

                const progress = await response.json();
                this.updateProgress(progress);

                if (progress.status === 'completed') {
                    this.handleProcessingComplete(progress);
                } else if (progress.status === 'failed') {
                    this.handleProcessingError(progress);
                }

            } catch (error) {
                console.error('Progress monitoring error:', error);
                this.showStatus('Lost connection to server. Please refresh the page.', 'error');
                this.stopProgressMonitoring();
            }
        }, 1000);
    }

    stopProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    updateProgress(progress) {
        const progressBar = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const etaText = document.getElementById('eta-text');

        if (progressBar && progress.percentage !== undefined) {
            progressBar.style.width = `${progress.percentage}%`;
        }

        if (progressText) {
            const current = progress.current_frame || 0;
            const total = progress.total_frames || 0;
            progressText.textContent = `Frame ${current}/${total} (${progress.percentage || 0}%)`;
        }

        if (etaText && progress.eta_seconds) {
            const eta = Math.round(progress.eta_seconds);
            etaText.textContent = `Estimated time: ${this.formatTime(eta)}`;
        }
    }

    handleProcessingComplete(progress) {
        this.stopProgressMonitoring();
        this.setProcessingState(false);

        this.showStatus('Processing completed successfully!', 'success');

        // Show download button
        const downloadSection = document.getElementById('download-section');
        if (downloadSection) {
            downloadSection.classList.remove('hidden');
        }

        // Update download link
        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn) {
            downloadBtn.href = `/download/${this.jobId}`;
            downloadBtn.textContent = '⬇️ Download Processed Video';
        }
    }

    handleProcessingError(progress) {
        this.stopProgressMonitoring();
        this.setProcessingState(false);

        const errorMsg = progress.error || 'Processing failed';
        this.showStatus(`Processing failed: ${errorMsg}`, 'error');
    }

    setProcessingState(processing) {
        const processBtn = document.getElementById('process-btn');
        const progressSection = document.getElementById('progress-section');

        if (processBtn) {
            processBtn.disabled = processing;
            processBtn.textContent = processing ? '🔄 Processing...' : '🚀 Process Video';
        }

        if (progressSection) {
            progressSection.classList.toggle('hidden', !processing);
        }
    }

    showStatus(message, type = 'info') {
        // Remove existing status messages
        const existing = document.querySelectorAll('.status-message');
        existing.forEach(el => el.remove());

        // Create new status message
        const statusDiv = document.createElement('div');
        statusDiv.className = `status-message status-${type}`;
        statusDiv.textContent = message;

        // Insert at top of container
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(statusDiv, container.firstChild);
        }

        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                statusDiv.remove();
            }, 5000);
        }
    }

    updateUI() {
        const processBtn = document.getElementById('process-btn');
        if (processBtn && !this.selectedFile) {
            processBtn.disabled = true;
        }
    }

    formatTime(seconds) {
        if (seconds < 60) {
            return `${seconds} seconds`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.videoProcessor = new VideoProcessor();
});