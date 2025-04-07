import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class TestRecorded_20250407_105307(unittest.TestCase):

    def setUp(self):
        # Initialize Chrome driver
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--start-maximized')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def test_recorded_actions(self):
        try:
            # Navigate to the initial URL
            self.driver.get('https://test.teamstreamz.com/')
            time.sleep(2)  # Wait for page to load

            # Click on element #Username
            element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#Username')))
            element.click()
            time.sleep(1)  # Wait for action to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('a')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('as')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('asf')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('asfs')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('asfsd')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('asfsdh')
            time.sleep(0.5)  # Wait for typing to complete

        finally:
            # Close the browser
            self.driver.quit()

    def tearDown(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

if __name__ == '__main__':
    unittest.main()