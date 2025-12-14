"""
================================================================================
core/__init__.py - Package Initialization
================================================================================
PURPOSE: Makes the core folder a Python package and exposes main classes/functions
         for easy importing in main.py

EXPORTS:
  - SheetsManager (from sheets)
  - authenticate (from auth)
  - setup_browser (from browser)
  - scrape_profile (from scraper)
  - log_msg, get_pkt_time (from logger)
================================================================================
"""

from core.config import (
    validate_config,
    SCRIPT_DIR, IS_CI,
    MAX_PROFILES_PER_RUN, BATCH_SIZE, MIN_DELAY, MAX_DELAY,
    TARGET_STATUS_DONE, TARGET_STATUS_ERROR, TARGET_STATUS_PENDING
)

from core.logger import (
    log_msg, get_pkt_time, get_timestamp_full,
    print_header, print_separator, print_success, print_error
)

from core.browser import (
    setup_browser, save_cookies, load_cookies, clear_cookies
)

from core.auth import authenticate, verify_login_status

from core.sheets import authenticate_google, SheetsManager

from core.scraper import scrape_profile

__all__ = [
    'validate_config',
    'log_msg', 'get_pkt_time', 'get_timestamp_full',
    'print_header', 'print_separator', 'print_success', 'print_error',
    'setup_browser', 'save_cookies', 'load_cookies', 'clear_cookies',
    'authenticate', 'verify_login_status',
    'authenticate_google', 'SheetsManager',
    'scrape_profile',
    'SCRIPT_DIR', 'IS_CI',
    'MAX_PROFILES_PER_RUN', 'BATCH_SIZE', 'MIN_DELAY', 'MAX_DELAY',
    'TARGET_STATUS_DONE', 'TARGET_STATUS_ERROR', 'TARGET_STATUS_PENDING'
]
