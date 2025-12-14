"""
================================================================================
AUTH.PY - LOGIN & AUTHENTICATION
================================================================================
PURPOSE: Handle DamaDam login process with multiple account support.
         Manages cookie-based session restoration and fresh login flow.

FEATURES:
  - Cookie-based login (prefer cached sessions)
  - Fallback to manual login with credentials
  - Multiple account support (primary + secondary)
  - Session persistence and recovery
  - Cross-environment support (local + CI/CD)
================================================================================
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from .config import (
        LOGIN_URL, HOME_URL,
        DAMADAM_USERNAME, DAMADAM_PASSWORD,
        DAMADAM_USERNAME_2, DAMADAM_PASSWORD_2
    )
    from .logger import log_msg, print_error, get_timestamp_short
    from .browser import save_cookies, load_cookies, test_session_validity
except ImportError:
    from core.config import (
        LOGIN_URL, HOME_URL,
        DAMADAM_USERNAME, DAMADAM_PASSWORD,
        DAMADAM_USERNAME_2, DAMADAM_PASSWORD_2
    )
    from core.logger import log_msg, print_error, get_timestamp_short
    from core.browser import save_cookies, load_cookies, test_session_validity

# ==================== LOGIN ORCHESTRATION ====================

def authenticate(driver):
    """
    PURPOSE: Main authentication orchestration function.
             Attempts login in this priority order:
             1. Load cached cookies
             2. Test if session is still valid
             3. Perform fresh login with credentials
    
    LOGIC:
      - First check if we have saved cookies from previous session
      - If cookies exist, test if they still grant access
      - If cookies invalid or don't exist, do fresh login
      - Save new cookies after successful login
    
    ARGS:
      driver (WebDriver): Initialized Chrome WebDriver instance
    
    RETURNS:
      bool: True if authentication succeeded, False otherwise
    """
    log_msg("[LOGIN] Starting authentication process...")
    
    # Step 1: Try loading cached cookies
    if load_cookies(driver):
        # Step 2: Test if cached session is still valid
        if test_session_validity(driver):
            log_msg("[LOGIN] [OK] Authenticated using cached cookies")
            return True
        else:
            log_msg("[LOGIN] Cached cookies expired, performing fresh login...")
    
    # Step 3: Perform fresh login with credentials
    if perform_login(driver):
        save_cookies(driver)
        log_msg("[LOGIN] [OK] Fresh login successful, cookies saved")
        return True
    
    print_error("Authentication failed - check credentials and try again")
    return False


# ==================== CREDENTIAL-BASED LOGIN ====================

def perform_login(driver):
    """
    PURPOSE: Execute DamaDam login form with stored credentials.
             Supports multiple accounts (primary + secondary fallback).
    
    LOGIC:
      - Navigate to login page
      - Wait for login form to load
      - Try primary account credentials
      - If primary fails, try secondary account (if configured)
      - Verify successful login by checking URL
    
    ARGS:
      driver (WebDriver): Initialized Chrome WebDriver instance
    
    RETURNS:
      bool: True if login successful, False otherwise
    """
    try:
        log_msg("[LOGIN] Navigating to login page...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        # Try both accounts: primary and secondary
        accounts = [
            ("Primary", DAMADAM_USERNAME, DAMADAM_PASSWORD),
            ("Secondary", DAMADAM_USERNAME_2, DAMADAM_PASSWORD_2)
        ]
        
        for account_name, username, password in accounts:
            # Skip if credentials not provided
            if not username or not password:
                continue
            
            log_msg(f"[LOGIN] Attempting login with {account_name} account...")
            
            # Attempt login
            if _try_account_login(driver, username, password):
                log_msg(f"[LOGIN] [OK] {account_name} account login successful")
                return True
            else:
                log_msg(f"[LOGIN] {account_name} account login failed, trying next...")
        
        print_error("All login attempts failed")
        return False
        
    except Exception as e:
        print_error(f"Login process error: {e}")
        return False


def _try_account_login(driver, username: str, password: str):
    """
    PURPOSE: Attempt login with a single set of credentials.
    
    LOGIC:
      - Wait for login form elements to appear
      - Fill username and password fields
      - Submit form
      - Wait for redirect away from login page
      - Verify we're no longer on login page
    
    ARGS:
      driver (WebDriver): Initialized Chrome WebDriver instance
      username (str): DamaDam username
      password (str): DamaDam password
    
    RETURNS:
      bool: True if login successful, False otherwise
    """
    try:
        # Wait for and locate username field
        nick_field = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#nick, input[name='nick']"))
        )
        
        # Wait for and locate password field
        try:
            pwd_field = driver.find_element(By.CSS_SELECTOR, "#pass, input[name='pass']")
        except NoSuchElementException:
            pwd_field = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
        
        # Find submit button
        submit_btn = driver.find_element(
            By.CSS_SELECTOR, "button[type='submit'], form button"
        )
        
        # Clear fields and enter credentials
        nick_field.clear()
        nick_field.send_keys(username)
        time.sleep(0.5)
        
        pwd_field.clear()
        pwd_field.send_keys(password)
        time.sleep(0.5)
        
        # Submit form
        submit_btn.click()
        time.sleep(4)
        
        # Check if we're no longer on login page
        if 'login' not in driver.current_url.lower():
            return True
        
        return False
        
    except TimeoutException:
        log_msg("[LOGIN] Form elements not found - timeout")
        return False
    except Exception as e:
        log_msg(f"[LOGIN] Login attempt error: {e}")
        return False


# ==================== SESSION VERIFICATION ====================

def verify_login_status(driver):
    """
    PURPOSE: Verify that we're currently logged in by checking page elements
             that only appear to authenticated users.
    
    LOGIC:
      - Check if we're on login page (means not authenticated)
      - Look for user-specific elements
      - Return authentication status
    
    ARGS:
      driver (WebDriver): Active Chrome WebDriver instance
    
    RETURNS:
      bool: True if logged in, False otherwise
    """
    try:
        # Most reliable check: are we on login page?
        if 'login' in driver.current_url.lower():
            return False
        
        # Try to find authenticated user indicators
        try:
            driver.find_element(By.CSS_SELECTOR, "a[href*='/profile/']")
            return True
        except NoSuchElementException:
            return False
            
    except Exception as e:
        log_msg(f"[LOGIN] Status verification error: {e}")
        return False
