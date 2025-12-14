"""
================================================================================
CONFIG.PY - CONFIGURATION & ENVIRONMENT VARIABLES
================================================================================
PURPOSE: Centralized configuration management for the entire DamaDam Scraper.
         Handles local credentials, GitHub Secrets, defaults, and constants.

FEATURES:
  - Loads .env file for local development
  - Falls back to GitHub Secrets in CI/CD
  - Path normalization for cross-platform support
  - All constants & configuration in one place
================================================================================
"""

import os
import sys
import json
from pathlib import Path

# ==================== PATHS ====================
## Root directory where script is running
SCRIPT_DIR = Path(__file__).parent.parent.absolute()

# ==================== LOAD .ENV FILE ====================
## Load .env file if it exists locally
env_file = SCRIPT_DIR / '.env'
if env_file.exists():
    print(f"[DEBUG] Loading .env from: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value

# ==================== ENVIRONMENT DETECTION ====================
## Check if running in GitHub Actions CI/CD
IS_CI = bool(os.getenv('GITHUB_ACTIONS'))
IS_LOCAL = not IS_CI

# ==================== DAMADAM CREDENTIALS ====================
## Primary DamaDam account credentials
DAMADAM_USERNAME = os.getenv('DAMADAM_USERNAME', '').strip()
DAMADAM_PASSWORD = os.getenv('DAMADAM_PASSWORD', '').strip()

## Secondary DamaDam account (optional)
DAMADAM_USERNAME_2 = os.getenv('DAMADAM_USERNAME_2', '').strip()
DAMADAM_PASSWORD_2 = os.getenv('DAMADAM_PASSWORD_2', '').strip()

# ==================== GOOGLE SHEETS CREDENTIALS ====================
## Google Sheet URL where data will be stored
GOOGLE_SHEET_URL = os.getenv('GOOGLE_SHEET_URL', '').strip()

## Raw JSON credentials string (for GitHub Actions)
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip()

## Path to local credentials.json file
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json').strip()

def _normalize_cred_path(p: str) -> str:
    """
    PURPOSE: Normalize credential file paths for cross-platform support
    
    LOGIC:
      - Strip quotes and whitespace
      - If relative path, make it absolute from SCRIPT_DIR
      - If absolute path, use as-is
      - Return normalized path
    
    ARGS:
      p (str): Path to normalize
    
    RETURNS:
      str: Normalized absolute path, or empty string if input is empty
    """
    p = (p or "").strip().strip('"').strip("'")
    if not p:
        return ""
    
    path_obj = Path(p)
    
    # If already absolute, return as-is
    if path_obj.is_absolute():
        return str(path_obj)
    
    # Make relative to SCRIPT_DIR
    full_path = SCRIPT_DIR / p
    return str(full_path)

GOOGLE_CRED_PATH = _normalize_cred_path(GOOGLE_APPLICATION_CREDENTIALS)

# ==================== BROWSER & COOKIES ====================
## Path to ChromeDriver executable
CHROMEDRIVER_PATH = _normalize_cred_path(
    os.getenv('CHROMEDRIVER_PATH', 'chromedriver.exe')
)

## Cookie file for session persistence (stored locally)
COOKIE_FILE = str(SCRIPT_DIR / 'damadam_cookies.pkl')

## Browser timeout for page loads (seconds)
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '30'))

# ==================== SCRAPING BEHAVIOR ====================
## Max profiles to scrape per run (0 = all)
MAX_PROFILES_PER_RUN = int(os.getenv('MAX_PROFILES_PER_RUN', '0'))

## Batch size before taking a pause
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '20'))

## Minimum delay between requests (seconds)
MIN_DELAY = float(os.getenv('MIN_DELAY', '0.3'))

## Maximum delay between requests (seconds)
MAX_DELAY = float(os.getenv('MAX_DELAY', '0.5'))

## Delay when writing to Google Sheets (seconds)
SHEET_WRITE_DELAY = float(os.getenv('SHEET_WRITE_DELAY', '1.0'))

# ==================== SHEET NAMES & COLUMNS ====================
## Worksheet names in Google Sheets
SHEET_PROFILES = "Profiles"
SHEET_RUNLIST = "RunList"

## Column order for the Profiles sheet
COLUMN_ORDER = [
    "NICK NAME", "TAGS", "CITY", "GENDER", "MARRIED", "AGE", "JOINED", 
    "FOLLOWERS", "STATUS", "POSTS", "INTRO", "SOURCE", "DATETIME SCRAP",
    "LAST POST", "LAST POST TIME", "IMAGE", "PROFILE LINK", "POST URL"
]

## Map column names to their index positions
COLUMN_TO_INDEX = {name: idx for idx, name in enumerate(COLUMN_ORDER)}

## Columns to exclude from highlighting
HIGHLIGHT_EXCLUDE_COLUMNS = {"LAST POST", "LAST POST TIME", "JOINED", "PROFILE LINK", "DATETIME SCRAP"}

# ==================== STATUS VALUES ====================
## Profile status: Account is verified and active
STATUS_VERIFIED = "Verified"

## Profile status: Account is unverified
STATUS_UNVERIFIED = "Unverified"

## Profile status: Account is banned/suspended
STATUS_BANNED = "Banned"

## Target sheet status: Pending scraping
TARGET_STATUS_PENDING = "⚡ Pending"

## Target sheet status: Successfully scraped
TARGET_STATUS_DONE = "Done 💀"

## Target sheet status: Encountered error
TARGET_STATUS_ERROR = "Error 💥"

# ==================== SUSPENSION INDICATORS ====================
## List of phrases that indicate account suspension
SUSPENSION_INDICATORS = [
    "accounts suspend",
    "aik se zyada fake accounts",
    "abuse ya harassment",
    "kisi aur user ki identity apnana",
    "accounts suspend kiye",
]

# ==================== DAMADAM URLS ====================
## DamaDam login page URL
LOGIN_URL = "https://damadam.pk/login/"

## DamaDam home page URL
HOME_URL = "https://damadam.pk/"

# ==================== VALIDATION ====================

def validate_config():
    """
    PURPOSE: Validate that all required configuration is present
    
    LOGIC:
      - Check if DamaDam credentials are set
      - Check if Google Sheet URL is set
      - Check if Google credentials exist (local file OR raw JSON)
      - Exit with error message if validation fails
      - Print detected values for debugging
    
    RETURNS:
      None (exits on error with code 1)
    """
    print("\n" + "=" * 70)
    print("CONFIGURATION VALIDATION")
    print("=" * 70)
    
    # Debug output
    print(f"\n📍 Script Directory: {SCRIPT_DIR}")
    print(f"📍 Credentials Path: {GOOGLE_CRED_PATH}")
    print(f"📍 Looking for: {GOOGLE_APPLICATION_CREDENTIALS}")
    
    # Check if credentials file exists
    cred_file_exists = False
    if GOOGLE_CRED_PATH:
        cred_file_exists = Path(GOOGLE_CRED_PATH).exists()
        print(f"📁 File exists: {cred_file_exists}")
        if cred_file_exists:
            print(f"   ✅ Found at: {GOOGLE_CRED_PATH}")
    
    errors = []
    
    # Validate DamaDam credentials
    if not DAMADAM_USERNAME or not DAMADAM_PASSWORD:
        errors.append("❌ DAMADAM_USERNAME and DAMADAM_PASSWORD not set")
    else:
        print(f"✅ DamaDam Username: {DAMADAM_USERNAME}")
    
    # Validate Google Sheet URL
    if not GOOGLE_SHEET_URL:
        errors.append("❌ GOOGLE_SHEET_URL not set")
    else:
        print(f"✅ Google Sheet URL: Present")
    
    # Validate Google credentials
    if not cred_file_exists and not GOOGLE_CREDENTIALS_JSON:
        errors.append("❌ Google credentials not found")
        print(f"❌ No credentials found:")
        print(f"   - File check: {cred_file_exists}")
        print(f"   - Raw JSON: {bool(GOOGLE_CREDENTIALS_JSON)}")
    else:
        if cred_file_exists:
            print(f"✅ Google Credentials: File found")
        elif GOOGLE_CREDENTIALS_JSON:
            print(f"✅ Google Credentials: Raw JSON found")
    
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
        print("4. Try absolute path: /full/path/to/credentials.json")
        print("=" * 70 + "\n")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED")
        print("=" * 70 + "\n")

# ==================== INITIALIZATION ====================
if __name__ != '__main__':
    # Validate config when module is imported
    validate_config()