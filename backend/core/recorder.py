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
            # Enable performance logging
            caps = DesiredCapabilities.CHROME
            caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL'}
            
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
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
            
            # Inject JavaScript to capture user actions
            print("Injecting recorder script")
            self.inject_recorder_script()
            
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
    
    # Add the rest of the recorder methods here
    # ...