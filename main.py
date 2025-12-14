#!/usr/bin/env python3
"""
================================================================================
MAIN.PY - ENTRY POINT & MASTER ORCHESTRATION
================================================================================
PURPOSE: Master orchestration file that coordinates the entire scraping workflow.
         This is the ONLY file you need to run.

WORKFLOW:
  1. Validate configuration
  2. Initialize browser
  3. Authenticate with DamaDam
  4. Connect to Google Sheets
  5. Fetch pending targets from RunList
  6. Scrape profiles (with duplicate detection)
  7. Append new profiles / add notes for duplicates
  8. Update RunList status
  9. Generate completion report

USAGE:
  python main.py                              # Run all pending targets
  python main.py --max-profiles 10           # Run only 10 profiles
  python main.py --batch-size 15             # Custom batch size
================================================================================
"""

import sys
import time
import argparse
import random
from pathlib import Path

# Import from core package
from core import (
    validate_config,
    log_msg, get_pkt_time, get_timestamp_full,
    print_header, print_separator, print_success, print_error,
    setup_browser,
    authenticate,
    authenticate_google, SheetsManager,
    scrape_profile,
    SCRIPT_DIR, IS_CI,
    MAX_PROFILES_PER_RUN, BATCH_SIZE, MIN_DELAY, MAX_DELAY,
    TARGET_STATUS_DONE, TARGET_STATUS_ERROR, TARGET_STATUS_PENDING
)

# ==================== UTILITIES ====================

class AdaptiveDelay:
    """
    PURPOSE: Adaptive delay system to avoid rate limiting.
             Increases delays when hitting limits, decreases when successful.
    
    ATTRIBUTES:
      base_min/base_max: Base delay range
      min_delay/max_delay: Current delay range (adaptive)
      hits: Number of consecutive rate limit hits
    """
    
    def __init__(self, min_delay: float, max_delay: float):
        """Initialize with base delay range."""
        self.base_min = min_delay
        self.base_max = max_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.hits = 0
        self.last_reset = time.time()
    
    def on_success(self):
        """
        PURPOSE: Call after successful request.
                 Gradually decrease delay if no errors.
        """
        if self.hits > 0:
            self.hits -= 1
        
        # Reset delay after 10 seconds of success
        if time.time() - self.last_reset > 10:
            self.min_delay = max(self.base_min, self.min_delay * 0.95)
            self.max_delay = max(self.base_max, self.max_delay * 0.95)
            self.last_reset = time.time()
    
    def on_batch_complete(self):
        """
        PURPOSE: Call after completing a batch.
                 Slightly increase delay before next batch.
        """
        self.min_delay = min(3.0, max(self.base_min, self.min_delay * 1.1))
        self.max_delay = min(6.0, max(self.base_max, self.max_delay * 1.1))
    
    def sleep(self):
        """
        PURPOSE: Sleep for current delay duration.
                 Adds randomness to avoid pattern detection.
        """
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)


def calculate_eta(processed: int, total: int, start_time: float) -> str:
    """
    PURPOSE: Calculate estimated time to completion based on processing rate.
    
    ARGS:
      processed (int): Number of items completed
      total (int): Total items to process
      start_time (float): Unix timestamp when started
    
    RETURNS:
      str: Human-readable ETA (e.g., "2h 30m")
    """
    if processed == 0:
        return "Calculating..."
    
    elapsed = time.time() - start_time
    rate = processed / elapsed if elapsed > 0 else 0
    remaining = total - processed
    eta_seconds = remaining / rate if rate > 0 else 0
    
    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    elif eta_seconds < 3600:
        return f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
    else:
        hours = int(eta_seconds // 3600)
        minutes = int((eta_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


# ==================== MAIN WORKFLOW ====================

def main():
    """
    PURPOSE: Main entry point for the DamaDam scraper.
    
    WORKFLOW:
      1. Parse command-line arguments
      2. Validate configuration
      3. Show configuration header
      4. Setup browser
      5. Authenticate with DamaDam
      6. Connect to Google Sheets
      7. Fetch pending targets
      8. Process each target (with duplicate detection)
      9. Report results
    
    RETURNS:
      int: Exit code (0 = success, 1 = error)
    """
    
    # ========== CONFIGURATION PARSING ==========
    parser = argparse.ArgumentParser(
        description="DamaDam Scraper v4.0 - Scrape profiles into Google Sheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run all pending targets
  python main.py --max-profiles 10 # Run only 10 profiles
  python main.py --batch-size 15   # Custom batch size
        """
    )
    parser.add_argument(
        "--max-profiles", type=int, default=None,
        help="Maximum profiles to scrape (0 = all, default from .env)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=None,
        help="Batch size before pause (default from .env)"
    )
    args = parser.parse_args()
    
    # Get arguments or use defaults from config
    max_profiles = args.max_profiles if args.max_profiles is not None else MAX_PROFILES_PER_RUN
    batch_size = args.batch_size if args.batch_size is not None else BATCH_SIZE
    
    # ========== VALIDATION ==========
    try:
        validate_config()
    except SystemExit:
        return 1
    
    # ========== SHOW HEADER ==========
    if not IS_CI:
        print_header("DamaDam Scraper v4.0 - Modular Edition", {
            "Max Profiles": "All" if max_profiles == 0 else max_profiles,
            "Batch Size": batch_size,
            "Mode": "CI/CD (GitHub Actions)" if IS_CI else "Local Development"
        })
    
    print_separator()
    
    # ========== INITIALIZE BROWSER ==========
    log_msg("[INFO] Initializing Chrome browser...")
    driver = setup_browser()
    if not driver:
        print_error("Failed to initialize browser")
        return 1
    
    try:
        # ========== AUTHENTICATE ==========
        log_msg("[LOGIN] Starting authentication...")
        if not authenticate(driver):
            print_error("Authentication failed - check credentials")
            return 1
        
        # ========== CONNECT TO SHEETS ==========
        log_msg("[INFO] Connecting to Google Sheets...")
        try:
            google_client = authenticate_google()
            sheets = SheetsManager(google_client)
        except SystemExit:
            return 1
        except Exception as e:
            print_error(f"Failed to connect to Google Sheets: {e}")
            return 1
        
        # ========== FETCH PENDING TARGETS ==========
        log_msg("[INFO] Fetching pending targets from RunList...")
        pending_targets = sheets.get_pending_runlist()
        
        if not pending_targets:
            log_msg("[INFO] No pending targets in RunList")
            print_separator()
            return 0
        
        # Limit if max_profiles specified
        if max_profiles > 0:
            targets_to_process = pending_targets[:max_profiles]
            log_msg(f"[INFO] Limited to {max_profiles} profiles (total available: {len(pending_targets)})")
        else:
            targets_to_process = pending_targets
        
        log_msg(f"[INFO] Processing {len(targets_to_process)} profiles")
        print_separator()
        
        # ========== PROCESS TARGETS ==========
        adaptive_delay = AdaptiveDelay(MIN_DELAY, MAX_DELAY)
        start_time = time.time()
        
        stats = {
            'processed': 0,
            'new_profiles': 0,
            'duplicates': 0,
            'errors': 0,
            'success': 0
        }
        
        for idx, target in enumerate(targets_to_process, 1):
            nickname = target['nickname']
            row = target['row']
            
            # Calculate ETA
            eta = calculate_eta(stats['processed'], len(targets_to_process), start_time)
            log_msg(f"[SCRAPING] [{idx}/{len(targets_to_process)}] [{eta}] {nickname}...")
            
            try:
                # Scrape profile
                profile = scrape_profile(driver, nickname)
                
                if not profile:
                    # Scraping failed
                    log_msg(f"[ERROR] Failed to scrape {nickname}")
                    sheets.update_runlist_status(
                        row,
                        TARGET_STATUS_ERROR,
                        f"Scrape failed @ {get_timestamp_full()}"
                    )
                    stats['errors'] += 1
                
                elif sheets.is_duplicate(nickname):
                    # Duplicate found - add note instead of appending
                    existing = sheets.existing_profiles[nickname.lower()]
                    existing_row = existing['row']
                    
                    log_msg(f"[INFO] Duplicate detected: {nickname} (original row {existing_row})")
                    
                    # Add note to the original row
                    note_text = f"Duplicate attempt @ {get_timestamp_full()}"
                    sheets.add_note_to_cell(existing_row, 0, note_text)
                    
                    sheets.update_runlist_status(
                        row,
                        TARGET_STATUS_DONE,
                        f"Duplicate (row {existing_row}) @ {get_timestamp_full()}"
                    )
                    
                    stats['duplicates'] += 1
                
                else:
                    # New profile - append to end
                    result = sheets.append_profile(profile, source=target['source'])
                    
                    if result['status'] == 'new':
                        log_msg(f"[OK] New profile added: {nickname}")
                        sheets.update_runlist_status(
                            row,
                            TARGET_STATUS_DONE,
                            f"New profile @ {get_timestamp_full()}"
                        )
                        stats['new_profiles'] += 1
                    else:
                        print_error(f"Write failed for {nickname}: {result['message']}")
                        sheets.update_runlist_status(
                            row,
                            TARGET_STATUS_ERROR,
                            f"Write failed @ {get_timestamp_full()}"
                        )
                        stats['errors'] += 1
                
                stats['success'] += 1
                
            except KeyboardInterrupt:
                log_msg("[INFO] Interrupted by user")
                sheets.update_runlist_status(
                    row,
                    TARGET_STATUS_PENDING,
                    f"Interrupted @ {get_timestamp_full()}"
                )
                print_separator()
                return 1
            
            except Exception as e:
                log_msg(f"[ERROR] Unexpected error processing {nickname}: {str(e)[:60]}")
                sheets.update_runlist_status(
                    row,
                    TARGET_STATUS_PENDING,
                    f"Error: {str(e)[:40]}"
                )
                stats['errors'] += 1
                stats['success'] += 1
            
            # Update counters
            stats['processed'] += 1
            
            # Batch pause
            if (batch_size > 0 and 
                stats['processed'] % batch_size == 0 and 
                stats['processed'] < len(targets_to_process)):
                adaptive_delay.on_batch_complete()
                log_msg("[INFO] Batch complete, pausing for stability...")
                time.sleep(3)
            
            # Delay before next request
            adaptive_delay.on_success()
            adaptive_delay.sleep()
        
        # ========== FINAL REPORT ==========
        print_separator()
        log_msg("[COMPLETE] Scraping finished")
        log_msg(f"  Total Processed: {stats['processed']}")
        log_msg(f"  New Profiles:    {stats['new_profiles']}")
        log_msg(f"  Duplicates:      {stats['duplicates']}")
        log_msg(f"  Errors:          {stats['errors']}")
        print_separator()
        
        return 0
    
    finally:
        # ========== CLEANUP ==========
        try:
            driver.quit()
            log_msg("[INFO] Browser closed")
        except:
            pass


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
