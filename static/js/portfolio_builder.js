/**
 * Real-time Autosave & Dynamic Compiled Preview Service
 * Module 8 - Visual Portfolio Editor
 */

document.addEventListener('DOMContentLoaded', () => {
    const builderForm = document.getElementById('builderMainForm');
    const iframe = document.getElementById('userPreviewFrame');
    const statusText = document.getElementById('saveStatusText');
    const statusIcon = document.getElementById('saveStatusIcon');

    if (!builderForm) return;

    const updateApiUrl = builderForm.getAttribute('data-update-url');
    const previewUrl = builderForm.getAttribute('data-preview-url');

    let debounceTimer;

    // Listen to value changes on all standard input fields
    const inputs = builderForm.querySelectorAll('input:not([type="file"]), textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', () => {
            triggerSavingState();
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(performAutoSave, 800);
        });
        
        input.addEventListener('change', () => {
            triggerSavingState();
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(performAutoSave, 300);
        });
    });

    function triggerSavingState() {
        if (statusText) statusText.textContent = "Saving draft...";
        if (statusIcon) {
            statusIcon.className = "bi bi-arrow-repeat text-yellow-500 animate-spin";
        }
    }

    function performAutoSave() {
        const formData = new FormData(builderForm);

        fetch(updateApiUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (statusText) statusText.textContent = "Draft Saved";
                if (statusIcon) {
                    statusIcon.className = "bi bi-check-circle-fill text-green-500";
                }
                
                // Refresh preview iframe dynamically without parent page reload
                refreshPreviewFrame();
            } else {
                showSaveError();
            }
        })
        .catch(err => {
            console.error("Autosave error:", err);
            showSaveError();
        });
    }

    function showSaveError() {
        if (statusText) statusText.textContent = "Unsaved Changes";
        if (statusIcon) {
            statusIcon.className = "bi bi-exclamation-triangle-fill text-danger";
        }
    }

    function refreshPreviewFrame() {
        if (!iframe || !previewUrl) return;
        
        // Fetch new compiled HTML and write to iframe body for seamless non-blink load
        fetch(previewUrl)
        .then(response => response.text())
        .then(html => {
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            doc.open();
            doc.write(html);
            doc.close();
        })
        .catch(err => {
            console.error("Failed to refresh preview iframe:", err);
            // Fallback reload
            iframe.src = iframe.src;
        });
    }
});
