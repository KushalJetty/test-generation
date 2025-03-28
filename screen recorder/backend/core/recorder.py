import time
import os
import webbrowser
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager

class SeleniumRecorder:
    def __init__(self):
        self.driver = None
        self.actions = []
        self.recording = False
        
    def start_recording(self, url):
        try:
            # Enable performance logging with optimized settings
            caps = DesiredCapabilities.CHROME
            caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL'}
            
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Performance optimizations
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            
            # Reduce memory usage
            chrome_options.add_argument("--js-flags=--max-old-space-size=512")
            
            # Add CDP listener for DOM events
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Create the driver with explicit path to ChromeDriver
            driver_path = ChromeDriverManager().install()
            print(f"Using ChromeDriver at: {driver_path}")
            
            self.driver = webdriver.Chrome(
                service=Service(driver_path), 
                options=chrome_options
            )
            
            # Navigate to URL
            print(f"Navigating to URL: {url}")
            self.driver.get(url)
            self.actions = []
            self.add_action("navigate", url=url)
            
            # Inject JavaScript to capture user actions - optimize the script
            print("Injecting optimized recorder script")
            self.inject_optimized_recorder_script()
            
            # Open editor window in a separate thread
            threading.Thread(target=self.open_editor_window).start()
            
            self.recording = True
            return True
        except Exception as e:
            print(f"Error starting recording: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            self.recording = False
            raise Exception(f"Failed to start recording: {str(e)}")
    
    def inject_optimized_recorder_script(self):
        """Inject an optimized version of the recorder script"""
        script = """
        // Use more efficient event delegation
        document.addEventListener('click', function(e) {
            if (e.target.tagName) {
                window.sendRecorderEvent('click', e.target);
            }
        }, true);
        
        document.addEventListener('input', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                window.sendRecorderEvent('input', e.target);
            }
        }, true);
        
        // Throttle events for better performance
        window.sendRecorderEvent = (function() {
            let lastEvent = null;
            let timeout = null;
            
            return function(eventType, element) {
                if (timeout) {
                    clearTimeout(timeout);
                }
                
                lastEvent = {
                    type: eventType,
                    element: element
                };
                
                timeout = setTimeout(function() {
                    const data = {
                        type: lastEvent.type,
                        tagName: lastEvent.element.tagName,
                        id: lastEvent.element.id,
                        className: lastEvent.element.className,
                        name: lastEvent.element.name,
                        value: lastEvent.element.value,
                        innerText: lastEvent.element.innerText ? lastEvent.element.innerText.substring(0, 50) : '',
                        xpath: getXPath(lastEvent.element),
                        timestamp: new Date().getTime()
                    };
                    
                    fetch('/api/record-action', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    }).catch(err => console.error('Error recording action:', err));
                    
                    lastEvent = null;
                    timeout = null;
                }, 300); // Throttle to one event per 300ms
            };
        })();
        
        function getXPath(element) {
            // Optimized XPath generation
            if (element.id) {
                return '//*[@id="' + element.id + '"]';
            }
            
            // Use a more efficient approach for XPath
            const parts = [];
            while (element && element.nodeType === Node.ELEMENT_NODE) {
                let idx = 0;
                let sibling = element.previousSibling;
                while (sibling) {
                    if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === element.tagName) {
                        idx++;
                    }
                    sibling = sibling.previousSibling;
                }
                
                const tagName = element.tagName.toLowerCase();
                const position = idx > 0 ? `[${idx + 1}]` : '';
                parts.unshift(tagName + position);
                
                element = element.parentNode;
            }
            
            return '/' + parts.join('/');
        }
        """
        
        try:
            self.driver.execute_script(script)
        except Exception as e:
            print(f"Error injecting recorder script: {str(e)}")
    
    # Add the rest of the recorder methods here
    # ...