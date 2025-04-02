class BrowserActionRecorder {
    constructor() {
        this.recording = false;
        this.actions = [];
        this.observers = [];
    }

    start() {
        this.recording = true;
        this.actions = [];
        this.setupListeners();
    }

    stop() {
        this.recording = false;
        this.removeListeners();
        return this.actions;
    }

    setupListeners() {
        // Click events
        document.addEventListener('click', this.handleClick.bind(this), true);
        
        // Input events
        document.addEventListener('input', this.handleInput.bind(this), true);
        
        // Navigation events
        window.addEventListener('popstate', this.handleNavigation.bind(this));
        
        // Setup mutation observer for dynamic content
        const observer = new MutationObserver(this.handleMutation.bind(this));
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style']
        });
        this.observers.push(observer);
    }

    removeListeners() {
        document.removeEventListener('click', this.handleClick.bind(this), true);
        document.removeEventListener('input', this.handleInput.bind(this), true);
        window.removeEventListener('popstate', this.handleNavigation.bind(this));
        
        // Disconnect observers
        this.observers.forEach(observer => observer.disconnect());
        this.observers = [];
    }

    handleClick(event) {
        if (!this.recording) return;
        
        const selector = this.getSelector(event.target);
        if (selector) {
            const action = {
                type: 'click',
                selector: selector,
                timestamp: Date.now()
            };
            this.recordAction(action);
        }
    }

    handleInput(event) {
        if (!this.recording) return;
        
        const selector = this.getSelector(event.target);
        if (selector) {
            const action = {
                type: 'input',
                selector: selector,
                value: event.target.value,
                timestamp: Date.now()
            };
            this.recordAction(action);
        }
    }

    handleNavigation(event) {
        if (!this.recording) return;
        
        const action = {
            type: 'navigate',
            url: window.location.href,
            timestamp: Date.now()
        };
        this.recordAction(action);
    }

    handleMutation(mutations) {
        if (!this.recording) return;
        
        mutations.forEach(mutation => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const selector = this.getSelector(node);
                        if (selector) {
                            const action = {
                                type: 'mutation',
                                selector: selector,
                                timestamp: Date.now()
                            };
                            this.recordAction(action);
                        }
                    }
                });
            }
        });
    }

    getSelector(element) {
        if (!element || !element.tagName) return null;
        
        // Try to get a unique selector
        if (element.id) {
            return `#${element.id}`;
        }
        
        // Use classes if available
        if (element.className) {
            const classes = element.className.split(' ')
                .filter(c => c)
                .map(c => `.${c}`)
                .join('');
            if (classes) {
                const similar = document.querySelectorAll(classes);
                if (similar.length === 1) {
                    return classes;
                }
            }
        }
        
        // Fallback to a more specific selector
        let selector = element.tagName.toLowerCase();
        let parent = element.parentElement;
        let nth = Array.from(parent.children)
            .filter(e => e.tagName === element.tagName)
            .indexOf(element);
            
        if (nth > 0) {
            selector += `:nth-of-type(${nth + 1})`;
        }
        
        return selector;
    }

    recordAction(action) {
        this.actions.push(action);
        
        // Send action to server
        fetch('/api/record/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(action)
        });
    }
}

// Initialize recorder
window.browserRecorder = new BrowserActionRecorder(); 