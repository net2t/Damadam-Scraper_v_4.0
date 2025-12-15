"""
================================================================================
config.py - Configuration & Environment Variables
================================================================================
PURPOSE: Centralized configuration management for the entire DamaDam Scraper.
         Handles local credentials, GitHub Secrets, defaults, and constants.

FEATURES:
  - Loads .env file for local development
  - Supports GitHub Secrets (plain JSON or base64 encoded)
  - Path normalization for cross-platform support
  - All constants & configuration in one place
================================================================================
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# ==================== PATHS ====================
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR

# ==================== LOAD .ENV FILE ====================
# Load .env file if it exists locally
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    print(f"[DEBUG] Loading .env from: {env_file}")
    with open(env_file, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value

# ==================== ENVIRONMENT DETECTION ====================
IS_CI = bool(os.getenv('GITHUB_ACTIONS'))
IS_LOCAL = not IS_CI

# ==================== DAMADAM CREDENTIALS ====================
DAMADAM_USERNAME = os.getenv('DAMADAM_USERNAME', '').strip()
DAMADAM_PASSWORD = os.getenv('DAMADAM_PASSWORD', '').strip()
DAMADAM_USERNAME_2 = os.getenv('DAMADAM_USERNAME_2', '').strip()
DAMADAM_PASSWORD_2 = os.getenv('DAMADAM_PASSWORD_2', '').strip()

# ==================== GOOGLE SHEETS CREDENTIALS ====================
GOOGLE_SHEET_URL = os.getenv('GOOGLE_SHEET_URL', '').strip()

_raw_google_secret = (
    os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip()
    or os.getenv('GOOGLE_CREDENTIALS', '').strip()
)

# Attempt to decode base64 encoded secrets automatically
if _raw_google_secret and not _raw_google_secret.startswith('{'):
    try:
        decoded = base64.b64decode(_raw_google_secret).decode('utf-8')
        if decoded.strip().startswith('{'):
            _raw_google_secret = decoded.strip()
    except Exception:
        # Leave as-is; json loading will raise a helpful error later
        pass

GOOGLE_CREDENTIALS_JSON = _raw_google_secret
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json').strip()


def _normalize_path(path_value: str) -> str:
    """Return absolute, normalized path for cross-platform support."""
    value = (path_value or '').strip().strip('"').strip("'")
    if not value:
        return ''

    path_obj = Path(value)
    if path_obj.is_absolute():
        return str(path_obj)
    return str(PROJECT_ROOT / path_obj)


GOOGLE_CRED_PATH = _normalize_path(GOOGLE_APPLICATION_CREDENTIALS)
CHROMEDRIVER_PATH = _normalize_path(os.getenv('CHROMEDRIVER_PATH', 'chromedriver.exe'))
COOKIE_FILE = str(PROJECT_ROOT / 'damadam_cookies.pkl')

# ==================== BROWSER CONFIG ====================
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '30'))

# ==================== SCRAPING BEHAVIOUR ====================
MAX_PROFILES_PER_RUN = int(os.getenv('MAX_PROFILES_PER_RUN', '0'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '20'))
MIN_DELAY = float(os.getenv('MIN_DELAY', '0.3'))
MAX_DELAY = float(os.getenv('MAX_DELAY', '0.5'))
SHEET_WRITE_DELAY = float(os.getenv('SHEET_WRITE_DELAY', '1.0'))

# ==================== SHEET NAMES & COLUMNS ====================
SHEET_PROFILES = "Profiles"
SHEET_RUNLIST = "RunList"
SHEET_ONLINE_LOG = os.getenv('ONLINE_LOG_SHEET', 'OnlineLog')

COLUMN_ORDER = [
    "NICK NAME", "TAGS", "CITY", "GENDER", "MARRIED", "AGE", "JOINED",
    "FOLLOWERS", "STATUS", "POSTS", "INTRO", "SOURCE", "DATETIME SCRAP",
    "LAST POST", "LAST POST TIME", "IMAGE", "PROFILE LINK", "POST URL"
]

COLUMN_TO_INDEX = {name: idx for idx, name in enumerate(COLUMN_ORDER)}
HIGHLIGHT_EXCLUDE_COLUMNS = {"LAST POST", "LAST POST TIME", "JOINED", "PROFILE LINK", "DATETIME SCRAP"}

# ==================== STATUS VALUES ====================
STATUS_VERIFIED = "Verified"
STATUS_UNVERIFIED = "Unverified"
STATUS_BANNED = "Banned"

TARGET_STATUS_PENDING = "⚡ Pending"
TARGET_STATUS_DONE = "Done 💀"
TARGET_STATUS_ERROR = "Error 💥"

SUSPENSION_INDICATORS = [
    "accounts suspend",
    "aik se zyada fake accounts",
    "abuse ya harassment",
    "kisi aur user ki identity apnana",
    "accounts suspend kiye",
]

# ==================== DAMADAM URLS ====================
LOGIN_URL = "https://damadam.pk/login/"
HOME_URL = "https://damadam.pk/"
ONLINE_USERS_URL = "https://damadam.pk/online_kon/"

# ==================== VALIDATION HELPERS ====================


def _debug_print_credentials():
    print(f"📍 Script Directory: {PROJECT_ROOT}")
    print(f"📍 Credentials Path: {GOOGLE_CRED_PATH}")
    print(f"📍 Looking for: {GOOGLE_APPLICATION_CREDENTIALS}")

    cred_file_exists = False
    if GOOGLE_CRED_PATH:
        cred_file_exists = Path(GOOGLE_CRED_PATH).exists()
        print(f"📁 File exists: {cred_file_exists}")
        if cred_file_exists:
            print(f"   ✅ Found at: {GOOGLE_CRED_PATH}")

    if GOOGLE_CREDENTIALS_JSON:
        sample = GOOGLE_CREDENTIALS_JSON[:40].replace('\n', ' ')
        print(f"✅ Google Credentials: Raw JSON provided ({len(GOOGLE_CREDENTIALS_JSON)} chars)")
        print(f"   Preview: {sample}...")
    else:
        print("❌ Google Credentials: Raw JSON not provided")

    return cred_file_exists


def validate_config():
    """Validate that all required configuration is present."""
    print("\n" + "=" * 70)
    print("CONFIGURATION VALIDATION")
    print("=" * 70)

    cred_file_exists = _debug_print_credentials()

    errors = []

    if not DAMADAM_USERNAME or not DAMADAM_PASSWORD:
        errors.append("❌ DAMADAM_USERNAME and DAMADAM_PASSWORD not set")
    else:
        print(f"✅ DamaDam Username: {DAMADAM_USERNAME}")

    if not GOOGLE_SHEET_URL:
        errors.append("❌ GOOGLE_SHEET_URL not set")
    else:
        print("✅ Google Sheet URL: Present")

    if not cred_file_exists and not GOOGLE_CREDENTIALS_JSON:
        errors.append("❌ Google credentials not found (file or JSON)")

    print("\n" + "=" * 70)
    if errors:
        print("VALIDATION FAILED")
        print("=" * 70)
        for error in errors:
            print(error)
        print("\n🔍 Troubleshooting:")
        print("1. Check if .env file exists in root directory")
        print("2. Check if credentials.json exists in root directory")
        print("3. Verify GOOGLE_APPLICATION_CREDENTIALS path in .env")
        print("4. Ensure GOOGLE_CREDENTIALS_JSON secret contains valid JSON (or base64)")
        print("=" * 70 + "\n")
        sys.exit(1)

    print("✅ VALIDATION PASSED")
    print("=" * 70 + "\n")


if __name__ != '__main__':
    validate_config()
