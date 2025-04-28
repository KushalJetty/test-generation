import csv
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.webdriver.chrome.options import Options

# Store test results
test_results = []

def log_result(step, result, error_msg=""):
    current_url = driver.current_url
    test_results.append([step, result, current_url, error_msg])
    print(f"{step}: {result} | URL: {current_url} {error_msg}")

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://test.teamstreamz.com/")
wait = WebDriverWait(driver, 15)

# **Login Section**
try:
    username_input = wait.until(EC.presence_of_element_located((By.ID, "Username")))
    password_input = wait.until(EC.presence_of_element_located((By.ID, "Password")))
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'SIGN IN')]")))
    username_input.send_keys("abhishek@teamstreamz.com")
    password_input.send_keys("Test@123")
    login_button.click()
    log_result("Login attempted", "PASS")
    time.sleep(5)
except Exception as e:
    log_result("Login failed", "FAIL", str(e))

# **Navigate from Dashboard to Activities Page**
try:
    activities_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Activities")))
    activities_link.click()
    log_result("Navigated to Activities section", "PASS")
    time.sleep(5)
except Exception as e:
    log_result("Failed to navigate to Activities section", "FAIL", str(e))

# **Navigate from Activities Page to Clone Activity Page**
try:
    clone_activity_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, ".//span[@title='Clone Activity']/img"))
    )
    clone_activity_button.click()
    log_result("Navigated to Clone Activity page", "PASS")
    time.sleep(5)

    # Locate the input field for the activity title and modify it
    title_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Activity Title']")))
    title_input.clear()
    title_input.send_keys("Test Clone")
    log_result("Changed the title to 'Test Clone'", "PASS")
    time.sleep(2)

    # Click the 'Next' button to proceed
    next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'NEXT')]")))
    next_button.click()
    log_result("Clicked 'Next' button to proceed", "PASS")
    time.sleep(3)

    # **Click the final 'CLONE' button**
    clone_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'CLONE')]")))
    clone_button.click()
    log_result("Clicked 'CLONE' button to finalize cloning", "PASS")
    time.sleep(3)

except Exception as e:
    log_result("Failed to complete cloning activity", "FAIL", str(e))

# **Save results to CSV**
timestamp = datetime.now().strftime("%Y-%m-%d")
filename = f"test_report_clone_{timestamp}.csv"
file_counter = 1
while os.path.exists(filename):
    filename = f"test_report_clone_{timestamp}_{file_counter}.csv"
    file_counter += 1

with open(filename, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Test Step", "Result", "URL", "Error Message"])
    writer.writerows(test_results)

print(f"✅ CSV Report saved as {filename}")
