/**
 * @file Client-side logic for the translation pipeline UI.
 * @description Handles form submission, file uploads, and status updates.
 */

/**
 * Updates the displayed filename when a file is selected.
 * @param {HTMLInputElement} input - The file input element
 * @param {string} spanId - The ID of the span element to update.
 */
function updateFileName(input, spanId) {
    const span = document.getElementById(spanId);

    if (input.files.length > 0) {
        const name = input.files[0].name;
        const displayName = name.length > 30 ? name.substring(0, 27) + '...' : name;

        span.textContent = displayName;
        span.classList.add('text-blue-400');
    } else {
        span.textContent = 'Drop file here or click to browse';
        span.classList.remove('text-blue-400');
    }
}

/**
 * Formats and displays a status message in the terminal output.
 * @param {string} message - The message to format and display.
 */
function formatStatusMessage(message) {
    const statusOutput = document.getElementById('status-output');
    const line = document.createElement('div');
    line.classList.add('flex', 'items-start');

    let icon = '<span class="mr-2 text-slate-500 w-5 text-center">&gt;</span>';
    let textClass = 'text-green-400/90';
    let msgText = message;

    if (message.includes('Validating translated chunk')) {
        icon = "";
        textClass = 'text-blue-300';
    } else if (message.includes('Validation') && message.includes('complete')) {
        icon = '<span class="mr-2 text-green-500 w-5 flex-shrink-0">✓</span>';
        textClass = 'text-slate-300';
    } else if (message.includes('Validation failed') || message.includes('Warning')) {
        icon = '<span class="mr-2 text-red-500 w-5 flex-shrink-0">✗</span>';
        textClass = 'text-red-400';
    } else if (message.includes('PROCESS COMPLETED')) {
        icon = '<span class="mr-2 text-green-500 w-5 flex-shrink-0">✓</span>';
        textClass = 'text-green-400';
        msgText = `<strong>${message}</strong>`;
    } else if (message.includes('FATAL ERROR') || message.includes('ERROR')) {
        icon = '<span class="mr-2 text-red-500 w-5 flex-shrink-0">✗</span>';
        textClass = 'text-red-400';
        msgText = `<strong>${message}</strong>`;
    } else if (message.includes('successfully') || message.includes('complete')) {
        icon = '<span class="mr-2 text-green-500 w-5 flex-shrink-0">✓</span>';
        textClass = 'text-green-300';
    }

    line.innerHTML = `${icon}<span class="${textClass}">${msgText}</span>`;
    statusOutput.appendChild(line);

    statusOutput.scrollTop = statusOutput.scrollHeight;
}

document.getElementById('translation-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const submitBtn = document.getElementById('submit-btn');
    const statusContainer = document.getElementById('status-container');
    const statusOutput = document.getElementById('status-output');

    statusOutput.innerHTML = '';
    formatStatusMessage('Initializing secure connection to translation pipeline...');

    statusContainer.classList.remove('hidden');
    setTimeout(() => statusContainer.classList.remove('opacity-0'), 50);

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    try {
        const response = await fetch('/translate', {
            method: 'POST',
            body: new FormData(this),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP Error [${response.status}]: ${response.statusText}`);
        }

        const data = await response.json();

        formatStatusMessage(`[SUCCESS] - Pipeline started for session: ${data.session_id}`);
        formatStatusMessage(`Output will be available at: ${data.output_location}`);
        formatStatusMessage('You can start another job. This window can be closed.');

    } catch (error) {
        formatStatusMessage(`[FATAL ERROR]: ${error.message}`);
        console.error('Translation pipeline error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Translate';
    }
});

/**
 * Validates form inputs before submission.
 * @returns {boolean} True if form is valid, false otherwise.
 */
function validateForm() {
    const sourceFile = document.getElementById('source_file').value;
    const targetLanguage = document.getElementById('target_language').value;
    const gcsBucket = document.getElementById('gcs_bucket').value;

    if (!sourceFile || !targetLanguage || !gcsBucket) {
        alert('Please fill in all required fields');
        return false;
    }

    return true;
}

/**
 * Formats file size for display.
 * @param {number} bytes - Size in bytes.
 * @returns {string} Formatted file size.
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
