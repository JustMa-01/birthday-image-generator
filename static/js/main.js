document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const controls = document.getElementById('controls');
    const previewSection = document.getElementById('previewSection');
    const originalPreview = document.getElementById('originalPreview');
    const processedPreview = document.getElementById('processedPreview');
    const textInput = document.getElementById('textInput');
    const doubleLineCheckbox = document.getElementById('doubleLineCheckbox');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const regenerateBtn = document.getElementById('regenerateBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');

    let currentFile = null;

    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    // Button click handlers
    processBtn.addEventListener('click', processImage);
    downloadBtn.addEventListener('click', downloadImage);
    regenerateBtn.addEventListener('click', processImage);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            currentFile = files[0];
            if (!currentFile.type.startsWith('image/')) {
                alert('Please upload an image file');
                return;
            }
            displayOriginalImage(currentFile);
            controls.style.display = 'block';
            previewSection.style.display = 'none';
        }
    }

    function displayOriginalImage(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            originalPreview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    async function processImage() {
        if (!currentFile) {
            alert('Please select an image first');
            return;
        }

        loadingOverlay.style.display = 'flex';

        const formData = new FormData();
        formData.append('image', currentFile);
        formData.append('text', textInput.value);
        formData.append('double_line', doubleLineCheckbox.checked);

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            processedPreview.src = data.image;
            previewSection.style.display = 'grid';
            
        } catch (error) {
            alert('Error processing image: ' + error.message);
        } finally {
            loadingOverlay.style.display = 'none';
        }
    }

    async function downloadImage() {
        if (!currentFile) {
            alert('Please process an image first');
            return;
        }

        loadingOverlay.style.display = 'flex';

        const formData = new FormData();
        formData.append('image', currentFile);
        formData.append('text', textInput.value);
        formData.append('double_line', doubleLineCheckbox.checked);

        try {
            const response = await fetch('/download', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Download failed');
            }

            // Create a download link and click it
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'birthday_image.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (error) {
            alert('Error downloading image: ' + error.message);
        } finally {
            loadingOverlay.style.display = 'none';
        }
    }
});
