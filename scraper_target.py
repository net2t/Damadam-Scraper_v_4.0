"""
Target Mode Scraper - Scrapes users from Target sheet
"""

import time
import re
from datetime import datetime, timedelta, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import Config
from browser import get_pkt_time, log_msg

# ==================== HELPER FUNCTIONS ====================

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = str(text).strip().replace('\xa0', ' ').replace('\n', ' ')
    return re.sub(r"\s+", " ", text).strip()

def convert_relative_date(text):
    """Convert 'X ago' to absolute date"""
    if not text:
        return ""
    
    t = text.lower().strip().replace("mins", "minutes").replace("min", "minute")
    t = t.replace("secs", "seconds").replace("sec", "second")
    t = t.replace("hrs", "hours").replace("hr", "hour")
    
    match = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", t)
    if not match:
        return text
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    seconds_map = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
        "week": 604800,
        "month": 2592000,
        "year": 31536000
    }
    
    if unit in seconds_map:
        dt = get_pkt_time() - timedelta(seconds=amount * seconds_map[unit])
        return dt.strftime("%d-%b-%y")
    
    return text

def detect_suspension(page_source):
    """Detect account suspension"""
    if not page_source:
        return None
    
    lower = page_source.lower()
    for indicator in Config.SUSPENSION_INDICATORS:
        if indicator in lower:
            return indicator
    return None

# ==================== PROFILE SCRAPER ====================

class ProfileScraper:
    """Scrapes individual user profiles"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def scrape_profile(self, nickname, source="Target"):
        """Scrape complete profile data"""
        url = f"https://damadam.pk/users/{nickname}/"
        
        try:
            log_msg(f"Scraping: {nickname}", "SCRAPING")
            
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.cxl.clb.lsp"))
            )
            
            page_source = self.driver.page_source
            now = get_pkt_time()
            
            # Initialize profile data
            data = {
                "NICK NAME": nickname,
                "TAGS": "",
                "CITY": "",
                "GENDER": "",
                "MARRIED": "",
                "AGE": "",
                "JOINED": "",
                "FOLLOWERS": "",
                "STATUS": "Normal",
                "POSTS": "",
                "INTRO": "",
                "SOURCE": source,
                "DATETIME SCRAP": now.strftime("%d-%b-%y %I:%M %p"),
                "LAST POST": "",
                "LAST POST TIME": "",
                "IMAGE": "",
                "PROFILE LINK": url.rstrip('/'),
                "POST URL": f"https://damadam.pk/profile/public/{nickname}",
            }
            
            # Check suspension
            suspend_reason = detect_suspension(page_source)
            if suspend_reason:
                data['STATUS'] = 'Banned'
                data['INTRO'] = "Account Suspended"[:250]
                data['__skip_reason'] = 'Account Suspended'
                return data
            
            if 'account suspended' in page_source.lower():
                data['STATUS'] = 'Banned'
                data['__skip_reason'] = 'Account Suspended'
                return data
            
            # Check unverified
            if (
                re.search(r">\s*unverified\s*user\s*<", page_source, re.IGNORECASE) or
                'background:tomato' in page_source or
                'style="background:tomato"' in page_source.lower()
            ):
                data['STATUS'] = 'Unverified'
                data['__skip_reason'] = 'Unverified user'
                return data
            
            # Extract intro
            for sel in ["span.cl.sp.lsp.nos", "span.cl", ".ow span.nos"]:
                try:
                    intro = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if intro.text.strip():
                        data['INTRO'] = clean_text(intro.text)
                        break
                except:
                    pass
            
            # Extract profile fields
            fields = {
                'City:': 'CITY',
                'Gender:': 'GENDER',
                'Married:': 'MARRIED',
                'Age:': 'AGE',
                'Joined:': 'JOINED'
            }
            
            for label, key in fields.items():
                try:
                    elem = self.driver.find_element(
                        By.XPATH,
                        f"//b[contains(text(), '{label}')]/following-sibling::span[1]"
                    )
                    value = elem.text.strip()
                    
                    if not value:
                        continue
                    
                    if key == 'JOINED':
                        data[key] = convert_relative_date(value)
                    elif key == 'GENDER':
                        low = value.lower()
                        if 'female' in low:
                            data[key] = 'Female'
                        elif 'male' in low:
                            data[key] = 'Male'
                    elif key == 'MARRIED':
                        low = value.lower()
                        if low in {'yes', 'married'}:
                            data[key] = 'Yes'
                        elif low in {'no', 'single', 'unmarried'}:
                            data[key] = 'No'
                    else:
                        data[key] = clean_text(value)
                
                except:
                    continue
            
            # Extract followers
            for sel in ["span.cl.sp.clb", ".cl.sp.clb"]:
                try:
                    followers = self.driver.find_element(By.CSS_SELECTOR, sel)
                    match = re.search(r'(\d+)', followers.text)
                    if match:
                        data['FOLLOWERS'] = match.group(1)
                        break
                except:
                    pass
            
            # Extract posts count
            for sel in [
                "a[href*='/profile/public/'] button div:first-child",
                "a[href*='/profile/public/'] button div"
            ]:
                try:
                    posts = self.driver.find_element(By.CSS_SELECTOR, sel)
                    match = re.search(r'(\d+)', posts.text)
                    if match:
                        data['POSTS'] = match.group(1)
                        break
                except:
                    pass
            
            # Extract profile image
            for sel in [
                "img[src*='avatar-imgs']",
                "img[src*='avatar']",
                "div[style*='whitesmoke'] img[src*='cloudfront.net']"
            ]:
                try:
                    img = self.driver.find_element(By.CSS_SELECTOR, sel)
                    src = img.get_attribute('src')
                    if src and ('avatar' in src or 'cloudfront.net' in src):
                        data['IMAGE'] = src.replace('/thumbnail/', '/')
                        break
                except:
                    pass
            
            # Get recent post if available
            if data.get('POSTS') and data['POSTS'] != '0':
                time.sleep(1)
                post_data = self._scrape_recent_post(nickname)
                data['LAST POST'] = post_data.get('url', '')
                data['LAST POST TIME'] = post_data.get('time', '')
            
            log_msg(
                f"Extracted: Gender={data['GENDER']}, City={data['CITY']}, "
                f"Posts={data['POSTS']}, Status={data['STATUS']}",
                "OK"
            )
            
            return data
        
        except TimeoutException:
            log_msg(f"Timeout while scraping {nickname}", "TIMEOUT")
            return None
        
        except WebDriverException as e:
            log_msg(f"Browser error while scraping {nickname}: {e}", "BROWSER_ERROR")
            return None
        
        except Exception as e:
            log_msg(f"Error scraping {nickname}: {str(e)[:60]}", "ERROR")
            return None
    
    def _scrape_recent_post(self, nickname):
        """Scrape most recent post"""
        post_url = f"https://damadam.pk/profile/public/{nickname}"
        
        try:
            self.driver.get(post_url)
            
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article.mbl"))
                )
            except TimeoutException:
                return {'url': '', 'time': ''}
            
            recent_post = self.driver.find_element(By.CSS_SELECTOR, "article.mbl")
            result = {'url': '', 'time': ''}
            
            # Get post URL
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
                        result['url'] = formatter(href)
                        break
                except:
                    continue
            
            # Get post timestamp
            time_selectors = [
                "span[itemprop='datePublished']",
                "time[itemprop='datePublished']",
                "span.cxs.cgy",
                "time"
            ]
            
            for sel in time_selectors:
                try:
                    time_elem = recent_post.find_element(By.CSS_SELECTOR, sel)
                    if time_elem.text.strip():
                        result['time'] = convert_relative_date(time_elem.text.strip())
                        break
                except:
                    continue
            
            return result
        
        except Exception:
            return {'url': '', 'time': ''}

# ==================== TARGET MODE RUNNER ====================

def run_target_mode(driver, sheets, max_profiles=0):
    """Run scraper in Target mode"""
    log_msg("=== TARGET MODE STARTED ===")
    
    # Get pending targets
    targets = sheets.get_pending_targets()
    
    if not targets:
        log_msg("No pending targets found")
        return {
            "success": 0,
            "failed": 0,
            "new": 0,
            "updated": 0,
            "unchanged": 0
        }
    
    # Limit targets if specified
    if max_profiles > 0:
        targets = targets[:max_profiles]
    
    log_msg(f"Processing {len(targets)} targets...")
    
    scraper = ProfileScraper(driver)
    stats = {"success": 0, "failed": 0, "new": 0, "updated": 0, "unchanged": 0}
    
    for i, target in enumerate(targets, 1):
        nickname = target['nickname']
        row = target['row']
        source = target.get('source', 'Target')
        
        log_msg(f"[{i}/{len(targets)}] Processing: {nickname}")
        
        try:
            # Scrape profile
            profile = scraper.scrape_profile(nickname, source)
            
            if not profile:
                sheets.update_target_status(
                    row, "Pending", 
                    f"Scrape failed @ {get_pkt_time().strftime('%I:%M %p')}"
                )
                stats['failed'] += 1
                continue
            
            # Check skip reason
            skip_reason = profile.get('__skip_reason')
            if skip_reason:
                sheets.write_profile(profile)
                sheets.update_target_status(
                    row, "Error",
                    f"{skip_reason} @ {get_pkt_time().strftime('%I:%M %p')}"
                )
                stats['failed'] += 1
            else:
                # Write profile
                result = sheets.write_profile(profile)
                status = result.get("status", "error")
                
                if status in {"new", "updated", "unchanged"}:
                    stats['success'] += 1
                    stats[status] += 1
                    sheets.update_target_status(
                        row, "Done",
                        f"{status} @ {get_pkt_time().strftime('%I:%M %p')}"
                    )
                else:
                    raise RuntimeError(result.get("error", "Write failed"))
        
        except Exception as e:
            log_msg(f"Error processing {nickname}: {e}", "ERROR")
            sheets.update_target_status(
                row, "Pending",
                f"Error: {str(e)[:50]}"
            )
            stats['failed'] += 1
        
        # Delay between profiles
        time.sleep(Config.MIN_DELAY)
    
    log_msg("=== TARGET MODE COMPLETED ===")
    log_msg(f"Results: {stats['success']} success, {stats['failed']} failed")
    
    return stats
