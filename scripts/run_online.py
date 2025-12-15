#!/usr/bin/env python3
"""
Run the Damadam Scraper in Online mode.
Accepts nicknames as command-line arguments.
"""

import sys
from core.scraper import DamadamScraper
from core.logger import log_msg

def main():
    if len(sys.argv) < 2:
        log_msg("[ERROR] Please provide nicknames as command-line arguments")
        return
        
    nicknames = [n.strip() for n in sys.argv[1].split(',')]
    log_msg(f"[INFO] Starting Online scraper for {len(nicknames)} profiles")
    
    try:
        scraper = DamadamScraper()
        
        for nickname in nicknames:
            try:
                log_msg(f"[SCRAPING] Processing {nickname}...")
                # Your existing scraping logic here
                pass
                
            except Exception as e:
                log_msg(f"[ERROR] Error processing {nickname}: {str(e)}")
                continue
                
    except Exception as e:
        log_msg(f"[ERROR] Fatal error in Online scraper: {str(e)}")
        raise

if __name__ == "__main__":
    main()