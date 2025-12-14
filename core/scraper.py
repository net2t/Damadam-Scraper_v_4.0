"""
================================================================================
SCRAPER.PY - PROFILE SCRAPING LOGIC
================================================================================
PURPOSE: Extract profile data from DamaDam.pk user pages.
         Handles profile parsing, data cleaning, and error detection.

FEATURES:
  - Extract profile fields (city, age, gender, followers, posts, etc.)
  - Detect account status (Verified, Unverified, Banned)
  - Parse relative timestamps to absolute dates
  - Scrape recent post information
  - Graceful error handling for missing data
================================================================================
"""

import re
import time
from datetime import datetime, timedelta, timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# ==================== SAFE IMPORTS ====================
def get_config_constants():
    """
    PURPOSE: Safely import config constants without circular imports
    """
    try:
        from core.config import (
            STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_BANNED,
            SUSPENSION_INDICATORS, COLUMN_ORDER
        )
    except ImportError:
        try:
            from .config import (
                STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_BANNED,
                SUSPENSION_INDICATORS, COLUMN_ORDER
            )
        except ImportError:
            # Fallback values
            STATUS_VERIFIED = "Verified"
            STATUS_UNVERIFIED = "Unverified"
            STATUS_BANNED = "Banned"
            SUSPENSION_INDICATORS = [
                "accounts suspend", "aik se zyada fake accounts",
                "abuse ya harassment", "kisi aur user ki identity apnana",
                "accounts suspend kiye",
            ]
            COLUMN_ORDER = [
                "NICK NAME", "TAGS", "CITY", "GENDER", "MARRIED", "AGE", "JOINED",
                "FOLLOWERS", "STATUS", "POSTS", "INTRO", "SOURCE", "DATETIME SCRAP",
                "LAST POST", "LAST POST TIME", "IMAGE", "PROFILE LINK", "POST URL"
            ]
    
    return STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_BANNED, SUSPENSION_INDICATORS, COLUMN_ORDER

def log_msg(message: str):
    """
    PURPOSE: Safe logging function without imports
    """
    ts = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)
    ts_str = ts.strftime('%H:%M:%S')
    print(f"[{ts_str}] {message}")

# Get constants
STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_BANNED, SUSPENSION_INDICATORS, COLUMN_ORDER = get_config_constants()

# ==================== TIME UTILITIES ====================

def get_pkt_time():
    """
    PURPOSE: Get current time in Pakistan Standard Time (UTC+5)
    """
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def get_timestamp():
    """
    PURPOSE: Get formatted timestamp for scraping
    """
    return get_pkt_time().strftime("%d-%b-%y %I:%M %p")

# ==================== DATA CLEANING UTILITIES ====================

def clean_text(text: str) -> str:
    """
    PURPOSE: Clean and normalize text extracted from HTML.
    
    LOGIC:
      - Remove extra whitespace and non-breaking spaces
      - Strip leading/trailing whitespace
      - Normalize newlines to spaces
    
    ARGS:
      text (str): Raw text from HTML
    
    RETURNS:
      str: Cleaned text
    """
    if not text:
        return ""
    text = str(text).strip().replace('\xa0', ' ').replace('\n', ' ')
    return re.sub(r"\s+", " ", text).strip()


def clean_data(value: str) -> str:
    """
    PURPOSE: Clean profile data and remove placeholder values.
    """
    if not value:
        return ""
    
    value = str(value).strip().replace('\xa0', ' ')
    
    placeholders = {
        "No city", "Not set", "[No Posts]", "N/A",
        "no city", "not set", "[no posts]", "n/a",
        "[No Post URL]", "[Error]", "no set", "none", "null"
    }
    
    if value in placeholders:
        return ""
    
    return re.sub(r"\s+", " ", value)


def convert_relative_to_absolute_date(relative_text: str) -> str:
    """
    PURPOSE: Convert relative timestamps ("2 days ago") to absolute dates.
    """
    if not relative_text:
        return ""
    
    text = relative_text.lower().strip()
    
    # Normalize common variations
    text = text.replace("mins", "minutes").replace("min", "minute")
    text = text.replace("secs", "seconds").replace("sec", "second")
    text = text.replace("hrs", "hours").replace("hr", "hour")
    
    # Match pattern: "N unit ago"
    match = re.search(
        r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago",
        text
    )
    
    if not match:
        return relative_text
    
    # Extract amount and unit
    amount = int(match.group(1))
    unit = match.group(2)
    
    # Map units to seconds
    unit_seconds = {
        "second": 1, "minute": 60, "hour": 3600, "day": 86400,
        "week": 604800, "month": 2592000, "year": 31536000
    }
    
    if unit not in unit_seconds:
        return relative_text
    
    # Calculate absolute date
    now = get_pkt_time()
    delta = timedelta(seconds=amount * unit_seconds[unit])
    absolute_date = now - delta
    
    return absolute_date.strftime("%d-%b-%y")


# ==================== PROFILE SCRAPING ====================

def scrape_profile(driver, nickname: str) -> dict | None:
    """
    PURPOSE: Main profile scraping function.
             Extracts all profile data from DamaDam user page.
    
    LOGIC:
      - Navigate to profile URL
      - Wait for page to load
      - Detect account status (Verified/Unverified/Banned)
      - Extract profile fields
      - Scrape recent post if any
      - Return complete profile dict
    
    ARGS:
      driver (WebDriver): Active Chrome WebDriver
      nickname (str): DamaDam username/nickname
    
    RETURNS:
      dict: Profile data with all columns, or None if failed
    """
    profile_url = f"https://damadam.pk/users/{nickname}/"
    
    try:
        log_msg(f"[SCRAPING] Fetching {nickname}...")
        
        # Navigate to profile
        driver.get(profile_url)
        
        # Wait for main profile heading to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.cxl.clb.lsp"))
        )
        
        # Get page source for suspension detection
        page_source = driver.page_source
        
        # Initialize base profile data
        profile = {
            "NICK NAME": nickname,
            "TAGS": "",
            "CITY": "",
            "GENDER": "",
            "MARRIED": "",
            "AGE": "",
            "JOINED": "",
            "FOLLOWERS": "",
            "STATUS": STATUS_VERIFIED,
            "POSTS": "",
            "INTRO": "",
            "SOURCE": "RunList",
            "DATETIME SCRAP": get_timestamp(),
            "LAST POST": "",
            "LAST POST TIME": "",
            "IMAGE": "",
            "PROFILE LINK": profile_url.rstrip('/'),
            "POST URL": f"https://damadam.pk/profile/public/{nickname}",
        }
        
        # Check account status
        status_result = _detect_account_status(driver, page_source)
        if status_result['status'] != STATUS_VERIFIED:
            profile['STATUS'] = status_result['status']
            profile['INTRO'] = status_result.get('reason', 'Account not verified')
            return profile
        
        # Extract profile fields
        _extract_profile_fields(driver, profile)
        
        # Extract intro/bio
        _extract_intro(driver, profile)
        
        # Extract followers count
        _extract_followers(driver, profile)
        
        # Extract posts count
        _extract_posts_count(driver, profile)
        
        # Extract profile image
        _extract_profile_image(driver, profile)
        
        # Scrape recent post if has posts
        if profile.get('POSTS') and profile['POSTS'] != '0':
            time.sleep(1)
            _scrape_recent_post(driver, nickname, profile)
        
        log_msg(f"[OK] {nickname}: {profile['GENDER']}, {profile['CITY']}, Posts: {profile['POSTS']}")
        return profile
        
    except TimeoutException:
        log_msg(f"[TIMEOUT] Loading {nickname} took too long")
        return None
    except WebDriverException as e:
        log_msg(f"[BROWSER_ERROR] Browser issue while scraping {nickname}")
        return None
    except Exception as e:
        log_msg(f"[ERROR] Scraping {nickname} failed: {str(e)[:60]}")
        return None


# ==================== STATUS DETECTION ====================

def _detect_account_status(driver, page_source: str) -> dict:
    """
    PURPOSE: Detect if account is Verified, Unverified, or Banned.
    """
    # Check for suspension reason in content
    for indicator in SUSPENSION_INDICATORS:
        if indicator.lower() in page_source.lower():
            return {'status': STATUS_BANNED, 'reason': 'Account Suspended'}
    
    # Check for "account suspended" text
    if 'account suspended' in page_source.lower():
        return {'status': STATUS_BANNED, 'reason': 'Account Suspended'}
    
    # Check for unverified UI (red/tomato background)
    if (re.search(r">\s*unverified\s*user\s*<", page_source, re.IGNORECASE) or
        'background:tomato' in page_source or
        'style="background:tomato"' in page_source.lower()):
        return {'status': STATUS_UNVERIFIED, 'reason': 'Account Unverified'}
    
    # Try CSS selector for tomato div
    try:
        driver.find_element(By.CSS_SELECTOR, "div[style*='tomato']")
        return {'status': STATUS_UNVERIFIED, 'reason': 'Account Unverified'}
    except NoSuchElementException:
        pass
    
    return {'status': STATUS_VERIFIED, 'reason': ''}


# ==================== FIELD EXTRACTION ====================

def _extract_profile_fields(driver, profile: dict):
    """
    PURPOSE: Extract standard profile fields (City, Gender, Age, etc.)
    """
    fields_map = {
        'City:': ('CITY', lambda x: clean_data(x)),
        'Gender:': ('GENDER', _parse_gender),
        'Married:': ('MARRIED', _parse_married),
        'Age:': ('AGE', lambda x: clean_data(x)),
        'Joined:': ('JOINED', convert_relative_to_absolute_date),
    }
    
    for label, (key, parser) in fields_map.items():
        try:
            elem = driver.find_element(
                By.XPATH, f"//b[contains(text(), '{label}')]/following-sibling::span[1]"
            )
            value = elem.text.strip()
            if value:
                profile[key] = parser(value)
        except NoSuchElementException:
            continue


def _extract_intro(driver, profile: dict):
    """
    PURPOSE: Extract profile bio/intro text.
    """
    selectors = ["span.cl.sp.lsp.nos", "span.cl", ".ow span.nos"]
    
    for selector in selectors:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, selector)
            if elem.text.strip():
                profile['INTRO'] = clean_text(elem.text)
                break
        except NoSuchElementException:
            continue


def _extract_followers(driver, profile: dict):
    """
    PURPOSE: Extract follower count from profile.
    """
    selectors = ["span.cl.sp.clb", ".cl.sp.clb"]
    
    for selector in selectors:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, selector)
            match = re.search(r'(\d+)', elem.text)
            if match:
                profile['FOLLOWERS'] = match.group(1)
                break
        except NoSuchElementException:
            continue


def _extract_posts_count(driver, profile: dict):
    """
    PURPOSE: Extract post count from profile.
    """
    selectors = [
        "a[href*='/profile/public/'] button div:first-child",
        "a[href*='/profile/public/'] button div"
    ]
    
    for selector in selectors:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, selector)
            match = re.search(r'(\d+)', elem.text)
            if match:
                profile['POSTS'] = match.group(1)
                break
        except NoSuchElementException:
            continue


def _extract_profile_image(driver, profile: dict):
    """
    PURPOSE: Extract profile image URL.
    """
    selectors = [
        "img[src*='avatar-imgs']",
        "img[src*='avatar']",
        "div[style*='whitesmoke'] img[src*='cloudfront.net']"
    ]
    
    for selector in selectors:
        try:
            img = driver.find_element(By.CSS_SELECTOR, selector)
            src = img.get_attribute('src')
            if src and ('avatar' in src or 'cloudfront.net' in src):
                profile['IMAGE'] = src.replace('/thumbnail/', '/')
                break
        except NoSuchElementException:
            continue


# ==================== POST SCRAPING ====================

def _scrape_recent_post(driver, nickname: str, profile: dict):
    """
    PURPOSE: Scrape most recent post info if profile has posts.
    """
    post_url = f"https://damadam.pk/profile/public/{nickname}"
    
    try:
        driver.get(post_url)
        
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.mbl"))
            )
        except TimeoutException:
            return  # No posts found
        
        recent_post = driver.find_element(By.CSS_SELECTOR, "article.mbl")
        
        # Extract post URL
        url_selectors = [
            ("a[href*='/content/']", lambda h: h),
            ("a[href*='/comments/text/']", lambda h: h),
            ("a[href*='/comments/image/']", lambda h: h)
        ]
        
        for selector, formatter in url_selectors:
            try:
                link = recent_post.find_element(By.CSS_SELECTOR, selector)
                href = link.get_attribute('href')
                if href:
                    profile['LAST POST'] = formatter(href)
                    break
            except NoSuchElementException:
                continue
        
        # Extract post timestamp
        time_selectors = [
            "span[itemprop='datePublished']",
            "time[itemprop='datePublished']",
            "span.cxs.cgy",
            "time"
        ]
        
        for selector in time_selectors:
            try:
                time_elem = recent_post.find_element(By.CSS_SELECTOR, selector)
                if time_elem.text.strip():
                    profile['LAST POST TIME'] = convert_relative_to_absolute_date(
                        time_elem.text.strip()
                    )
                    break
            except NoSuchElementException:
                continue
                
    except Exception as e:
        log_msg(f"[ERROR] Failed to scrape post for {nickname}: {e}")


# ==================== DATA PARSERS ====================

def _parse_gender(value: str) -> str:
    """
    PURPOSE: Parse gender field and normalize to "Male" or "Female".
    """
    lower = value.lower()
    if 'female' in lower:
        return "Female"
    elif 'male' in lower:
        return "Male"
    return ""


def _parse_married(value: str) -> str:
    """
    PURPOSE: Parse married field and normalize to "Yes" or "No".
    """
    lower = value.lower()
    if lower in {'yes', 'married'}:
        return "Yes"
    elif lower in {'no', 'single', 'unmarried'}:
        return "No"
    return ""
