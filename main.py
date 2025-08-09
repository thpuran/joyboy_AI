import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

Firefox headless mode (optional)

options = Options()

options.add_argument("--headless")  # Uncomment if you don't want browser UI

Start Firefox browser

driver = webdriver.Firefox(options=options)

STEP 1: Open Goethe homepage

driver.get("https://www.goethe.de/en/index.html")
print("✅ Opened Goethe homepage.")
time.sleep(2)

STEP 2: Accept cookies

try:
accept = driver.find_element(By.XPATH, "//button[contains(text(),'Accept All')]")
accept.click()
print("✅ Accepted cookies.")
except:
print("⚠️ Cookie accept button not found.")
time.sleep(2)

STEP 3: Go to exams page

driver.get("https://www.goethe.de/ins/in/en/spr/prf.html")
print("✅ Navigated to Exams page.")
time.sleep(2)

try:
country_dropdown = Select(driver.find_element(By.ID, "countryFilter"))
country_dropdown.select_by_visible_text("India")
print("✅ Country selected: India")
except:
print("❌ Could not select country")
time.sleep(2)

STEP 4: Go to B1 exam

driver.get("https://www.goethe.de/ins/in/en/spr/prf/gzb1.cfm")
print("✅ Opened B1 Exam page.")
time.sleep(2)

STEP 5: Click DETAILS for the first available date

try:
details = driver.find_element(By.XPATH, "//a[contains(text(),'DETAILS')]")
details.click()
print("✅ Clicked on DETAILS.")
except:
print("⚠️ DETAILS button not found.")
time.sleep(2)

STEP 6: Click SELECT MODULES

try:
select_modules = driver.find_element(By.XPATH, "//a[contains(text(),'SELECT MODULES')]")
select_modules.click()
print("✅ Clicked SELECT MODULES.")
except:
print("⚠️ SELECT MODULES not found.")
time.sleep(2)

STEP 7: Click BOOK FOR MYSELF

try:
book_button = driver.find_element(By.XPATH, "//button[contains(text(),'BOOK FOR MYSELF')]")
book_button.click()
print("✅ Clicked BOOK FOR MYSELF.")
except:
print("⚠️ BOOK FOR MYSELF button not found.")
time.sleep(2)

STEP 8: Login form – enter credentials

try:
email_input = driver.find_element(By.ID, "username")
password_input = driver.find_element(By.ID, "password")

email_input.send_keys("ebin98807@gmail.com")       # <-- Replace with your email  
password_input.send_keys("your_password")             # <-- Replace with your password  

login_btn = driver.find_element(By.ID, "login-button")  
login_btn.click()  
print("✅ Login submitted.")

except:
print("⚠️ Login form not found.")
time.sleep(2)

print("🎉 Automation complete. Closing browser.")
driver.quit()
