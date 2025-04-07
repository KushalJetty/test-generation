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