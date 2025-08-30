#!/usr/bin/env python3
"""
goethe_bot.py
Automates Goethe-Institut exam booking (India, B1, etc.).
Flow:
1. Open Exams page
2. Select country (India)
3. Select exam (B1)
4. Go through options/selection
5. Choose "Für mich buchen"
6. Login if credentials are given
"""

import time
import argparse
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -------------------------
# Helpers
# -------------------------
def wait_and_click(driver, xpath, timeout=15):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
        return el
    except (TimeoutException, ElementClickInterceptedException) as e:
        print(f"[WARN] Could not click {xpath} -> {e}")
        return None


def wait_and_find(driver, xpath, timeout=15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except TimeoutException:
        print(f"[WARN] Not found: {xpath}")
        return None


# -------------------------
# Flow functions
# -------------------------
def open_home(driver, url):
    print(f"[INFO] Opening {url}")
    driver.get(url)


def open_examinations_tab(driver):
    print("[INFO] Clicking Exams tab")
    xpath_tab = "//*[@id='tab-7391913-2']"
    el = wait_and_click(driver, xpath_tab, timeout=8)
    if el:
        print("[OK] Exams tab opened")
    else:
        print("[ERROR] Could not click Exams tab")


def select_country(driver, country_name):
    print(f"[INFO] Selecting country: {country_name}")
    input_box = wait_and_find(driver, "//input[@id='combobox-input-647526']", timeout=8)
    if not input_box:
        print("[ERROR] Country input not found")
        return False
    input_box.clear()
    input_box.send_keys(country_name)
    time.sleep(1)
    suggestion = wait_and_click(driver, f"//li[contains(.,'{country_name}')]", timeout=8)
    if suggestion:
        print(f"[OK] Country chosen: {country_name}")
        return True
    else:
        print("[WARN] No suggestion clicked")
        return False


def select_exam_level(driver, level_text="B1"):
    print(f"[INFO] Selecting exam level: {level_text}")
    xpath = f"//a[contains(.,'Goethe-Zertifikat {level_text}')]"
    el = wait_and_click(driver, xpath, timeout=10)
    if el:
        print(f"[OK] Selected exam {level_text}")
        return True
    else:
        print(f"[ERROR] Could not select {level_text}")
        return False


def click_further(driver):
    print("[INFO] Clicking Weiter (next)")
    xpath = "//button[contains(.,'weiter') or contains(.,'Weiter')]"
    el = wait_and_click(driver, xpath, timeout=10)
    if el:
        print("[OK] Weiter clicked")
        return True
    else:
        print("[ERROR] Weiter button not found")
        return False


def choose_book_for(driver):
    print("[INFO] Clicking 'Für mich buchen'")
    xpath = "//button[contains(.,'Für mich buchen')]"
    el = wait_and_click(driver, xpath, timeout=10)
    if el:
        print("[OK] Selected 'Für mich buchen'")
        return True
    else:
        print("[ERROR] 'Für mich buchen' button not found")
        return False


def login_if_needed(driver, email, password):
    if not email or not password:
        print("[INFO] No credentials, skipping login")
        return
    el_email = wait_and_find(driver, "//input[@type='email']", timeout=8)
    el_pass = wait_and_find(driver, "//input[@type='password']", timeout=8)
    if el_email:
        el_email.clear()
        el_email.send_keys(email)
    if el_pass:
        el_pass.clear()
        el_pass.send_keys(password)
    wait_and_click(driver, "//button[contains(.,'Login') or contains(.,'Anmelden')]", timeout=8)
    print("[OK] Login submitted")


# -------------------------
# Main Flow
# -------------------------
def main(args):
    options = Options()
    if args.headless:
        options.add_argument("--headless")

    service = Service(args.gecko) if args.gecko else Service()
    driver = webdriver.Firefox(service=service, options=options)
    driver.maximize_window()

    try:
        # Start from main exams page
        open_home(driver, "https://www.goethe.de/ins/in/de/spr/prf.html")
        time.sleep(2)

        open_examinations_tab(driver)
        time.sleep(2)

        select_country(driver, args.country)
        time.sleep(2)

        select_exam_level(driver, args.level)
        time.sleep(2)

        # This will land on exam B1 page
        click_further(driver)
        time.sleep(2)

        # Options page
        open_home(driver, "https://www.goethe.de/coe/options?6")
        time.sleep(2)

        # Selection page
        open_home(driver, "https://www.goethe.de/coe/selection?7")
        time.sleep(2)

        # Booking type
        choose_book_for(driver)
        time.sleep(2)

        # Login page
        open_home(driver, "https://login.goethe.de/cas/login")
        login_if_needed(driver, args.email, args.password)

        print("[DONE] Flow completed")

    finally:
        if args.keep_open:
            print("[INFO] Browser kept open")
        else:
            print("[INFO] Closing browser in 6 seconds...")
            time.sleep(6)
            driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Goethe booking automation")
    parser.add_argument("--country", type=str, default="India", help="Country to select")
    parser.add_argument("--level", type=str, default="B1", help="Exam level (e.g., B1)")
    parser.add_argument("--gecko", type=str, default="", help="Path to geckodriver binary")
    parser.add_argument("--headless", type=lambda x: (str(x).lower() == "true"), default=False)
    parser.add_argument("--email", type=str, default="", help="Login email (optional)")
    parser.add_argument("--password", type=str, default="", help="Login password (optional)")
    parser.add_argument("--keep_open", action="store_true")
    args = parser.parse_args()
    main(args)
