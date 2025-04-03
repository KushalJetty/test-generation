// Recorder for browser actions
class BrowserRecorder {
    constructor() {
        this.recording = false;
        this.actions = [];
        this.serverUrl = window.location.origin;
    }

    start() {
        this.recording = true;
        this.actions = [];
        this.attachEventListeners();
        
        // Record initial page load
        this.recordAction({
            type: 'navigate',
            url: window.location.href,
            timestamp: Date.now()
        });
    }

    stop() {
        this.recording = false;
        this.removeEventListeners();
        return this.actions;
    }

    recordAction(action) {
        if (this.recording) {
            this.actions.push(action);
            
            // Send action to server
            fetch(`${this.serverUrl}/api/record/action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(action)
            }).then(response => response.json())
            .then(data => {
                // Update UI with new action
                this.updateUI(action);
            });
        }
    }

    updateUI(action) {
        const testCasesList = document.getElementById('testCasesList');
        if (!testCasesList) return;

        // Create step element
        const stepElement = document.createElement('div');
        stepElement.className = 'step-item animate__animated animate__fadeIn';
        
        // Format action description
        let description = '';
        switch (action.type) {
            case 'click':
                description = `Click on element: ${action.selector}`;
                break;
            case 'input':
                description = `Type text "${action.value}" into: ${action.selector}`;
                break;
            case 'select':
                description = `Select option "${action.value}" in: ${action.selector}`;
                break;
            case 'navigate':
                description = `Navigate to: ${action.url}`;
                break;
            case 'keypress':
                description = `Press key: ${action.key}`;
                break;
            case 'hover':
                description = `Hover over: ${action.selector}`;
                break;
            case 'scroll':
                description = `Scroll to position: ${action.position}`;
                break;
            case 'submit':
                description = `Submit form: ${action.selector}`;
                break;
        }

        stepElement.innerHTML = `<small>${this.actions.length}. ${description}</small>`;
        testCasesList.appendChild(stepElement);
    }

    attachEventListeners() {
        // Record clicks
        document.addEventListener('click', this.handleClick.bind(this), true);
        
        // Record form inputs
        document.addEventListener('input', this.handleInput.bind(this), true);
        
        // Record form submissions
        document.addEventListener('submit', this.handleSubmit.bind(this), true);
        
        // Record navigation
        window.addEventListener('popstate', this.handleNavigation.bind(this));
        
        // Record key presses
        document.addEventListener('keydown', this.handleKeyPress.bind(this), true);
        
        // Record hover events
        document.addEventListener('mouseover', this.handleHover.bind(this), true);
        
        // Record scroll events
        document.addEventListener('scroll', this.debounce(this.handleScroll.bind(this), 500), true);
        
        // Record select changes
        document.addEventListener('change', this.handleSelect.bind(this), true);
    }

    removeEventListeners() {
        document.removeEventListener('click', this.handleClick.bind(this), true);
        document.removeEventListener('input', this.handleInput.bind(this), true);
        document.removeEventListener('submit', this.handleSubmit.bind(this), true);
        window.removeEventListener('popstate', this.handleNavigation.bind(this));
        document.removeEventListener('keydown', this.handleKeyPress.bind(this), true);
        document.removeEventListener('mouseover', this.handleHover.bind(this), true);
        document.removeEventListener('scroll', this.handleScroll.bind(this), true);
        document.removeEventListener('change', this.handleSelect.bind(this), true);
    }

    handleClick(event) {
        const element = event.target;
        const selector = this.getSelector(element);
        
        this.recordAction({
            type: 'click',
            selector: selector,
            text: element.textContent?.trim(),
            timestamp: Date.now()
        });
    }

    handleInput(event) {
        const element = event.target;
        const selector = this.getSelector(element);
        
        // Don't record password inputs
        if (element.type === 'password') {
            this.recordAction({
                type: 'input',
                selector: selector,
                value: '********',
                timestamp: Date.now()
            });
        } else {
            this.recordAction({
                type: 'input',
                selector: selector,
                value: element.value,
                timestamp: Date.now()
            });
        }
    }

    handleSelect(event) {
        const element = event.target;
        if (element.tagName.toLowerCase() === 'select') {
            const selector = this.getSelector(element);
            const selectedOption = element.options[element.selectedIndex];
            
            this.recordAction({
                type: 'select',
                selector: selector,
                value: selectedOption.text,
                timestamp: Date.now()
            });
        }
    }

    handleSubmit(event) {
        const form = event.target;
        const selector = this.getSelector(form);
        
        this.recordAction({
            type: 'submit',
            selector: selector,
            timestamp: Date.now()
        });
    }

    handleNavigation(event) {
        this.recordAction({
            type: 'navigate',
            url: window.location.href,
            timestamp: Date.now()
        });
    }

    handleKeyPress(event) {
        // Only record special keys
        if (event.key.length > 1) {
            this.recordAction({
                type: 'keypress',
                key: event.key,
                timestamp: Date.now()
            });
        }
    }

    handleHover(event) {
        // Debounce hover events to avoid too many recordings
        if (!this.lastHoverTime || Date.now() - this.lastHoverTime > 1000) {
            const element = event.target;
            const selector = this.getSelector(element);
            
            this.recordAction({
                type: 'hover',
                selector: selector,
                timestamp: Date.now()
            });
            
            this.lastHoverTime = Date.now();
        }
    }

    handleScroll(event) {
        const element = event.target;
        if (element === document) {
            this.recordAction({
                type: 'scroll',
                position: {
                    x: window.scrollX,
                    y: window.scrollY
                },
                timestamp: Date.now()
            });
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    getSelector(element) {
        if (element.id) {
            return `#${element.id}`;
        }
        
        if (element.name) {
            return `[name="${element.name}"]`;
        }
        
        if (element.className && typeof element.className === 'string') {
            const classes = element.className.split(' ')
                .filter(c => c)
                .join('.');
            if (classes) {
                return `.${classes}`;
            }
        }
        
        // Try to get a unique selector
        let selector = element.tagName.toLowerCase();
        const parent = element.parentElement;
        
        if (parent) {
            const siblings = Array.from(parent.children)
                .filter(e => e.tagName === element.tagName);
            if (siblings.length > 1) {
                const index = siblings.indexOf(element);
                selector += `:nth-of-type(${index + 1})`;
            }
        }
        
        return selector;
    }
}

// Initialize recorder
window.browserRecorder = new BrowserRecorder(); 