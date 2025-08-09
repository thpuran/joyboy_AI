from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time

# Firefox options
options = Options()
options.add_argument("--headless")  # Optional: run without opening browser window

# Start driver
driver = webdriver.Firefox(options=options)

# STEP 1: Open Goethe website
driver.get("https://www.goethe.de/en/index.html")
time.sleep(3)

# STEP 2: Accept cookies
try:
    accept_button = driver.find_element(By.XPATH, "//button[contains(text(),'Accept All')]")
    accept_button.click()
    print("[✔] Cookies accepted.")
except:
    print("[!] Cookie popup not found.")

# STEP 3: Click on “Exams”
driver.get("https://www.goethe.de/ins/in/en/spr/prf.html")
time.sleep(2)

# STEP 4: Select B1 Exam
driver.get("https://www.goethe.de/ins/in/en/spr/prf/gzb1.cfm")
time.sleep(2)

# STEP 5: Click on ‘Details’ of a date
try:
    details_button = driver.find_element(By.XPATH, "//a[contains(text(),'DETAILS')]")
    details_button.click()
    print("[✔] Exam date selected.")
except:
    print("[!] Couldn't click on details button.")

time.sleep(3)

# STEP 6: Click "Select Modules"
try:
    select_modules = driver.find_element(By.XPATH, "//a[contains(text(),'SELECT MODULES')]")
    select_modules.click()
    print("[✔] Proceeded to module selection.")
except:
    print("[!] SELECT MODULES not found.")

# STEP 7: Click "Book for myself"
time.sleep(2)
try:
    book_button = driver.find_element(By.XPATH, "//button[contains(text(),'BOOK FOR MYSELF')]")
    book_button.click()
except:
    print("[!] BOOK FOR MYSELF not found.")

# STEP 8: Enter login credentials
time.sleep(3)
try:
    email_input = driver.find_element(By.ID, "username")
    password_input = driver.find_element(By.ID, "password")

    email_input.send_keys("your_email@example.com")
    password_input.send_keys("your_password")

    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    print("[✔] Login submitted.")
except:
    print("[!] Login page not loaded properly.")

# Done
time.sleep(5)
driver.quit()
print("✅ Automation complete.")
