import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------------------
# Configure Firefox Driver
# ------------------------------
options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Firefox(options=options)
wait = WebDriverWait(driver, 20)

# ------------------------------
# Step 1: Open Exam Page
# ------------------------------
driver.get("https://www.goethe.de/ins/in/en/spr/prf.html")
time.sleep(2)

# ------------------------------
# Step 2: Accept Cookies
# ------------------------------
try:
    accept_cookies = wait.until(EC.element_to_be_clickable((By.ID, "gdpr-cookie-accept")))
    accept_cookies.click()
    print("✅ Cookies accepted.")
except:
    print("⚠️ Cookie accept button not found.")

# ------------------------------
# Step 3: Click B1 Exam
# ------------------------------
try:
    b1_exam = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "B1")))
    b1_exam.click()
    print("✅ B1 exam clicked.")
except:
    print("⚠️ B1 exam link not found.")
time.sleep(2)

# ------------------------------
# Step 4: Click on "Details"
# ------------------------------
try:
    details_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'DETAILS')]")))
    details_button.click()
    print("✅ Details button clicked.")
except:
    print("⚠️ Details button not found.")
time.sleep(2)

# ------------------------------
# Step 5: Click "Select Modules"
# ------------------------------
try:
    select_modules = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'SELECT MODULES')]")))
    select_modules.click()
    print("✅ Select Modules clicked.")
except:
    print("⚠️ Select Modules not found.")
time.sleep(2)

# ------------------------------
# Step 6: Click "Book for Myself"
# ------------------------------
try:
    book_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Book for myself')]")))
    book_btn.click()
    print("✅ Book for Myself clicked.")
except:
    print("⚠️ Book for Myself button not found.")
time.sleep(2)

# ------------------------------
# Step 7: Login Page - Fill Email & Password
# ------------------------------
try:
    email_input = wait.until(EC.presence_of_element_located((By.ID, "login_email")))
    password_input = driver.find_element(By.ID, "login_password")
    
    email_input.send_keys("your-email@example.com")  # Replace with your email
    password_input.send_keys("your-password")        # Replace with your password
    
    print("✅ Credentials entered.")
    
    # Click Login
    login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_btn.click()
    print("✅ Login button clicked.")
except:
    print("⚠️ Login inputs or button not found.")

# ------------------------------
# Done
# ------------------------------
time.sleep(5)
driver.quit()
