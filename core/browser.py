"""
================================================================================
BROWSER.PY - BROWSER SETUP & COOKIE MANAGEMENT
================================================================================
PURPOSE: Manage Chrome browser setup, initialization, and session persistence
         through cookies. Handles both local and CI/CD environments.

FEATURES:
  - Headless Chrome configuration for scraping
  - Cookie persistence for session reuse
  - Anti-detection measures (Selenium/webdriver hiding)
  - Cross-platform compatibility (Windows, Linux, GitHub Actions)
  - Automatic ChromeDriver detection
================================================================================
"""

import os
import pickle
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

try:
    from .config import (
        CHROMEDRIVER_PATH, COOKIE_FILE, PAGE_LOAD_TIMEOUT,
        IS_CI, SCRIPT_DIR
    )
    from .logger import log_msg, print_error, get_pkt_time
except ImportError:
    from core.config import (
        CHROMEDRIVER_PATH, COOKIE_FILE, PAGE_LOAD_TIMEOUT,
        IS_CI, SCRIPT_DIR
    )
    from core.logger import log_msg, print_error, get_pkt_time

# ==================== BROWSER SETUP ====================

def setup_browser():
    """
    PURPOSE: Initialize and configure a Chrome WebDriver instance with
             anti-detection measures and optimal settings for scraping.
    
    LOGIC:
      - Create Chrome options with headless mode
      - Add anti-detection arguments to avoid webdriver detection
      - Set up security and performance options
      - Initialize WebDriver with ChromeDriver
      - Set page load timeout
    
    RETURNS:
      WebDriver: Configured Chrome WebDriver instance, or None if failed
    """
    try:
        log_msg("[INFO] Setting up Chrome browser...")
        
        # Create Chrome options
        opts = Options()
        
        # Headless mode: run browser without GUI
        opts.add_argument("--headless=new")
        
        # Window size for consistent rendering
        opts.add_argument("--window-size=1920,1080")
        
        # Hide webdriver automation markers
        opts.add_argument("--disable-blink-features=AutomationControlled")
        
        # Remove automation indicators
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)
        
        # Security and stability options
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        
        # Suppress logging noise
        opts.add_argument("--log-level=3")
        
        # Initialize driver with service
        driver = None
        if CHROMEDRIVER_PATH and Path(CHROMEDRIVER_PATH).exists():
            log_msg(f"[INFO] Using ChromeDriver: {CHROMEDRIVER_PATH}")
            service = Service(executable_path=CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=opts)
        else:
            log_msg("[INFO] Using system ChromeDriver")
            driver = webdriver.Chrome(options=opts)
        
        # Set page load timeout
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Hide webdriver property via JavaScript
        driver.execute_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        
        log_msg("[OK] Browser initialized successfully")
        return driver
        
    except WebDriverException as e:
        print_error(f"WebDriver initialization failed: {e}")
        return None
    except Exception as e:
        print_error(f"Browser setup error: {e}")
        return None


# ==================== COOKIE MANAGEMENT ====================

def save_cookies(driver):
    """
    PURPOSE: Save browser cookies to a local pickle file for session persistence.
             Allows reusing login sessions across multiple runs.
    
    LOGIC:
      - Extract all cookies from WebDriver
      - Serialize to pickle file at COOKIE_FILE path
      - Handle errors gracefully (session loss if save fails)
    
    ARGS:
      driver (WebDriver): Active Chrome WebDriver instance
    
    RETURNS:
      bool: True if successful, False otherwise
    """
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, 'wb') as f:
            pickle.dump(cookies, f)
        log_msg(f"[OK] Cookies saved ({len(cookies)} items)")
        return True
    except Exception as e:
        log_msg(f"[ERROR] Failed to save cookies: {e}")
        return False


def load_cookies(driver):
    """
    PURPOSE: Load previously saved cookies into the browser to restore
             a previous login session. Avoids need for fresh login if valid.
    
    LOGIC:
      - Check if cookie file exists
      - Deserialize cookies from pickle file
      - Add each cookie to WebDriver
      - Handle errors gracefully
    
    ARGS:
      driver (WebDriver): Active Chrome WebDriver instance
    
    RETURNS:
      bool: True if cookies loaded successfully, False otherwise
    """
    try:
        cookie_path = Path(COOKIE_FILE)
        
        # Check if cookie file exists
        if not cookie_path.exists():
            log_msg("[INFO] No saved cookies found")
            return False
        
        # Load cookies from file
        with open(COOKIE_FILE, 'rb') as f:
            cookies = pickle.load(f)
        
        # Add each cookie to driver
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception:
                # Skip problematic cookies
                pass
        
        log_msg(f"[OK] Loaded cookies ({len(cookies)} items)")
        return True
        
    except Exception as e:
        log_msg(f"[ERROR] Failed to load cookies: {e}")
        return False


def clear_cookies():
    """
    PURPOSE: Delete saved cookie file to force fresh login on next run.
             Used when debugging login issues or switching accounts.
    
    LOGIC:
      - Delete cookie file if it exists
      - Handle errors gracefully
    
    RETURNS:
      bool: True if successful or file didn't exist, False on error
    """
    try:
        cookie_path = Path(COOKIE_FILE)
        if cookie_path.exists():
            cookie_path.unlink()
            log_msg("[OK] Cookies cleared")
            return True
        return True
    except Exception as e:
        log_msg(f"[ERROR] Failed to clear cookies: {e}")
        return False


# ==================== COOKIE VALIDATION ====================

def test_session_validity(driver):
    """
    PURPOSE: Test if current browser session (with loaded cookies) is still valid.
             Determines whether to use cached cookies or perform fresh login.
    
    LOGIC:
      - Navigate to home page
      - Check if login page appears (indicates expired session)
      - Return validity status
    
    ARGS:
      driver (WebDriver): Active Chrome WebDriver instance
    
    RETURNS:
      bool: True if session is valid, False if needs fresh login
    """
    try:
        HOME_URL = "https://damadam.pk/"
        
        log_msg("[INFO] Testing session validity...")
        driver.get(HOME_URL)
        time.sleep(2)
        
        # If still on login page, session is invalid
        if 'login' in driver.current_url.lower():
            log_msg("[INFO] Session expired, fresh login needed")
            return False
        
        log_msg("[OK] Session is valid")
        return True
        
    except Exception as e:
        log_msg(f"[ERROR] Session test failed: {e}")
        return False
