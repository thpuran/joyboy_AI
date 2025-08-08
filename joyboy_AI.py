#!/usr/bin/env python3
"""
ai_webbot.py
Offline self-learning web automation assistant.
Uses Selenium (Firefox) + SQLite. No external APIs.

How it works (quick):
1. User inputs a website URL and a natural-language task.
2. System parses the task into an ordered list of actions.
3. It tries to find an existing saved script in the DB for the same task.
   - If found, asks to reuse or regenerate.
   - If not found or regenerate requested, it generates a new Python automation script string from the action plan.
4. It executes the generated script (in same process), logs success/failure, and stores it for future reuse.
"""

import sqlite3
import re
import os
import sys
import time
import datetime
import traceback
from typing import List, Dict, Tuple

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DB_PATH = os.path.join(os.path.dirname(__file__), "ai_webbot.db")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "generated_scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)
service = Service(executable_path="C:\\Users\\Admin\\Downloads\\geckodriver-v0.36.0-win-aarch64\\geckodriver.exe")
# --- Database helpers ----------------------------------------------------
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_text TEXT UNIQUE,
            script_path TEXT,
            script_text TEXT,
            last_used TEXT,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0
        );
    """)
    con.commit()
    return con

# --- Simple NLP parser ---------------------------------------------------
# This is purposely small and rule-based. You can extend rules as needed.
ACTION_KEYWORDS = {
    "open": ["open", "go to", "visit", "navigate"],
    "click": ["click", "press", "tap", "select"],
    "type": ["type", "enter", "fill", "write"],
    "select": ["select", "choose"],
    "wait": ["wait", "pause", "sleep", "hold"],
    "login": ["login", "log in", "sign in"],
    "submit": ["submit", "send", "confirm"],
    "pick_date": ["date", "pick", "choose date", "select date"],
}

def find_action_verb(sentence: str) -> Tuple[str, str]:
    """
    Determine primary action and return (action, remainder)
    """
    s = sentence.lower()
    for action, kw_list in ACTION_KEYWORDS.items():
        for kw in kw_list:
            if kw in s:
                # split at keyword occurrence
                idx = s.find(kw)
                # return original-case remainder for better element text extraction
                remainder = sentence[idx + len(kw):].strip()
                return (action, remainder)
    return ("unknown", sentence)

def simple_plan_from_task(task_text: str, base_url: str) -> List[Dict]:
    """
    Convert a free-text task into a list of action dicts.
    Each action dict: {"action": "open|click|type|select|wait|submit", "target": "...", "value": "..."}
    This is heuristic-based. For more accuracy, add more patterns.
    """
    plan = []
    # Step 0: always open base URL (if provided)
    if base_url:
        plan.append({"action": "open", "target": base_url, "value": None})

    # Split into sentence-like chunks using common separators
    chunks = re.split(r'[,.;]+|\band\b|\bthen\b|\bafter\b', task_text)
    for raw in chunks:
        s = raw.strip()
        if not s:
            continue
        act, rem = find_action_verb(s)
        # heuristics per action
        if act == "open":
            # maybe includes a URL
            url_match = re.search(r'(https?://\S+)|www\.\S+', s)
            if url_match:
                plan.append({"action": "open", "target": url_match.group(0), "value": None})
            else:
                # open homepage already added; ignore
                pass
        elif act == "click":
            # Try to extract clickable label in quotes or after 'click'
            label = extract_label(rem) or extract_label(s) or rem.strip()
            plan.append({"action": "click", "target": label, "value": None})
        elif act == "type":
            # match "type 'text' into username" or "enter email abc@d.com"
            value = extract_quoted(rem) or extract_email(rem) or guess_value_from_sentence(s)
            target = guess_target_from_sentence(s, rem)
            if value:
                plan.append({"action": "type", "target": target, "value": value})
            else:
                plan.append({"action": "type", "target": target, "value": rem.strip()})
        elif act == "select":
            option = extract_label(rem) or rem.strip()
            target = guess_target_from_sentence(s, rem)
            plan.append({"action": "select", "target": target, "value": option})
        elif act == "pick_date":
            # try to find a date
            date_val = find_date_in_text(s)
            target = guess_target_from_sentence(s, rem)
            plan.append({"action": "pick_date", "target": target, "value": date_val})
        elif act == "wait":
            secs = extract_number(rem) or 2
            plan.append({"action": "wait", "target": None, "value": int(secs)})
        elif act == "submit" or act == "login":
            plan.append({"action": "submit", "target": None, "value": None})
        else:
            # fallback: if token contains '@' probably an email -> type
            if '@' in s:
                plan.append({"action": "type", "target": "email", "value": extract_email(s)})
            else:
                # store as click if looks short, else type
                if len(s.split()) <= 4:
                    plan.append({"action": "click", "target": s.strip(), "value": None})
                else:
                    plan.append({"action": "type", "target": None, "value": s.strip()})
    # compress consecutive opens
    cleaned = []
    for a in plan:
        if cleaned and a["action"] == "open" and cleaned[-1]["action"] == "open":
            continue
        cleaned.append(a)
    return cleaned

# small helper extractors
def extract_quoted(s: str) -> str:
    m = re.search(r'["\'](.+?)["\']', s)
    return m.group(1).strip() if m else None

def extract_label(s: str) -> str:
    # common pattern: label "Register" or label Register
    q = extract_quoted(s)
    if q:
        return q
    m = re.search(r'(["\']?)([A-Za-z0-9 ._-]{2,80})\1', s)
    if m:
        return m.group(2).strip()
    return None

def extract_email(s: str) -> str:
    m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', s)
    return m.group(0) if m else None

def extract_number(s: str) -> int:
    m = re.search(r'(\d+)', s)
    return int(m.group(1)) if m else None

def guess_value_from_sentence(sentence: str) -> str:
    # look for the last token in sentence which may be the value
    parts = sentence.strip().split()
    if not parts:
        return ""
    return parts[-1].strip()

def guess_target_from_sentence(sentence: str, remainder: str) -> str:
    # simple heuristics: if 'username' in text -> username, 'password' -> password
    s = sentence.lower() + " " + remainder.lower()
    for name in ("username", "user", "email", "password", "search", "country", "exam", "date"):
        if name in s:
            return name
    # fallback to remainder short text
    if remainder and len(remainder.split()) <= 4:
        return remainder.strip()
    return None

def find_date_in_text(s: str):
    # try common patterns dd/mm/yyyy or dd-mm-yyyy or month names
    m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', s)
    if m:
        return m.group(1)
    # month name like "August 21 2025" or "21 August"
    m2 = re.search(r'(\d{1,2}\s+[A-Za-z]{3,9}\s*\d{0,4})', s)
    if m2:
        return m2.group(1).strip()
    return None

# --- Script generation ---------------------------------------------------
def generate_script_from_plan(plan: List[Dict], script_name: str) -> str:
    """
    Build a Python script (as string) that performs the plan using Selenium.
    The script will define a helper 'find_element_fuzzy(driver, descriptor)' to heuristically locate elements.
    """
    lines = []
    lines.append("from selenium import webdriver")
    lines.append("from selenium.webdriver.common.by import By")
    lines.append("from selenium.webdriver.support.ui import Select")
    lines.append("import time")
    lines.append("")
    lines.append("def find_element_fuzzy(driver, descriptor):")
    lines.append("    # descriptor can be id, name, visible text, css selector or xpath fragment")
    lines.append("    if not descriptor:")
    lines.append("        return None")
    lines.append("    d = descriptor.strip()")
    lines.append("    # try several common locators")
    lines.append("    tries = []")
    lines.append("    try:")
    lines.append("        # by id")
    lines.append("        tries.append(driver.find_element(By.ID, d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    try:")
    lines.append("        tries.append(driver.find_element(By.NAME, d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    try:")
    lines.append("        tries.append(driver.find_element(By.LINK_TEXT, d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    try:")
    lines.append("        # partial link text fallback")
    lines.append("        tries.append(driver.find_element(By.PARTIAL_LINK_TEXT, d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    try:")
    lines.append("        tries.append(driver.find_element(By.XPATH, \"//*[text()=\\\"%s\\\"]\" % d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    try:")
    lines.append("        tries.append(driver.find_element(By.XPATH, \"//*[contains(text(), '%s')]\" % d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    try:")
    lines.append("        tries.append(driver.find_element(By.CSS_SELECTOR, d))")
    lines.append("    except Exception:")
    lines.append("        pass")
    lines.append("    if tries:")
    lines.append("        return tries[0]")
    lines.append("    return None")
    lines.append("")
    lines.append("def run_plan(driver):")
    lines.append("    ok = True")
    for step in plan:
        a = step["action"]
        t = step.get("target")
        v = step.get("value")
        if a == "open":
            lines.append(f"    driver.get(r'''{t}''')  # open")
            lines.append("    time.sleep(2)")
        elif a == "click":
            lines.append(f"    el = find_element_fuzzy(driver, r'''{t or ''}''')")
            lines.append("    if el:")
            lines.append("        try: el.click(); time.sleep(1)")
            lines.append("        except Exception: pass")
            lines.append("    else:")
            lines.append(f"        print('Could not find element to click: {t}')")
        elif a == "type":
            sval = v or ""
            lines.append(f"    el = find_element_fuzzy(driver, r'''{t or ''}''')")
            lines.append("    if el:")
            lines.append(f"        try: el.clear(); el.send_keys(r'''{sval}'''); time.sleep(0.8)")
            lines.append("        except Exception: pass")
            lines.append("    else:")
            lines.append(f"        print('Could not find element to type into: {t}. Trying to search inputs and use first.')")
            lines.append("        try:")
            lines.append("            inputs = driver.find_elements(By.TAG_NAME, 'input')")
            lines.append("            if inputs: inputs[0].send_keys(r'''%s''')" % sval)
            lines.append("        except Exception: pass")
        elif a == "select":
            opt = v or ""
            lines.append(f"    el = find_element_fuzzy(driver, r'''{t or ''}''')")
            lines.append("    if el:")
            lines.append("        try:")
            lines.append("            sel = Select(el)")
            lines.append("            sel.select_by_visible_text(r'''%s''')" % opt)
            lines.append("        except Exception:")
            lines.append("            try: el.click(); time.sleep(0.5)  # fallback")
            lines.append("            except Exception: pass")
            lines.append("    else:")
            lines.append("        # Try to select option by visible text anywhere")
            lines.append("        try:")
            lines.append("            opt_el = driver.find_element(By.XPATH, \"//option[contains(normalize-space(.), '%s')]\")" % opt)
            lines.append("            opt_el.click()")
            lines.append("        except Exception: pass")
        elif a == "pick_date":
            date_val = v or ""
            lines.append(f"    el = find_element_fuzzy(driver, r'''{t or ''}''')")
            lines.append("    if el:")
            lines.append(f"        try: el.send_keys(r'''{date_val}'''); time.sleep(0.5) except Exception: pass")
        elif a == "wait":
            lines.append(f"    time.sleep({int(v or 2)})")
        elif a == "submit":
            lines.append("    try:")
            lines.append("        forms = driver.find_elements(By.TAG_NAME, 'form')")
            lines.append("        if forms: forms[0].submit(); time.sleep(1)")
            lines.append("    except Exception: pass")
        else:
            # fallback: print
            lines.append(f"    print('Unknown action {a} for step target {t} value {v}')")
    lines.append("    return ok")
    # Driver creation wrapper for standalone script
    script = "\n".join(lines)
    # Add main guard for standalone run (so user can run saved scripts individually)
    script += """

if __name__ == '__main__':
    from selenium.webdriver.firefox.options import Options
    opts = Options()
    # opts.add_argument('--headless')  # uncomment to run headless
    driver = webdriver.Firefox(options=opts)
    try:
        ok = run_plan(driver)
        print('Done, ok=', ok)
    except Exception as e:
        print('Error during run:', e)
    finally:
        driver.quit()
"""
    return script

# --- Execution / storage / run-time engine --------------------------------
def save_script_to_db(con, task_text, script_text):
    cur = con.cursor()
    file_name = f"script_{int(time.time())}.py"
    path = os.path.join(SCRIPTS_DIR, file_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(script_text)
    now = datetime.datetime.utcnow().isoformat()
    try:
        cur.execute("INSERT OR REPLACE INTO tasks (task_text, script_path, script_text, last_used, success_count, fail_count) VALUES (?, ?, ?, ?, COALESCE((SELECT success_count FROM tasks WHERE task_text=?), 0), COALESCE((SELECT fail_count FROM tasks WHERE task_text=?), 0))",
                    (task_text, path, script_text, now, task_text, task_text))
        con.commit()
    except Exception as e:
        print("DB save error:", e)

def load_script_from_db(con, task_text):
    cur = con.cursor()
    cur.execute("SELECT id, script_path, script_text, last_used, success_count, fail_count FROM tasks WHERE task_text=? LIMIT 1", (task_text,))
    row = cur.fetchone()
    return row

def update_task_stats(con, task_text, success: bool):
    cur = con.cursor()
    col = "success_count" if success else "fail_count"
    cur.execute(f"UPDATE tasks SET {col} = {col} + 1, last_used = ? WHERE task_text = ?", (datetime.datetime.utcnow().isoformat(), task_text))
    con.commit()

def execute_script_text(script_text: str, headless=False, timeout_per_step=20):
    """
    Execute a generated script string in a controlled namespace.
    We'll create a Firefox driver here and call the run_plan function defined in the script.
    This avoids subprocess and keeps DB interactions in single process.
    """
    # build a namespace
    ns = {}
    # we'll provide selenium objects to the script env
    try:
        # compile and exec the script
        compiled = compile(script_text, "<generated>", "exec")
        exec(compiled, ns)
        # after exec, a function run_plan(driver) should be present
        if "run_plan" not in ns:
            print("Generated script has no run_plan function.")
            return False
    except Exception:
        print("Failed to compile/exec generated script:")
        traceback.print_exc()
        return False

    # create driver and run
    opts = Options()
    if headless:
        opts.add_argument("--headless")
    driver = webdriver.Firefox(options=opts)
    try:
        ok = ns["run_plan"](driver)
        success = bool(ok)
    except Exception:
        print("Error while running plan:")
        traceback.print_exc()
        success = False
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return success

# --- CLI interaction ------------------------------------------------------
def main_loop():
    print("=== AI WebBot (offline self-learning) ===")
    print("Requirements: Python, Selenium, geckodriver in PATH, Firefox.")
    print("Type 'exit' to quit.")
    con = init_db()
    while True:
        base_url = input("\nEnter base website URL (or blank to skip): ").strip()
        if base_url.lower() in ("exit", "quit"):
            print("Bye.")
            break
        task = input("Describe the task you want automated (plain English): ").strip()
        if not task:
            print("Please enter a non-empty task.")
            continue
        if task.lower() in ("exit", "quit"):
            print("Bye.")
            break

        # check DB for exact same task
        existing = load_script_from_db(con, task)
        if existing:
            print("Found a previously saved script for this exact task.")
            _id, path, script_text, last_used, sc, fc = existing
            print(f"Saved script: {path}  last used: {last_used}  successes: {sc}  fails: {fc}")
            ans = input("Use saved script? (y/N) or [r]egenerate: ").strip().lower()
            if ans == "y":
                print("Executing saved script...")
                ok = execute_script_text(script_text)
                update_task_stats(con, task, ok)
                print("Success" if ok else "Failed")
                continue
            elif ans == "r":
                print("Regenerating script from your task.")
            else:
                print("Regenerating script.")
        # build plan
        plan = simple_plan_from_task(task, base_url)
        print("Generated plan (heuristic):")
        for i, s in enumerate(plan, 1):
            print(f"  {i}. {s}")
        # generate script
        script_text = generate_script_from_plan(plan, "temp")
        # show preview option
        show = input("Show generated script preview? (Y/n): ").strip().lower()
        if show != "n":
            print("\n--- GENERATED SCRIPT PREVIEW (top 200 lines) ---")
            for i, line in enumerate(script_text.splitlines()):
                if i >= 200:
                    print("... (truncated)")
                    break
                print(line)
            print("--- end preview ---\n")

        run_now = input("Execute this automation now? (Y/n): ").strip().lower()
        if run_now == "n":
            save = input("Save generated script for future reuse? (Y/n): ").strip().lower()
            if save != "n":
                save_script_to_db(con, task, script_text)
                print("Saved.")
            else:
                print("Not saved.")
            continue

        # execute
        print("Running the generated script in a controlled environment (creates Firefox window).")
        headless = input("Run headless? (y/N): ").strip().lower() == "y"
        ok = execute_script_text(script_text, headless=headless)
        update_task_stats(con, task, ok)
        if ok:
            print("Execution finished successfully.")
            save_script_to_db(con, task, script_text)
            print("Script saved to DB for future reuse.")
        else:
            print("Execution failed. You can inspect the script and re-run after edits.")
            save_choice = input("Save this failed script for debugging? (y/N): ").strip().lower()
            if save_choice == "y":
                save_script_to_db(con, task, script_text)
                print("Saved.")
        # small pause
        time.sleep(0.5)

if __name__ == '__main__':
    main_loop()
