"""Online list scraping workflow."""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

from browser import BrowserSession
from config import MAX_DELAY, MIN_DELAY, ONLINE_USERS_URL
from core.logger import get_timestamp_full, log_msg, print_error
from core.scraper import scrape_profile
from scraper.utils import AdaptiveDelay
from sheets_manager import SheetsManager, authenticate_google


def fetch_online_nicknames(url: str = ONLINE_USERS_URL, timeout: int = 20) -> List[str]:
    """Fetch the current list of online nicknames from damadam.pk."""
    log_msg("[INFO] Fetching online users list...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise RuntimeError(f"Failed to fetch online user list: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    nicknames = []

    for tag in soup.select("li bdi"):
        nickname = tag.get_text(strip=True)
        if nickname:
            nicknames.append(nickname)

    # Preserve order but remove duplicates
    ordered = list(OrderedDict.fromkeys(nicknames))
    log_msg(f"[INFO] Found {len(ordered)} online nicknames")
    return ordered


def run_online_mode(
    *,
    nicknames: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, int]:
    """Scrape profiles for online users and log their presence."""

    if nicknames:
        queue = [name.strip() for name in nicknames if name and name.strip()]
        log_msg(f"[INFO] Using provided nicknames list ({len(queue)} entries)")
    else:
        queue = fetch_online_nicknames()

    if limit is not None and limit > 0:
        queue = queue[:limit]
        log_msg(f"[INFO] Limiting online scrape to first {len(queue)} users")

    if not queue:
        log_msg("[INFO] No online users detected, nothing to do")
        return {
            "processed": 0,
            "new_profiles": 0,
            "duplicates": 0,
            "errors": 0,
        }

    google_client = authenticate_google()
    sheets = SheetsManager(google_client)

    stats = {
        "processed": 0,
        "new_profiles": 0,
        "duplicates": 0,
        "errors": 0,
    }

    adaptive_delay = AdaptiveDelay(MIN_DELAY, MAX_DELAY)

    with BrowserSession(auto_login=True) as driver:
        for nickname in queue:
            log_msg(f"[SCRAPING] Processing online nickname: {nickname}")
            sheets.log_online_presence(nickname)

            if sheets.is_duplicate(nickname):
                log_msg(
                    f"[INFO] {nickname} already exists in Profiles sheet; presence logged"
                )
                stats["duplicates"] += 1
                continue

            profile = scrape_profile(driver, nickname)
            if not profile:
                print_error(f"Failed to scrape profile for {nickname}")
                stats["errors"] += 1
                continue

            profile_result = sheets.append_profile(profile, source="Online")
            if profile_result.get("status") == "new":
                stats["new_profiles"] += 1
                log_msg(f"[OK] Profile stored for {nickname} (Online mode)")
            else:  # Defensive branch; append_profile returns status even if not "new"
                log_msg(
                    f"[INFO] Profile for {nickname} stored with status {profile_result.get('status')}"
                )

            stats["processed"] += 1
            adaptive_delay.on_success()
            adaptive_delay.sleep()

    log_msg("[COMPLETE] Online mode scraping finished")
    log_msg(f"  New Profiles: {stats['new_profiles']}")
    log_msg(f"  Duplicates:   {stats['duplicates']}")
    log_msg(f"  Errors:       {stats['errors']}")
    return stats
