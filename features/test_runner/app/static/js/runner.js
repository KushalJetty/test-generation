// Global variables
let eventSource;
let testConfig = {};
let testStats = {
    total: 0,
    passed: 0,
    failed: 0,
    retried: 0
};

// DOM elements
const statusBadge = document.getElementById('statusBadge');
const progressBar = document.getElementById('progressBar');
const stepsList = document.getElementById('stepsList');
const consoleOutput = document.getElementById('consoleOutput');
const screenshotGallery = document.getElementById('screenshotGallery');
const viewReportBtn = document.getElementById('viewReportBtn');
const stopTestBtn = document.getElementById('stopTestBtn');

// Stats elements
const totalStepsEl = document.getElementById('totalSteps');
const passedStepsEl = document.getElementById('passedSteps');
const failedStepsEl = document.getElementById('failedSteps');
const retriedStepsEl = document.getElementById('retriedSteps');

// Form elements
const testConfigForm = document.getElementById('testConfigForm');
const testFile = document.getElementById('testFile');
const testUrl = document.getElementById('testUrl');
const defaultMode = document.getElementById('defaultMode');
const customBatchMode = document.getElementById('customBatchMode');
const customDynamicMode = document.getElementById('customDynamicMode');
const customBatchInputsSection = document.getElementById('customBatchInputsSection');
const customInputs = document.getElementById('customInputs');
const browserSelect = document.getElementById('browserSelect');
const headlessMode = document.getElementById('headlessMode');
const retryCount = document.getElementById('retryCount');
const stopOnFailure = document.getElementById('stopOnFailure');
const vpnConfig = document.getElementById('vpnConfig');
const reportFormat = document.getElementById('reportFormat');
const runTestBtn = document.getElementById('runTestBtn');

// Dynamic input elements
const dynamicInputModal = document.getElementById('dynamicInputModal');
const inputFieldName = document.getElementById('inputFieldName');
const dynamicInputField = document.getElementById('dynamicInputField');
const originalValueText = document.getElementById('originalValueText');
const elementScreenshot = document.getElementById('elementScreenshot');
const submitInputBtn = document.getElementById('submitInputBtn');

// Step failure elements
const stepFailureModal = document.getElementById('stepFailureModal');
const failedStepInfo = document.getElementById('failedStepInfo');
const failureMessage = document.getElementById('failureMessage');
const failureScreenshot = document.getElementById('failureScreenshot');
const terminateTestBtn = document.getElementById('terminateTestBtn');

// Schedule elements
const scheduleForm = document.getElementById('scheduleForm');
const scheduleTestSelect = document.getElementById('scheduleTestSelect');
const scheduleDateTime = document.getElementById('scheduleDateTime');
const recurrenceSelect = document.getElementById('recurrenceSelect');
const scheduleTestBtn = document.getElementById('scheduleTestBtn');
const scheduledTestsList = document.getElementById('scheduledTestsList');

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    setupEventListeners();

    // Load scheduled tests
    loadScheduledTests();

    // Set default date/time for scheduling
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5); // Default to 5 minutes from now
    scheduleDateTime.value = now.toISOString().slice(0, 16);
});

// Set up event listeners
function setupEventListeners() {
    // Toggle custom inputs section based on mode selection
    document.querySelectorAll('input[name="optimizationMode"]').forEach(radio => {
        radio.addEventListener('change', () => {
            customBatchInputsSection.style.display = customBatchMode.checked ? 'block' : 'none';
        });
    });

    // Set up dynamic input modal
    submitInputBtn.addEventListener('click', submitDynamicInput);

    // Set up step failure modal
    terminateTestBtn.addEventListener('click', () => {
        stopEventSource();
        updateStatus('Terminated', 'danger');
        const modal = bootstrap.Modal.getInstance(document.getElementById('stepFailureModal'));
        if (modal) modal.hide();
    });

    // Handle test file upload
    testFile.addEventListener('change', handleTestFileUpload);

    // Run test button
    runTestBtn.addEventListener('click', startTestExecution);

    // Stop test button
    stopTestBtn.addEventListener('click', stopTestExecution);

    // Schedule test button
    scheduleTestBtn.addEventListener('click', scheduleTest);

    // View report button
    viewReportBtn.addEventListener('click', viewTestReport);
}

// Handle test file upload
async function handleTestFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Create form data
    const formData = new FormData();
    formData.append('test_file', file);

    try {
        const response = await fetch('/upload-test', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Pre-fill form with test configuration
            if (data.test_config) {
                testConfig = data.test_config;

                // Fill URL if available
                if (testConfig.url) {
                    testUrl.value = testConfig.url;
                }

                // Set optimization mode
                if (testConfig.mode === 'custom-batch') {
                    customBatchMode.checked = true;
                    customBatchInputsSection.style.display = 'block';
                } else if (testConfig.mode === 'custom-dynamic') {
                    customDynamicMode.checked = true;
                    customBatchInputsSection.style.display = 'none';
                } else {
                    defaultMode.checked = true;
                    customBatchInputsSection.style.display = 'none';
                }

                // Set advanced options if available
                if (testConfig.browser) {
                    browserSelect.value = testConfig.browser;
                }

                if (testConfig.headless !== undefined) {
                    headlessMode.checked = testConfig.headless;
                }

                if (testConfig.retries !== undefined) {
                    retryCount.value = testConfig.retries;
                }

                if (testConfig.stopOnFailure !== undefined) {
                    stopOnFailure.checked = testConfig.stopOnFailure;
                }

                if (testConfig.report_format) {
                    reportFormat.value = testConfig.report_format;
                }
            }
        } else {
            showError(data.message || 'Failed to parse test file');
        }
    } catch (error) {
        showError('Error uploading test file: ' + error.message);
    }
}

// Start test execution
async function startTestExecution() {
    // Reset UI
    resetUI();

    // Enable stop button
    stopTestBtn.disabled = false;

    // Update status
    updateStatus('Preparing', 'primary');

    // Gather configuration from form
    const config = {
        url: testUrl.value,
        mode: document.querySelector('input[name="optimizationMode"]:checked').value,
        browser: browserSelect.value,
        headless: headlessMode.checked,
        retries: parseInt(retryCount.value),
        stopOnFailure: stopOnFailure.checked,
        report_format: reportFormat.value
    };

    // Add test steps from uploaded file
    if (testConfig.test_steps) {
        config.test_steps = testConfig.test_steps;
    }

    // Handle custom inputs for batch mode
    if (customBatchMode.checked && customInputs.files.length > 0) {
        const inputFile = customInputs.files[0];
        const inputFormData = new FormData();
        inputFormData.append('input_file', inputFile);

        try {
            const response = await fetch('/upload-inputs', {
                method: 'POST',
                body: inputFormData
            });

            const data = await response.json();

            if (data.status === 'success') {
                config.inputs = data.file_path;
                config.input_type = 'batch';
            } else {
                showError(data.message || 'Failed to upload input file');
                return;
            }
        } catch (error) {
            showError('Error uploading input file: ' + error.message);
            return;
        }
    } else if (customDynamicMode.checked) {
        // For dynamic mode, just set the input type
        config.input_type = 'dynamic';
    }

    // Handle VPN configuration
    if (vpnConfig.files.length > 0) {
        const vpnFile = vpnConfig.files[0];
        const vpnFormData = new FormData();
        vpnFormData.append('vpn_file', vpnFile);

        try {
            const response = await fetch('/upload-vpn', {
                method: 'POST',
                body: vpnFormData
            });

            const data = await response.json();

            if (data.status === 'success') {
                config.vpn_config = data.file_path;
            } else {
                showError(data.message || 'Failed to upload VPN configuration');
                return;
            }
        } catch (error) {
            showError('Error uploading VPN configuration: ' + error.message);
            return;
        }
    }

    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('configModal'));
    modal.hide();

    // Start the event source
    startEventSource();

    // Send the test configuration to the server
    try {
        const response = await fetch('/run-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.status === 'queued') {
            updateStatus('Queued', 'info');
        } else {
            showError(data.message || 'Failed to start test execution');
            stopEventSource();
        }
    } catch (error) {
        showError('Error starting test execution: ' + error.message);
        stopEventSource();
    }
}

// Start the event source for real-time updates
function startEventSource() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/event-stream');

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'status':
                updateStatus(data.data, 'primary');
                break;

            case 'step_update':
                updateStepProgress(data.data);
                break;

            case 'screenshot':
                addScreenshot(data.data);
                break;

            case 'error':
                logConsoleMessage('error', data.data);
                showError(data.data);
                break;

            case 'console':
                logConsoleMessage(data.data.type, data.data.text);
                break;

            case 'report':
                handleReportGenerated(data.data);
                break;

            case 'heartbeat':
                // Ignore heartbeat messages
                break;

            case 'input_required':
                handleDynamicInput(data.data);
                break;

            case 'step_failure':
                handleStepFailure(data.data);
                break;
        }
    };

    eventSource.onerror = function() {
        console.error('EventSource failed');
    };
}

// Stop the event source
function stopEventSource() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

// Stop test execution
async function stopTestExecution() {
    try {
        // Call the stop-test endpoint
        const response = await fetch('/stop-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Stop the event source
            stopEventSource();

            // Update status
            updateStatus('Stopped', 'warning');

            // Disable stop button
            stopTestBtn.disabled = true;

            // Log to console
            logConsoleMessage('info', 'Test execution stopped by user');
        } else {
            showError(data.message || 'Failed to stop test execution');
        }
    } catch (error) {
        showError('Error stopping test execution: ' + error.message);
    }
}

// Update the status badge
function updateStatus(status, type) {
    statusBadge.textContent = status;
    statusBadge.className = `badge bg-${type}`;

    // Log to console
    logConsoleMessage('info', `Status: ${status}`);
}

// Update step progress
function updateStepProgress(data) {
    // Update progress bar
    const progress = Math.round((data.step / data.total) * 100);
    progressBar.style.width = `${progress}%`;
    progressBar.textContent = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);

    // Add step to the list
    const row = document.createElement('tr');
    row.className = getStatusClass(data.status);

    row.innerHTML = `
        <td>${data.step}</td>
        <td>${data.action}</td>
        <td>${data.selector}</td>
        <td>${data.status}</td>
        <td>${data.time}s</td>
    `;

    stepsList.appendChild(row);

    // Update stats
    updateStats(data.status);

    // Scroll to the bottom of the steps list
    const stepsContainer = stepsList.parentElement;
    stepsContainer.scrollTop = stepsContainer.scrollHeight;

    // Log to console
    logConsoleMessage('info', `Step ${data.step}: ${data.action} ${data.selector} - ${data.status}`);
}

// Get CSS class for step status
function getStatusClass(status) {
    switch (status) {
        case 'passed':
            return 'table-success';
        case 'failed':
            return 'table-danger';
        case 'skipped':
            return 'table-warning';
        default:
            return '';
    }
}

// Update test statistics
function updateStats(status) {
    testStats.total++;

    if (status === 'passed') {
        testStats.passed++;
    } else if (status === 'failed') {
        testStats.failed++;
    } else if (status === 'retry') {
        testStats.retried++;
    }

    // Update UI
    totalStepsEl.textContent = testStats.total;
    passedStepsEl.textContent = testStats.passed;
    failedStepsEl.textContent = testStats.failed;
    retriedStepsEl.textContent = testStats.retried;
}

// Add a screenshot to the gallery
function addScreenshot(path) {
    const col = document.createElement('div');
    col.className = 'col-md-4 mb-3';

    // Extract the filename from the path
    const filename = path.split('/').pop();

    col.innerHTML = `
        <div class="card">
            <img src="/screenshots/${filename}" class="card-img-top" alt="Screenshot">
            <div class="card-body">
                <p class="card-text">Screenshot</p>
            </div>
        </div>
    `;

    screenshotGallery.appendChild(col);
}

// Log a console message
function logConsoleMessage(type, message) {
    const timestamp = new Date().toLocaleTimeString();
    const logClass = getLogClass(type);

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${logClass}`;
    logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> ${message}`;

    consoleOutput.appendChild(logEntry);

    // Scroll to the bottom
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// Get CSS class for log type
function getLogClass(type) {
    switch (type) {
        case 'error':
            return 'log-error';
        case 'warning':
            return 'log-warning';
        case 'info':
            return 'log-info';
        default:
            return '';
    }
}

// Handle report generation
function handleReportGenerated(reportPath) {
    viewReportBtn.dataset.reportPath = reportPath;
    viewReportBtn.disabled = false;

    updateStatus('Completed', 'success');

    // Log to console
    logConsoleMessage('info', `Report generated: ${reportPath}`);
}

// View the test report
function viewTestReport() {
    const reportPath = viewReportBtn.dataset.reportPath;
    if (reportPath) {
        // Extract just the filename from the path
        const filename = reportPath.split('/').pop();
        window.open(`/reports/${filename}`, '_blank');
    }
}

// Show error modal
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;

    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    errorModal.show();

    // Update status
    updateStatus('Error', 'danger');
}

// Reset the UI for a new test run
function resetUI() {
    // Reset status
    statusBadge.textContent = 'Ready';
    statusBadge.className = 'badge bg-primary';

    // Reset progress bar
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressBar.setAttribute('aria-valuenow', 0);

    // Clear steps list
    stepsList.innerHTML = '';

    // Clear console output
    consoleOutput.innerHTML = '';

    // Clear screenshots
    screenshotGallery.innerHTML = '';

    // Reset stats
    testStats = {
        total: 0,
        passed: 0,
        failed: 0,
        retried: 0
    };

    totalStepsEl.textContent = '0';
    passedStepsEl.textContent = '0';
    failedStepsEl.textContent = '0';
    retriedStepsEl.textContent = '0';

    // Disable buttons
    viewReportBtn.disabled = true;
    viewReportBtn.dataset.reportPath = '';
    stopTestBtn.disabled = true;
}

// Load scheduled tests
async function loadScheduledTests() {
    try {
        const response = await fetch('/get-scheduled-tests');
        const data = await response.json();

        // Clear the list
        scheduledTestsList.innerHTML = '';

        // Add tests to the list
        if (data.tests && Object.keys(data.tests).length > 0) {
            for (const [id, test] of Object.entries(data.tests)) {
                addScheduledTest(id, test);
            }
        } else {
            // Show empty message
            scheduledTestsList.innerHTML = '<li class="list-group-item text-center">No scheduled tests</li>';
        }
    } catch (error) {
        console.error('Error loading scheduled tests:', error);
    }
}

// Add a scheduled test to the list
function addScheduledTest(id, test) {
    const item = document.createElement('li');
    item.className = 'list-group-item d-flex justify-content-between align-items-center';

    const scheduleTime = new Date(test.schedule_time).toLocaleString();
    const statusBadge = getScheduleStatusBadge(test.status);

    item.innerHTML = `
        <div>
            <strong>Test ID: ${id}</strong>
            <div>Scheduled: ${scheduleTime}</div>
        </div>
        <div>
            ${statusBadge}
            <button class="btn btn-sm btn-outline-danger cancel-btn" data-test-id="${id}">Cancel</button>
        </div>
    `;

    // Add cancel button event listener
    item.querySelector('.cancel-btn').addEventListener('click', () => cancelScheduledTest(id));

    scheduledTestsList.appendChild(item);
}

// Get status badge for scheduled test
function getScheduleStatusBadge(status) {
    switch (status) {
        case 'scheduled':
            return '<span class="badge bg-info">Scheduled</span>';
        case 'running':
            return '<span class="badge bg-primary">Running</span>';
        case 'completed':
            return '<span class="badge bg-success">Completed</span>';
        case 'cancelled':
            return '<span class="badge bg-warning">Cancelled</span>';
        case 'failed':
            return '<span class="badge bg-danger">Failed</span>';
        default:
            return '<span class="badge bg-secondary">Unknown</span>';
    }
}

// Schedule a test
async function scheduleTest() {
    const dateTime = scheduleDateTime.value;
    const recurrence = recurrenceSelect.value;

    if (!dateTime) {
        showError('Please select a date and time');
        return;
    }

    // Get the test configuration
    const config = {
        schedule_time: dateTime,
        recurrence: recurrence,
        // Add other test configuration
    };

    try {
        const response = await fetch('/schedule-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.status === 'scheduled') {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('scheduleModal'));
            modal.hide();

            // Reload scheduled tests
            loadScheduledTests();

            // Log to console
            logConsoleMessage('info', `Test scheduled with ID: ${data.test_id}`);
        } else {
            showError(data.message || 'Failed to schedule test');
        }
    } catch (error) {
        showError('Error scheduling test: ' + error.message);
    }
}

// Cancel a scheduled test
async function cancelScheduledTest(testId) {
    try {
        const response = await fetch('/cancel-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ test_id: testId })
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Reload scheduled tests
            loadScheduledTests();

            // Log to console
            logConsoleMessage('info', `Test ${testId} cancelled`);
        } else {
            showError(data.message || 'Failed to cancel test');
        }
    } catch (error) {
        showError('Error cancelling test: ' + error.message);
    }
}

// Handle dynamic input request
function handleDynamicInput(data) {
    // Set the input field name
    inputFieldName.textContent = data.selector;

    // Set the original value
    originalValueText.textContent = `Original value: ${data.original_value || '(empty)'}`;

    // Set the screenshot
    elementScreenshot.src = `/screenshots/${data.screenshot.split('/').pop()}`;

    // Clear any previous input
    dynamicInputField.value = '';

    // Store the input ID for later use
    dynamicInputField.dataset.inputId = data.input_id;

    // Show the modal
    const modal = new bootstrap.Modal(dynamicInputModal);
    modal.show();

    // Focus the input field
    dynamicInputField.focus();

    // Log to console
    logConsoleMessage('info', `Input required for ${data.selector}`);
}

// Submit dynamic input
async function submitDynamicInput() {
    const inputId = dynamicInputField.dataset.inputId;
    const value = dynamicInputField.value;
    const selector = inputFieldName.textContent;

    if (!inputId) {
        showError('No input ID found');
        return;
    }

    try {
        const response = await fetch('/set-input-value', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                input_id: inputId,
                value: value
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Hide the modal
            const modal = bootstrap.Modal.getInstance(dynamicInputModal);
            modal.hide();

            // Log to console
            logConsoleMessage('info', `Input provided for ${selector}: ${value}`);
        } else {
            showError(data.message || 'Failed to submit input');
        }
    } catch (error) {
        showError('Error submitting input: ' + error.message);
    }
}

// Handle step failure
function handleStepFailure(data) {
    // Set the step information
    failedStepInfo.textContent = JSON.stringify(data.step, null, 2);

    // Set the error message
    failureMessage.textContent = data.message;

    // Set the screenshot
    failureScreenshot.src = `/screenshots/${data.screenshot.split('/').pop()}`;

    // Show the modal
    const modal = new bootstrap.Modal(stepFailureModal);
    modal.show();

    // Log to console
    logConsoleMessage('error', `Step failed: ${data.message}`);
}
