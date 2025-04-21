import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class TestRecorded_20250417_110334(unittest.TestCase):

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
            element.send_keys('ab')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abh')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhi')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhis')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhish')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishe')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@t')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@te')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@tea')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@team')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teams')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamst')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstr')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstre')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstrea')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstream')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstreamz')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstreamz.')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstreamz.c')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstreamz.co')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Username
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Username')))
            element.clear()
            element.send_keys('abhishek@teamstreamz.com')
            time.sleep(0.5)  # Wait for typing to complete
            # Press Tab key
            active_element = self.driver.switch_to.active_element
            active_element.send_keys(Keys.TAB)
            time.sleep(0.5)  # Wait for key press
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('T')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Te')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Tes')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Test')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Test@')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Test@1')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Test@12')
            time.sleep(0.5)  # Wait for typing to complete
            # Input text into #Password
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#Password')))
            element.clear()
            element.send_keys('Test@123')
            time.sleep(0.5)  # Wait for typing to complete
            # Click on element app-root > app-login > div > div:nth-of-type(3) > div:nth-of-type(2) > form > div:nth-of-type(3) > button
            element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'app-root > app-login > div > div:nth-of-type(3) > div:nth-of-type(2) > form > div:nth-of-type(3) > button')))
            element.click()
            time.sleep(1)  # Wait for action to complete
            # Submit form app-root > app-login > div > div:nth-of-type(3) > div:nth-of-type(2) > form
            form = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'app-root > app-login > div > div:nth-of-type(3) > div:nth-of-type(2) > form')))
            form.submit()
            time.sleep(2)  # Wait for form submission

        finally:
            # Close the browser
            self.driver.quit()

    def tearDown(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

if __name__ == '__main__':
    unittest.main()