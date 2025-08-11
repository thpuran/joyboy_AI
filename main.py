#!/usr/bin/env python3
"""
goethe_bot.py
Automate booking flow on goethe.de with a configurable start delay.

Usage:
    python3 goethe_bot.py --delay 30 --country "India" --level "B1" \
        --gecko /path/to/geckodriver --headless False \
        --email you@example.com --password yourpass
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

# -------------------------
# Helper utilities
# -------------------------
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

# -------------------------
# New additions based on screenshots
# -------------------------
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

# -------------------------
# Booking flow
# -------------------------
def open_home(driver, lang_url=None):
    url = lang_url or "https://www.goethe.de/en/index.html"
    print(f"[INFO] Opening {url}")
    driver.get(url)

def select_country(driver, country_name):
    print(f"[INFO] Selecting country: {country_name}")
    dd = wait_and_click(driver, "//div[contains(normalize-space(.),'Search country') or contains(normalize-space(.),'Search country/region')]", timeout=10)
    if not dd:
        print("[WARN] Could not open country dropdown.")
        return False

    time.sleep(0.6)
    country_xpath = f"//li[normalize-space(.)='{country_name}'] | //div[@role='option' and normalize-space(.)='{country_name}'] | //button[normalize-space(.)='{country_name}'] | //span[normalize-space(.)='{country_name}']"
    el_country = wait_and_click(driver, country_xpath, timeout=12)
    if el_country:
        print(f"[OK] Selected country: {country_name}")
        return True
    else:
        print("[WARN] Country not found in list.")
        return False

def select_exam_level(driver, level_text):
    print(f"[INFO] Selecting exam level: {level_text}")
    xpath_card = f"//h3[contains(normalize-space(.),'{level_text}')] | //h2[contains(normalize-space(.),'{level_text}')] | //a[contains(normalize-space(.),'{level_text}')]"
    el = wait_and_click(driver, xpath_card, timeout=12)
    if el:
        print("[OK] Clicked exam card")
        return True
    else:
        print("[WARN] Could not click exam card.")
        return False

def click_select_modules(driver):
    print("[INFO] Clicking 'Select modules'")
    xpath = "//button[contains(normalize-space(.),'Select modules')] | //a[contains(normalize-space(.),'Select modules')]"
    el = wait_and_click(driver, xpath, timeout=12)
    if el:
        print("[OK] Select modules clicked")
        return True
    else:
        print("[WARN] 'Select modules' not found.")
        return False

def pick_available_modules(driver, module_names=None):
    print("[INFO] Selecting available modules")
    xpath_checkboxes = "//input[@type='checkbox' and not(@disabled)]"
    try:
        candidates = driver.find_elements(By.XPATH, xpath_checkboxes)
    except Exception as e:
        print(f"[WARN] error locating module checkboxes: {e}")
        candidates = []

    if not candidates:
        print("[WARN] No modules available.")
        return False

    selected = 0
    for el in candidates:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            if not el.is_selected():
                el.click()
            selected += 1
            print(f"[OK] selected module #{selected}")
            break
        except Exception as e:
            print(f"[WARN] failed to click module: {e}")
            continue

    return selected > 0

def click_further(driver):
    print("[INFO] Clicking 'Further' or continue")
    xpath = "//button[contains(.,'Further')] | //button[contains(.,'Continue')]"
    el = wait_and_click(driver, xpath, timeout=10)
    if el:
        print("[OK] Clicked further")
        return True
    else:
        print("[WARN] 'Further' button not found.")
        return False

def choose_book_for(driver, book_for_me=True):
    print("[INFO] Choosing booking type")
    if book_for_me:
        xpath = "//button[contains(normalize-space(.),'Book for me')]"
    else:
        xpath = "//button[contains(normalize-space(.),'Book for my child')]"
    el = wait_and_click(driver, xpath, timeout=10)
    return bool(el)

def login_if_needed(driver, email=None, password=None):
    if not email or not password:
        print("[INFO] No login credentials provided. Skipping login.")
        return
    el_email = wait_and_find(driver, "//input[@type='email']", timeout=8)
    if el_email:
        el_email.clear()
        el_email.send_keys(email)
    el_pass = wait_and_find(driver, "//input[@type='password']", timeout=8)
    if el_pass:
        el_pass.clear()
        el_pass.send_keys(password)
    btn = wait_and_click(driver, "//button[contains(normalize-space(.),'Login')]", timeout=8)
    if btn:
        print("[OK] Submitted login")
    else:
        print("[WARN] Login button not found.")

# -------------------------
# Main
# -------------------------
def main(args):
    print(f"[INFO] Starting automation in {args.delay} seconds.")
    for remaining in range(args.delay, 0, -1):
        print(f"Starting in {remaining} seconds...", end="\r")
        time.sleep(1)
    print("\n[INFO] Launching browser...")

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

        accept_all_cookies(driver)
        time.sleep(1.0)

        open_examinations_tab(driver)
        time.sleep(1.5)

        if not select_country(driver, args.country):
            print("[WARN] Country selection failed. Proceeding anyway.")

        time.sleep(1.2)
        if not select_exam_level(driver, args.level):
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

        print("[DONE] Script completed. Please complete CAPTCHA or other manual steps if needed.")
    finally:
        if args.keep_open:
            print("[INFO] Keeping browser open.")
        else:
            print("[INFO] Closing browser in 6 seconds...")
            time.sleep(6)
            driver.quit()

if __name__ == "__main__":
    parser = argparse
    
