/**
 * theme_upload.js
 * Handles drag-and-drop ZIP upload UX and form submission behavior.
 */
document.addEventListener('DOMContentLoaded', function () {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('id_zip_file');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const priceField = document.getElementById('priceField');
    const isPremiumCheckbox = document.getElementById('id_is_premium');

    // ── Drag & Drop ──────────────────────────────────────────────────────────

    if (dropZone) {
        ['dragenter', 'dragover'].forEach(event => {
            dropZone.addEventListener(event, e => {
                e.preventDefault();
                dropZone.classList.add('border-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
            });
        });

        ['dragleave', 'drop'].forEach(event => {
            dropZone.addEventListener(event, e => {
                e.preventDefault();
                dropZone.classList.remove('border-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
            });
        });

        dropZone.addEventListener('drop', e => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });
    }

    // ── File Input Change ────────────────────────────────────────────────────

    if (fileInput) {
        fileInput.addEventListener('change', function () {
            if (this.files.length > 0) {
                handleFileSelect(this.files[0]);
            }
        });
    }

    function handleFileSelect(file) {
        // Validate extension
        if (!file.name.toLowerCase().endsWith('.zip')) {
            showFileError('Only .zip files are accepted.');
            return;
        }

        // Validate size (50MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            showFileError(`File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 50 MB.`);
            return;
        }

        // Assign to the real file input if dropped
        if (file !== fileInput.files[0]) {
            const dt = new DataTransfer();
            dt.items.add(file);
            fileInput.files = dt.files;
        }

        // Show filename + size
        const sizeMB = (file.size / 1024 / 1024).toFixed(2);
        if (fileNameDisplay) {
            fileNameDisplay.textContent = `✓ ${file.name} (${sizeMB} MB)`;
            fileNameDisplay.classList.remove('d-none');
        }

        // Clear any previous error
        clearFileError();

        // Update drop zone icon
        if (dropZone) {
            const icon = dropZone.querySelector('i');
            if (icon) {
                icon.className = 'bi bi-file-earmark-zip-fill text-green-500';
                icon.style.fontSize = '3rem';
            }
        }
    }

    function showFileError(msg) {
        clearFileError();
        const err = document.createElement('div');
        err.id = 'fileErrorMsg';
        err.className = 'alert alert-danger mt-3 mb-0 text-sm rounded-lg';
        err.textContent = msg;
        if (dropZone) dropZone.appendChild(err);
        if (fileNameDisplay) fileNameDisplay.classList.add('d-none');
    }

    function clearFileError() {
        document.getElementById('fileErrorMsg')?.remove();
    }

    // ── Form Submit (show progress) ──────────────────────────────────────────

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            // Quick client-side guard
            if (!fileInput || !fileInput.files.length) {
                e.preventDefault();
                showFileError('Please select a ZIP file before uploading.');
                return;
            }

            // Show progress bar + disable button
            if (uploadProgress) uploadProgress.classList.remove('d-none');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
            }
        });
    }

    // ── Premium / Price Toggle ───────────────────────────────────────────────

    window.togglePrice = function (checkbox) {
        if (priceField) {
            priceField.style.display = checkbox.checked ? '' : 'none';
        }
        if (!checkbox.checked) {
            const priceInput = document.getElementById('id_price');
            if (priceInput) priceInput.value = '0.00';
        }
    };
});
