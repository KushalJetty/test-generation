import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class RecordedTest(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 10)

    def test_main(self):
        driver = self.driver
        wait = self.wait
        
        # Navigate to site
        driver.get('https://test.teamstreamz.com/')
        
        # Login process
        username = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#Username')))
        username.click()
        username.clear()
        username.send_keys('kushal.jetty@teamstreamz.com')  # Enter full username at once
        
        password = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#Password')))
        password.click()
        password.clear()
        password.send_keys('Test@123')  # Enter full password at once
        
        # Click login button
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button.btn.signin-btn.bg-primary.ng-tns-c813547932-0')
        )).click()
        
        # Navigation
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'a.list-group-item.inactive-link.ng-star-inserted')
        )).click()
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button.btn-ts.btn-ts-primary.ng-star-inserted')
        )).click()
        
        # Activity creation
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'div.activity-type.font-fourteen.mb-3.bg-light.rounded')
        )).click()
        
        # Form filling
        title_field = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'input.form-control.ng-untouched.ng-pristine.ng-valid')
        ))
        title_field.click()
        title_field.clear()
        title_field.send_keys('fekub')  # Enter full title at once
        
        desc_field = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'textarea.form-control.ng-untouched.ng-pristine.ng-valid')
        ))
        desc_field.clear()
        desc_field.send_keys('iuhkd')  # Enter full description at once
        
        # Dropdown selections
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'span.ng-arrow-wrapper')
        )).click()
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'span.ng-option-label.ng-star-inserted')
        )).click()
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'body:nth-child(2) > app-root:nth-child(1) > app-layout:nth-child(2) > section:nth-child(3) > app-create-activity-template:nth-child(4) > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(3) > ng-select:nth-child(2) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > input')
        )).click()
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '#a4e71ad968a2-1')
        )).click()
        
        # Checkbox and final steps
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'span.checkmark')
        )).click()
        
        on_field = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input.ng-untouched.ng-pristine.ng-valid')
        ))
        on_field.clear()
        on_field.send_keys('on')
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button.btn-ts.btn-ts-primary-outline.ng-star-inserted')
        )).click()
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'div.svc-page__add-new-question.svc-btn.ng-star-inserted')
        )).click()
        
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'span.svc-string-editor__input')
        )).click()

    def tearDown(self):
        self.driver.quit()


if __name__ == "__main__":
    unittest.main()