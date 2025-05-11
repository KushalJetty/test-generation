/**
 * Test recorder functionality for StreamzAI
 */

function setupRecorder(suiteId, options) {
    const elementIds = {
        startBtn: options.startBtnId || `startBtn${suiteId}`,
        stopBtn: options.stopBtnId || `stopBtn${suiteId}`,
        clearBtn: options.clearBtnId || `clearBtn${suiteId}`,
        saveBtn: options.saveBtnId || `saveBtn${suiteId}`,
        recordedActions: options.recordedActionsId || `recordedActions${suiteId}`,
        generatedCode: options.generatedCodeId || `generatedCode${suiteId}`,
        urlInput: options.urlInputId || `urlInput${suiteId}`
    };

    let eventSource;
    const startBtn = document.getElementById(elementIds.startBtn);
    const stopBtn = document.getElementById(elementIds.stopBtn);
    const clearBtn = document.getElementById(elementIds.clearBtn);
    const saveBtn = document.getElementById(elementIds.saveBtn);
    const recordedActions = document.getElementById(elementIds.recordedActions);
    const codePreview = document.getElementById(elementIds.generatedCode);
    const urlInput = document.getElementById(elementIds.urlInput);

    let actionsArray = [];

    function updateButtonStates(isRecording) {
        startBtn.disabled = isRecording;
        stopBtn.disabled = !isRecording;
        clearBtn.disabled = !isRecording;
        saveBtn.disabled = !actionsArray.length;
    }

    function renderActions() {
        recordedActions.textContent = JSON.stringify(actionsArray, null, 2);
        saveBtn.disabled = !actionsArray.length;
    }

    function addAction(action) {
        actionsArray.push(action);
        renderActions();
    }

    function clearActions() {
        actionsArray = [];
        renderActions();
        codePreview.textContent = '';
    }

    startBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            alert('Please enter a URL first.');
            return;
        }
        try {
            const response = await fetch('/api/record/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            if (response.ok) {
                updateButtonStates(true);
                // Start listening for events
                if (eventSource) eventSource.close();
                eventSource = new EventSource('/api/record/stream');
                eventSource.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'clear') {
                        clearActions();
                    }
                    if (data.type === 'action') {
                        addAction(data.data);
                    }
                    if (data.type === 'code') {
                        codePreview.textContent = data.data;
                    }
                };
            } else {
                alert('Failed to start recording');
            }
        } catch (error) {
            console.error('Error starting recording:', error);
            alert('Failed to start recording');
        }
    });

    stopBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/record/stop', { method: 'POST' });
            if (response.ok) {
                const data = await response.json();
                if (data.steps) {
                    actionsArray = data.steps;
                    renderActions();
                }
                if (data.code) {
                    codePreview.textContent = data.code;
                }
                updateButtonStates(false);
                if (eventSource) eventSource.close();
            }
        } catch (error) {
            console.error('Error stopping recording:', error);
            alert('Failed to stop recording');
        }
    });

    clearBtn.addEventListener('click', async () => {
        try {
            clearActions();
            await fetch('/api/record/clear', { method: 'POST' });
        } catch (error) {
            console.error('Error clearing actions:', error);
            alert('Failed to clear actions');
        }
    });

    saveBtn.addEventListener('click', async () => {
        // Always stop recording before saving
        await stopBtn.click();
        const codeContent = codePreview.textContent;
        
        // Create a custom modal for test case name and description
        const modalId = `saveTestCaseModal${suiteId}`;
        
        // Remove any existing modal with the same ID
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }
        
        const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Save Test Case</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="saveTestCaseForm${suiteId}">
                            <div class="mb-3">
                                <label for="testCaseName${suiteId}" class="form-label">Test Case Name</label>
                                <input type="text" class="form-control" id="testCaseName${suiteId}" 
                                       value="Recorded Test ${new Date().toISOString().replace(/[:.]/g, '-')}" required>
                            </div>
                            <div class="mb-3">
                                <label for="testCaseDescription${suiteId}" class="form-label">Description</label>
                                <textarea class="form-control" id="testCaseDescription${suiteId}" rows="3" 
                                          placeholder="Enter test case description..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirmSaveBtn${suiteId}">Save</button>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Add the modal to the document
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Initialize the modal
        const saveModal = new bootstrap.Modal(document.getElementById(modalId));
        saveModal.show();
        
        // Handle save confirmation
        document.getElementById(`confirmSaveBtn${suiteId}`).addEventListener('click', async () => {
            const testName = document.getElementById(`testCaseName${suiteId}`).value.trim();
            const testDescription = document.getElementById(`testCaseDescription${suiteId}`).value.trim();
            
            if (!testName) {
                alert('Please enter a test case name');
                return;
            }
            
            try {
                // Save to database
                const response = await fetch('/api/record/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        suite_id: suiteId,
                        code: codeContent,
                        name: testName,
                        description: testDescription
                    })
                });
                
                const saveResult = await response.json();
                
                if (saveResult.status === 'success') {
                    alert('Test case saved successfully!');
                    
                    // Close the save modal
                    saveModal.hide();
                    
                    // If recorder modal is shown, close it
                    const recorderModalElement = document.querySelector(`#recordModal${suiteId}`);
                    if (recorderModalElement) {
                        const recorderModal = bootstrap.Modal.getInstance(recorderModalElement);
                        if (recorderModal) {
                            recorderModal.hide();
                        }
                    }
                    
                    // Automatically redirect to the test suite page
                    window.location.href = `/test-suite/${suiteId}`;
                } else {
                    alert(`Error saving test case: ${saveResult.error || 'Unknown error'}`);
                }
            } catch (err) {
                console.error('Error saving file:', err);
                alert('Error saving test case.');
            }
        });
    });

    // Initial state
    updateButtonStates(false);
    renderActions();

    return {
        updateButtonStates,
        renderActions,
        addAction,
        clearActions
    };
}

class BrowserRecorder {
    constructor() {
        this.recording = false;
        this.actions = [];
        this.observer = null;
        this.lastActionTime = null;
        this.minimumDelay = 300; // Reduced delay for better responsiveness
        this.inputBuffer = new Map(); // Buffer for input changes
        this.inputTimeout = 1000; // Delay before recording input changes
    }

    startRecording() {
        this.recording = true;
        this.actions = [];
        this.lastActionTime = null;
        this.inputBuffer.clear();
        this.setupEventListeners();
    }

    stopRecording() {
        this.recording = false;
        this.removeEventListeners();
        // Flush any pending input changes
        this.inputBuffer.forEach((timer, element) => {
            clearTimeout(timer);
            this.recordInputChange(element);
        });
        return this.actions;
    }

    setupEventListeners() {
        // Listen for clicks
        document.addEventListener('click', this.handleClick.bind(this), true);
        
        // Listen for input changes
        document.addEventListener('input', this.handleInput.bind(this), true);
        document.addEventListener('change', this.handleChange.bind(this), true);
        
        // Listen for form submissions
        document.addEventListener('submit', this.handleSubmit.bind(this), true);
        
        // Listen for key presses
        document.addEventListener('keydown', this.handleKeyPress.bind(this), true);
        
        // Listen for navigation
        window.addEventListener('popstate', this.handleNavigation.bind(this));
        
        // Setup mutation observer for dynamic elements
        this.observer = new MutationObserver(this.handleDOMChanges.bind(this));
        this.observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'disabled', 'hidden', 'value']
        });
    }

    removeEventListeners() {
        document.removeEventListener('click', this.handleClick.bind(this), true);
        document.removeEventListener('input', this.handleInput.bind(this), true);
        document.removeEventListener('change', this.handleChange.bind(this), true);
        document.removeEventListener('submit', this.handleSubmit.bind(this), true);
        document.removeEventListener('keydown', this.handleKeyPress.bind(this), true);
        window.removeEventListener('popstate', this.handleNavigation.bind(this));
        if (this.observer) {
            this.observer.disconnect();
        }
    }

    handleClick(event) {
        if (!this.recording) return;
        
        const element = event.target;
        const selector = this.getSelector(element);
        
        if (selector && this.shouldRecordAction()) {
            // If clicking on a form element, record its current value
            if (element.form && ['input', 'select', 'textarea'].includes(element.tagName.toLowerCase())) {
                this.recordInputChange(element);
            }
            
            this.recordAction({
                type: 'click',
                selector: selector,
                text: element.textContent?.trim(),
                description: `Clicked on ${element.tagName.toLowerCase()}${element.id ? '#' + element.id : ''}`
            });
        }
    }

    handleInput(event) {
        if (!this.recording) return;
        
        const element = event.target;
        
        // Clear any existing timeout for this element
        if (this.inputBuffer.has(element)) {
            clearTimeout(this.inputBuffer.get(element));
        }
        
        // Set a new timeout to record the input change
        this.inputBuffer.set(element, setTimeout(() => {
            this.recordInputChange(element);
            this.inputBuffer.delete(element);
        }, this.inputTimeout));
    }

    handleChange(event) {
        if (!this.recording) return;
        
        const element = event.target;
        
        // Clear any pending input timeout
        if (this.inputBuffer.has(element)) {
            clearTimeout(this.inputBuffer.get(element));
            this.inputBuffer.delete(element);
        }
        
        // Record the change immediately
        this.recordInputChange(element);
    }

    recordInputChange(element) {
        const selector = this.getSelector(element);
        if (!selector || !this.shouldRecordAction()) return;
        
        let value = '';
        if (element.type === 'checkbox' || element.type === 'radio') {
            value = element.checked;
        } else if (element.type === 'password') {
            // For security, don't record actual password values
            value = '*'.repeat(element.value.length);
        } else {
            value = element.value;
        }
        
        this.recordAction({
            type: 'input',
            selector: selector,
            value: value,
            inputType: element.type || 'text',
            description: `Entered ${element.type === 'password' ? 'password' : 'text'} in ${element.tagName.toLowerCase()}${element.id ? '#' + element.id : ''}`
        });
    }

    handleSubmit(event) {
        if (!this.recording) return;
        
        const form = event.target;
        const selector = this.getSelector(form);
        
        if (selector && this.shouldRecordAction()) {
            // Record any pending input changes before form submission
            form.querySelectorAll('input, select, textarea').forEach(element => {
                if (this.inputBuffer.has(element)) {
                    clearTimeout(this.inputBuffer.get(element));
                    this.recordInputChange(element);
                }
            });
            
            this.recordAction({
                type: 'submit',
                selector: selector,
                description: `Submitted form${form.id ? ' #' + form.id : ''}`
            });
        }
    }

    handleKeyPress(event) {
        if (!this.recording) return;
        
        // Record special keys and Enter key on inputs
        const specialKeys = ['Enter', 'Tab', 'Escape'];
        const element = event.target;
        
        if (specialKeys.includes(event.key) && this.shouldRecordAction()) {
            if (event.key === 'Enter' && element.tagName.toLowerCase() === 'input') {
                // Record the input value before handling Enter
                this.recordInputChange(element);
            }
            
            this.recordAction({
                type: 'keypress',
                key: event.key,
                description: `Pressed ${event.key} key`
            });
        }
    }

    handleNavigation(event) {
        if (!this.recording) return;
        
        if (this.shouldRecordAction()) {
            this.recordAction({
                type: 'navigate',
                url: window.location.href,
                description: `Navigated to ${window.location.href}`
            });
        }
    }

    handleDOMChanges(mutations) {
        if (!this.recording) return;
        
        let hasRelevantChanges = false;
        for (const mutation of mutations) {
            if (mutation.type === 'childList' && mutation.addedNodes.length) {
                hasRelevantChanges = true;
                break;
            }
            if (mutation.type === 'attributes') {
                const relevantAttributes = ['class', 'style', 'disabled', 'hidden', 'value'];
                if (relevantAttributes.includes(mutation.attributeName)) {
                    hasRelevantChanges = true;
                    break;
                }
            }
        }
        
        if (hasRelevantChanges && this.shouldRecordAction()) {
            this.recordAction({
                type: 'dom_change',
                description: 'Page content was updated'
            });
        }
    }

    getSelector(element) {
        if (!element) return null;
        
        // Try ID first
        if (element.id) {
            return `#${element.id}`;
        }
        
        // Try name attribute
        if (element.name) {
            return `[name="${element.name}"]`;
        }
        
        // Try data attributes
        const dataAttrs = Array.from(element.attributes)
            .filter(attr => attr.name.startsWith('data-'));
        if (dataAttrs.length > 0) {
            return `[${dataAttrs[0].name}="${dataAttrs[0].value}"]`;
        }
        
        // Try type and name combination for inputs
        if (element.type && element.name) {
            return `input[type="${element.type}"][name="${element.name}"]`;
        }
        
        // Try classes
        if (element.className) {
            const classes = Array.from(element.classList)
                .filter(cls => !cls.includes(' '))
                .join('.');
            if (classes) {
                const similar = document.querySelectorAll('.' + classes);
                if (similar.length === 1) {
                    return `.${classes}`;
                }
            }
        }
        
        // Try parent context with nth-child
        let path = [];
        let current = element;
        
        while (current && current !== document.body) {
            let selector = current.tagName.toLowerCase();
            let parent = current.parentElement;
            
            if (parent) {
                let children = Array.from(parent.children);
                let index = children.filter(child => child.tagName === current.tagName).indexOf(current);
                if (index > 0) {
                    selector += `:nth-of-type(${index + 1})`;
                }
            }
            
            path.unshift(selector);
            current = parent;
        }
        
        return path.join(' > ');
    }

    shouldRecordAction() {
        const now = Date.now();
        if (!this.lastActionTime || (now - this.lastActionTime) >= this.minimumDelay) {
            this.lastActionTime = now;
            return true;
        }
        return false;
    }

    recordAction(action) {
        // Add timestamp and clean up action object
        action.timestamp = new Date().toISOString();
        
        // Store action locally
        this.actions.push(action);
        
        // Send action to server
        fetch('/api/record/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(action)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to record action');
            }
            return response.json();
        })
        .then(data => {
            if (data.status !== 'success') {
                console.error('Failed to record action:', data.message);
            }
        })
        .catch(error => {
            console.error('Failed to record action:', error);
        });
    }
}

// Export for use in other files
window.BrowserRecorder = BrowserRecorder;

function runTestCase(testCaseId) {
    // Show confirmation dialog
    if (confirm('Are you sure you want to run this test case?')) {
        // Show loading indicator if it exists
        const loadingToast = document.getElementById('loadingToast');
        if (loadingToast) {
            const toast = new bootstrap.Toast(loadingToast);
            toast.show();
        }
        
        // Call API to run the test
        fetch(`/api/test-case/${testCaseId}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Show success message
                alert('Test execution started successfully!');
                // Redirect to test run detail page if available
                if (data.test_run_id) {
                    window.location.href = `/test-run/${data.test_run_id}`;
                }
            } else {
                alert(`Error running test: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while running the test.');
        })
        .finally(() => {
            // Hide loading indicator if it exists
            if (loadingToast) {
                const toast = bootstrap.Toast.getInstance(loadingToast);
                if (toast) {
                    toast.hide();
                }
            }
        });
    }
}

function deleteTestCase(testCaseId) {
    // Show confirmation dialog
    if (confirm('Are you sure you want to delete this test case? This action cannot be undone.')) {
        fetch(`/test-case/${testCaseId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                // Reload the page to show updated list
                window.location.reload();
            } else {
                response.json().then(data => {
                    alert(`Failed to delete test case: ${data.error || 'Unknown error'}`);
                }).catch(() => {
                    alert('Failed to delete test case.');
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while deleting the test case.');
        });
    }
}

// Make these functions globally available
window.runTestCase = runTestCase;
window.deleteTestCase = deleteTestCase;
