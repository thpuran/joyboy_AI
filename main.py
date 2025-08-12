#!/usr/bin/env python3
"""
goethe_bot.py
Automate booking flow on goethe.de with a configurable start delay.

Usage:
python3 goethe_bot.py --delay 30 --country "India" --level "B1" \
--gecko /path/to/geckodriver --headless False \
--email you@example.com --password yourpass

Notes:

You will probably need to tweak some XPATH selectors if the site layout changes.

Uses Firefox (geckodriver). Make sure geckodriver matches your Firefox.
"""


import time
import argparse
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

-------------------------

Helper utilities

-------------------------

options = Options()
options.add_argument("--headless")  # Optional: Run in headless mode

service = Service(executable_path="/usr/local/bin/geckodriver")

driver = webdriver.Firefox(service=service, options=options)

def accept_all_cookies(driver):
print("[INFO] Attempting to accept cookies")
xpath_accept_all = "//button[contains(normalize-space(.),'Accept All')]"
el = wait_and_click(driver, xpath_accept_all, timeout=6)
if el:
print("[OK] Accepted cookies")
return True
else:
print("[WARN] 'Accept All' button not found")
return False

def open_examinations_tab(driver):
print("[INFO] Clicking Exams tab")
xpath_tab = "//a[contains(normalize-space(.),'Exams')]"
el = wait_and_click(driver, xpath_tab, timeout=6)
if el:
print("[OK] Clicked Exams tab")
return True
else:
print("[WARN] Could not find Exams tab/button")
return False

def wait_and_click(driver, xpath, timeout=15, scroll_into_view=True):
try:
el = WebDriverWait(driver, timeout).until(
EC.element_to_be_clickable((By.XPATH, xpath))
)
if scroll_into_view:
driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
el.click()
return el
except (TimeoutException, ElementClickInterceptedException) as e:
print(f"[WARN] Could not click element by xpath: {xpath} -> {e}")
return None

def wait_and_find(driver, xpath, timeout=15):
try:
el = WebDriverWait(driver, timeout).until(
EC.presence_of_element_located((By.XPATH, xpath))
)
return el
except TimeoutException:
print(f"[WARN] Element not found: {xpath}")
return None

def safe_sleep(seconds):
for i in range(seconds):
time.sleep(1)

-------------------------

Flow functions

-------------------------

def open_home(driver, lang_url=None):
url = lang_url or "https://www.goethe.de/en/index.html"
print(f"[INFO] Opening {url}")
driver.get(url)

def accept_all_cookies(driver):
print("[INFO] Attempting to accept cookies")
xpath_accept_all = "//button[contains(normalize-space(.),'Accept All')]"
el = wait_and_click(driver, xpath_accept_all, timeout=6)
if el:
print("[OK] Accepted cookies")
return True
else:
print("[WARN] 'Accept All' button not found")
return False

def open_examinations_tab(driver):
# Try to click tab labelled 'Examinations' in header box shown in screenshots
# This xpath searches for an element containing the word "Examinations"
xpath_tab = "//a[contains(normalize-space(.),'Exams') or //*[contains(normalize-space(.),'Examinations')]]"
el = wait_and_click(driver, "//a[contains(normalize-space(.),'Exams')]", timeout=10)
if not el:
# fallback: search for green tab text inside page
el = wait_and_click(driver, "//div[contains(@class,'tabs') or contains(@class,'tab')]//a[contains(normalize-space(.),'Exams')]", timeout=7)
if el:
print("[OK] Opened Examinations tab")
else:
print("[WARN] Couldn't find Examinations tab — you may need to update the xpath.")

def select_country(driver, country_name):
# Click the country dropdown
# The visible box "Search country/region" is likely a button/input; try typical patterns
print(f"[INFO] Opening country selector to choose: {country_name}")
# Try input/placeholder
xpath_dropdown = "//label[contains(.,'Search country')]/following::div[1] | //input[@placeholder[contains(.,'Search country')]] | //div[contains(.,'Search country/region')]"
dd = wait_and_click(driver, "//div[contains(normalize-space(.),'Search country') or contains(normalize-space(.),'Search country/region') or contains(normalize-space(.),'Search country/region')]", timeout=10)
if not dd:
# fallback: find any clickable element that looks like a select
dd = wait_and_click(driver, "//div[contains(@class,'select')][1]", timeout=6)
if not dd:
print("[WARN] Could not open country dropdown. Check xpath.")
return False

time.sleep(0.6)  
# Now find the country item in the list (the list appears as <li> or <div>). We'll match text.  
# The modal list may render a list of countries; try to click the exact text.  
country_xpath = f"//li[normalize-space(.)='{country_name}'] | //div[@role='option' and normalize-space(.)='{country_name}'] | //button[normalize-space(.)='{country_name}'] | //span[normalize-space(.)='{country_name}']"  
el_country = wait_and_click(driver, country_xpath, timeout=12)  
if el_country:  
    print(f"[OK] Selected country: {country_name}")  
    return True  
else:  
    print("[WARN] Country list item not found. You may need to scroll the list or adjust xpath.")  
    return False

def select_exam_level(driver, level_text):
# Find and click the exam card (e.g., "Goethe Certificate B1")
print(f"[INFO] Selecting exam level: {level_text}")
# look for card title containing the level text
xpath_card = f"//h3[contains(normalize-space(.),'{level_text}')] | //h2[contains(normalize-space(.),'{level_text}')] | //a[contains(normalize-space(.),'Goethe Certificate {level_text}') or contains(normalize-space(.),'{level_text}')]"
el = wait_and_click(driver, xpath_card, timeout=12)
if el:
print("[OK] Clicked exam card")
return True
else:
print("[WARN] Could not click exam card. Try updating xpath_card.")
return False

def click_select_modules(driver):
print("[INFO] Clicking 'Select modules' button")
xpath = "//button[contains(normalize-space(.),'Select modules') or contains(normalize-space(.),'SELECT MODULES') or //*[contains(normalize-space(.),'Select modules')]]"
el = wait_and_click(driver, "//button[contains(normalize-space(.),'Select modules')] | //a[contains(normalize-space(.),'Select modules')] | //div[contains(normalize-space(.),'Select modules')]", timeout=12)
if el:
print("[OK] Select modules clicked")
return True
else:
print("[WARN] 'Select modules' not found — update the xpath.")
return False

def pick_available_modules(driver, module_names=None):
"""
Try to pick modules that are available.
If module_names is None => selects any module checkbox that is clickable (first available).
"""
print("[INFO] Selecting available modules")
# look for checkboxes or elements with 'Only a few places left!' (orange text) or clickable checkbox
# generic xpath for checkbox inputs or check buttons within module listings:
xpath_checkboxes = "//input[@type='checkbox' and not(@disabled)] | //label[contains(@class,'checkbox') and not(contains(@class,'disabled'))] | //div[contains(@class,'module')]//button[contains(.,'Select') or contains(.,'Choose')]"
try:
candidates = driver.find_elements(By.XPATH, xpath_checkboxes)
if not candidates:
# try another fallback: look for elements with headphone icon "HEAR" that are selectable
candidates = driver.find_elements(By.XPATH, "//div[contains(.,'HEAR') or contains(.,'TO READ') or contains(.,'WRITE') or contains(.,'SPEAK')]/..//input[@type='checkbox']")
except Exception as e:
print(f"[WARN] error locating module checkboxes: {e}")
candidates = []

if not candidates:  
    print("[WARN] No module check elements found automatically. You may need to inspect DOM and provide explicit xpath.")  
    return False  

# If module_names provided, try to match text nearby  
selected = 0  
for el in candidates:  
    try:  
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)  
        if not el.is_selected():  
            el.click()  
        selected += 1  
        print(f"[OK] selected candidate #{selected}")  
        # break after selecting one (for single-module booking) or continue  
        # If user wants multiple modules, remove the break  
        break  
    except Exception as e:  
        print(f"[WARN] failed to click candidate: {e}")  
        continue  

return selected > 0

def click_further(driver):
print("[INFO] Clicking 'Further' or proceed button")
xpath = "//button[contains(normalize-space(.),'Further') or contains(normalize-space(.),'Proceed') or contains(normalize-space(.),'Continue') or //*[contains(normalize-space(.),'Further')]]"
el = wait_and_click(driver, "//button[contains(.,'Further')] | //button[contains(.,'Continue')] | //a[contains(.,'Further')]", timeout=10)
if el:
print("[OK] Clicked further")
return True
else:
print("[WARN] 'Further' button not found. Update xpath.")
return False

def choose_book_for(driver, book_for_me=True):
print("[INFO] Choosing booking type: " + ("Book for me" if book_for_me else "Book for my child"))
if book_for_me:
xpath = "//button[contains(normalize-space(.),'Book for me')] | //a[contains(normalize-space(.),'Book for me')]"
else:
xpath = "//button[contains(normalize-space(.),'Book for my child')] | //a[contains(normalize-space(.),'Book for my child')]"
el = wait_and_click(driver, xpath, timeout=10)
return bool(el)

def login_if_needed(driver, email=None, password=None):
if not email or not password:
print("[INFO] No login credentials provided. Skipping login.")
return
# Try to find email / password inputs and submit
el_email = wait_and_find(driver, "//input[@type='email' or contains(@name,'email') or contains(@placeholder,'Email')]", timeout=8)
if el_email:
el_email.clear()
el_email.send_keys(email)
el_pass = wait_and_find(driver, "//input[@type='password' or contains(@name,'password') or contains(@placeholder,'Password')]", timeout=8)
if el_pass:
el_pass.clear()
el_pass.send_keys(password)

# find a login/submit button  
btn = wait_and_click(driver, "//button[contains(normalize-space(.),'Login') or contains(normalize-space(.),'Sign in') or contains(.,'Anmelden')]", timeout=8)  
if btn:  
    print("[OK] Submitted login")  
else:  
    print("[WARN] Login button not found; you may need to submit manually or adjust xpath.")

-------------------------

Main

-------------------------

def main(args):
print(f"[INFO] Starting automation with start delay {args.delay} seconds.")
# Configurable countdown before the script runs
for remaining in range(args.delay, 0, -1):
print(f"Starting in {remaining} seconds...", end="\r")
time.sleep(1)
print("\n[INFO] Starting browser now.")

options = Options()  
if args.headless:  
    options.add_argument("--headless")  
options.add_argument("--no-sandbox")  
options.add_argument("--disable-gpu")  
service = Service(args.gecko) if args.gecko else Service()  

driver = webdriver.Firefox(service=service, options=options)  
driver.maximize_window()  

try:  
    open_home(driver, lang_url=args.start_url)  
    time.sleep(1.5)  

    open_examinations_tab(driver)  
    time.sleep(1.5)  

    ok = select_country(driver, args.country)  
    time.sleep(0.8)  
    if not ok:  
        print("[WARN] Country selection step failed. You may still proceed if the site already defaults to your country.")  

    time.sleep(1.2)  
    ok = select_exam_level(driver, args.level)  
    if not ok:  
        print("[WARN] exam selection failed. Trying to scroll and retry.")  
        driver.execute_script("window.scrollBy(0,400);")  
        time.sleep(1)  
        ok = select_exam_level(driver, args.level)  
        if not ok:  
            print("[ERROR] Could not select exam. Exiting.")  
            return  

    time.sleep(1.2)  
    if not click_select_modules(driver):  
        print("[ERROR] Could not open modules. Exiting.")  
        return  

    time.sleep(1.0)  
    pick_available_modules(driver)  

    time.sleep(0.8)  
    click_further(driver)  
    time.sleep(1.0)  
    choose_book_for(driver, book_for_me=True)  
    time.sleep(1.0)  
    login_if_needed(driver, email=args.email, password=args.password)  

    print("[DONE] Flow attempted. Inspect browser for results / complete any manual steps (captcha, additional forms).")  

finally:  
    if args.keep_open:  
        print("[INFO] keep_open set -> leaving browser open for inspection.")  
    else:  
        print("[INFO] Closing browser in 6 seconds...")  
        time.sleep(6)  
        driver.quit()

if name == "main":
parser = argparse.ArgumentParser(description="Goethe booking automation")
parser.add_argument("--delay", type=int, default=10, help="Seconds to wait before starting the flow")
parser.add_argument("--country", type=str, default="India", help="Country name to select in the dropdown")
parser.add_argument("--level", type=str, default="B1", help="Exam level to select (e.g., B1)")
parser.add_argument("--gecko", type=str, default="", help="Path to geckodriver binary (leave empty if in PATH)")
parser.add_argument("--headless", type=lambda x: (str(x).lower() == "true"), default=False, help="Run in headless mode (True/False)")
parser.add_argument("--email", type=str, default="", help="Login email (optional)")
parser.add_argument("--password", type=str, default="", help="Login password (optional)")
parser.add_argument("--start_url", type=str, default="https://www.goethe.de/en/index.html", help="Starting URL")
parser.add_argument("--keep_open", action="store_true", help="Leave browser open after script completes")
args = parser.parse_args()
main(args)
i want website for run this tool create best design you have and i want this code for back end and make the python code really work

