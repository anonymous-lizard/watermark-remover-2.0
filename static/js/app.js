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
/**
 * Sora Video Processor - Frontend JavaScript
 * Handles file uploads, processing, and downloads
 *
 * Enhancements:
 *  - Uses WebSocket for real-time progress updates when available
 *  - Falls back to polling (/progress/{jobId}) if WebSocket is not available
 *  - Keeps existing UI logic intact
 */

class VideoProcessor {
    constructor() {
        this.jobId = null;
        this.progressInterval = null;
        this.ws = null;
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

        // Show selected file info in dedicated element (don't replace file input to preserve events)
        const selectedInfo = document.getElementById('selected-info');
        if (selectedInfo) {
            selectedInfo.innerHTML = `
                <h4>Selected: ${file.name}</h4>
                <p>Size: ${(file.size / (1024 * 1024)).toFixed(1)} MB</p>
                <div style="margin-top:8px;"><button id="choose-different" class="upload-btn">Choose Different File</button></div>
            `;
            const chooseBtn = document.getElementById('choose-different');
            if (chooseBtn) chooseBtn.addEventListener('click', () => document.getElementById('file-input').click());
        }

        // Show inline preview if possible
        try {
            const previewSection = document.getElementById('preview-section');
            const previewVideo = document.getElementById('preview-video');
            if (previewVideo && previewSection) {
                const objectUrl = URL.createObjectURL(file);
                previewVideo.src = objectUrl;
                previewSection.classList.remove('hidden');
            }
        } catch (e) {
            // ignore preview errors
        }

        // Debug: log selection
        console.log('Selected file:', file.name, file.type, file.size);
        this.showStatus(`Selected ${file.name}`, 'info');

        this.selectedFile = file;
        this.updateUI();
    }

    async startProcessing() {
        console.log('startProcessing invoked');
        this.showStatus('Starting processing...', 'info');

        if (!this.selectedFile) {
            this.showStatus('Please select a video file first.', 'error');
            return;
        }

        const toolName = this.getCurrentTool();
        if (!toolName) {
            this.showStatus('Unable to determine tool. Make sure you are on a tool page.', 'error');
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
            this.setProcessingState(true);

            console.log('Uploading file to', `/process/${toolName}`);

            const response = await fetch(`/process/${toolName}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const text = await response.text().catch(() => '');
                console.error('Upload failed:', response.status, response.statusText, text);
                this.showStatus(`Failed to start processing: ${response.status} ${response.statusText}`, 'error');
                this.setProcessingState(false);
                return;
            }

            const result = await response.json();
            console.log('Upload response:', result);
            this.jobId = result.job_id;

            // If server returned an input_url, set the 'View Uploaded' button
            if (result.input_url) {
                try {
                    const viewBtn = document.getElementById('view-uploaded-btn');
                    if (viewBtn) {
                        viewBtn.href = result.input_url;
                        viewBtn.classList.remove('hidden');
                    }
                } catch (e) {}
            }

            // Try to open a websocket connection for progress updates; fallback to polling if it fails
            this.startWebSocketProgress(this.jobId).catch(err => {
                console.warn('WebSocket progress unavailable, falling back to polling:', err);
                this.startProgressMonitoring();
            });

        } catch (error) {
            console.error('Processing error:', error);
            this.showStatus('Failed to start processing. Please check console and server logs.', 'error');
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

    async startWebSocketProgress(jobId) {
        if (!("WebSocket" in window)) {
            throw new Error('WebSocket not supported by browser');
        }

        // Close any existing websocket or polling
        this.stopProgressMonitoring();
        if (this.ws) {
            try { this.ws.close(); } catch(e) { /* ignore */ }
            this.ws = null;
        }

        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${scheme}://${window.location.host}/ws/progress/${jobId}`;
        console.log('Connecting websocket to', wsUrl);

        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('Progress WebSocket opened');
                    resolve();
                };

                this.ws.onmessage = (evt) => {
                    try {
                        const progress = JSON.parse(evt.data);
                        this.updateProgress(progress);

                        if (progress.status === 'completed') {
                            this.handleProcessingComplete(progress);
                        } else if (progress.status === 'failed') {
                            this.handleProcessingError(progress);
                        }
                    } catch (e) {
                        console.warn('Invalid websocket message', e);
                    }
                };

                this.ws.onclose = (evt) => {
                    console.log('Progress WebSocket closed, falling back to polling');
                    this.ws = null;
                    // If processing still ongoing, fall back to polling
                    if (this.jobId) {
                        this.startProgressMonitoring();
                    }
                };

                this.ws.onerror = (err) => {
                    console.warn('WebSocket error:', err);
                    try { this.ws.close(); } catch(e) {}
                    this.ws = null;
                    reject(err);
                };
            } catch (err) {
                this.ws = null;
                reject(err);
            }
        });
    }

    async startProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(async () => {
            try {
                if (!this.jobId) {
                    throw new Error('Missing jobId for progress monitoring');
                }
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
        if (this.ws) {
            try { this.ws.close(); } catch(e) {}
            this.ws = null;
        }
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
        if (this.ws) {
            try { this.ws.close(); } catch(e) {}
            this.ws = null;
        }
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
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.videoProcessor = new VideoProcessor();
});