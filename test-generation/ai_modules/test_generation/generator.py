import requests
from bs4 import BeautifulSoup

class TestGenerator:
    def __init__(self):
        pass
        
    def generate_from_url(self, url, test_types=None):
        """Generate test cases from a URL"""
        if test_types is None:
            test_types = ['functional', 'ui']
            
        # Fetch the page content
        try:
            response = requests.get(url)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")
            
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Generate tests based on the page content
        tests = {}
        
        if 'functional' in test_types:
            tests['functional'] = self._generate_functional_tests(soup, url)
            
        if 'ui' in test_types:
            tests['ui'] = self._generate_ui_tests(soup, url)
            
        return tests
        
    def _generate_functional_tests(self, soup, url):
        """Generate functional tests based on the page content"""
        tests = []
        
        # Find forms
        forms = soup.find_all('form')
        for form in forms:
            test = {
                'name': f"Test form submission: {form.get('id', 'unnamed')}",
                'description': f"Test submitting the form {form.get('id', 'unnamed')}",
                'steps': [
                    {'action': 'navigate', 'url': url},
                    {'action': 'fill_form', 'form_selector': self._get_selector(form)},
                    {'action': 'submit_form', 'form_selector': self._get_selector(form)},
                    {'action': 'assert', 'type': 'success_message'}
                ]
            }
            tests.append(test)
            
        # Find links
        links = soup.find_all('a')
        for link in links:
            href = link.get('href')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                test = {
                    'name': f"Test navigation: {link.text.strip() or 'unnamed'}",
                    'description': f"Test clicking on link '{link.text.strip() or href}'",
                    'steps': [
                        {'action': 'navigate', 'url': url},
                        {'action': 'click', 'selector': self._get_selector(link)},
                        {'action': 'assert', 'type': 'page_loaded'}
                    ]
                }
                tests.append(test)
                
        return tests
        
    def _generate_ui_tests(self, soup, url):
        """Generate UI tests based on the page content"""
        tests = []
        
        # Test responsive layout
        test = {
            'name': "Test responsive layout",
            'description': "Test that the page layout is responsive",
            'steps': [
                {'action': 'navigate', 'url': url},
                {'action': 'resize', 'width': 1920, 'height': 1080},
                {'action': 'assert', 'type': 'no_horizontal_scroll'},
                {'action': 'resize', 'width': 768, 'height': 1024},
                {'action': 'assert', 'type': 'no_horizontal_scroll'},
                {'action': 'resize', 'width': 375, 'height': 667},
                {'action': 'assert', 'type': 'no_horizontal_scroll'}
            ]
        }
        tests.append(test)
        
        # Test images
        images = soup.find_all('img')
        if images:
            test = {
                'name': "Test images loaded",
                'description': "Test that all images are loaded correctly",
                'steps': [
                    {'action': 'navigate', 'url': url},
                    {'action': 'assert', 'type': 'images_loaded', 'selectors': [self._get_selector(img) for img in images]}
                ]
            }
            tests.append(test)
            
            # Test for accessibility - check for alt text on images
            if images:
                test = {
                    'name': "Test image accessibility",
                    'description': "Test that all images have alt text",
                    'steps': [
                        {'action': 'navigate', 'url': url},
                        {'action': 'assert', 'type': 'images_have_alt', 'selectors': [self._get_selector(img) for img in images]}
                    ]
                }
                tests.append(test)
            
            # Test for color contrast
            test = {
                'name': "Test color contrast",
                'description': "Test that text has sufficient color contrast with its background",
                'steps': [
                    {'action': 'navigate', 'url': url},
                    {'action': 'assert', 'type': 'color_contrast'}
                ]
            }
            tests.append(test)
            
            # Test for keyboard navigation
            test = {
                'name': "Test keyboard navigation",
                'description': "Test that the page can be navigated using keyboard",
                'steps': [
                    {'action': 'navigate', 'url': url},
                    {'action': 'press_key', 'key': 'Tab'},
                    {'action': 'assert', 'type': 'element_focused'},
                    {'action': 'press_key', 'key': 'Tab'},
                    {'action': 'assert', 'type': 'element_focused'},
                    {'action': 'press_key', 'key': 'Enter'},
                    {'action': 'assert', 'type': 'action_performed'}
                ]
            }
            tests.append(test)
            
            return tests
        
        def _get_selector(self, element):
            """Generate a CSS selector for a given element"""
            if element.get('id'):
                return f"#{element['id']}"
            
            if element.get('class'):
                classes = ' '.join(element['class'])
                if classes:
                    return f"{element.name}.{'.'.join(element['class'])}"
            
            # Try with other attributes
            if element.get('name'):
                return f"{element.name}[name='{element['name']}']"
                
            if element.get('href'):
                return f"{element.name}[href='{element['href']}']"
                
            if element.get('src'):
                return f"{element.name}[src='{element['src']}']"
            
            # Fallback to a more complex selector
            parent = element.parent
            if parent:
                siblings = parent.find_all(element.name, recursive=False)
                if len(siblings) > 1:
                    index = siblings.index(element)
                    return f"{element.name}:nth-child({index + 1})"
            
            return element.name
        
        def generate_selenium_test(self, test_data):
            """Generate a Selenium test script from test data"""
            test_name = test_data.get('name', 'GeneratedTest').replace(' ', '')
            test_code = f"""import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time

class {test_name}(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def test_main(self):
        driver = self.driver
        wait = self.wait
"""
            # Add test steps with proper indentation
            for step in test_data.get('steps', []):
                if step['action'] == 'navigate':
                    test_code += f"        driver.get('{step['url']}')\n"
                elif step['action'] == 'click':
                    test_code += f"        element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '{step['selector']}')))\n"
                    test_code += "        element.click()\n"
                elif step['action'] == 'input':
                    test_code += f"        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{step['selector']}')))\n"
                    test_code += "        element.clear()\n"
                    test_code += f"        element.send_keys('{step['value']}')\n"
                elif step['action'] == 'assert':
                    if step['type'] == 'page_loaded':
                        test_code += "        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))\n"
                    elif step['type'] == 'success_message':
                        test_code += "        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.alert-success')))\n"
            
            # Add tearDown method
            test_code += """
    def tearDown(self):
        self.driver.quit()
        
if __name__ == "__main__":
    unittest.main()
"""
            return test_code