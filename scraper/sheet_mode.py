"""RunList (sheet-driven) scraping workflow."""

from __future__ import annotations

import time
from typing import Dict, Optional

from browser import BrowserSession
from config import (
    BATCH_SIZE,
    IS_CI,
    MAX_DELAY,
    MAX_PROFILES_PER_RUN,
    MIN_DELAY,
    TARGET_STATUS_DONE,
    TARGET_STATUS_ERROR,
)
from core.logger import (
    get_timestamp_full,
    log_msg,
    print_error,
    print_separator,
)
from core.scraper import scrape_profile
from scraper.utils import AdaptiveDelay, calculate_eta
from sheets_manager import SheetsManager, authenticate_google


def run_sheet_mode(
    max_profiles: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> Dict[str, int]:
    """Process pending nicknames from the RunList sheet."""

    max_profiles = MAX_PROFILES_PER_RUN if max_profiles is None else max_profiles
    batch_size = BATCH_SIZE if batch_size is None else batch_size

    log_msg("[INFO] Starting Sheet mode scraping run")

    with BrowserSession(auto_login=True) as driver:
        google_client = authenticate_google()
        sheets = SheetsManager(google_client)

        log_msg("[INFO] Fetching pending targets from RunList...")
        pending_targets = sheets.get_pending_runlist()
        if not pending_targets:
            log_msg("[INFO] No pending targets in RunList. Nothing to do.")
            return {
                "processed": 0,
                "new_profiles": 0,
                "duplicates": 0,
                "errors": 0,
            }

        if max_profiles and max_profiles > 0:
            targets_to_process = pending_targets[:max_profiles]
            log_msg(
                f"[INFO] Limited to {len(targets_to_process)} profiles "
                f"(out of {len(pending_targets)})"
            )
        else:
            targets_to_process = pending_targets

        log_msg(f"[INFO] Processing {len(targets_to_process)} profiles from RunList")
        print_separator()

        adaptive_delay = AdaptiveDelay(MIN_DELAY, MAX_DELAY)
        start_time = time.time()

        stats = {
            "processed": 0,
            "new_profiles": 0,
            "duplicates": 0,
            "errors": 0,
        }

        for idx, target in enumerate(targets_to_process, 1):
            nickname = target["nickname"]
            row = target["row"]

            eta = calculate_eta(stats["processed"], len(targets_to_process), start_time)
            log_msg(f"[SCRAPING] [{idx}/{len(targets_to_process)}] [{eta}] {nickname}...")

            try:
                profile = scrape_profile(driver, nickname)

                if not profile:
                    log_msg(f"[ERROR] Failed to scrape {nickname}")
                    sheets.update_runlist_status(
                        row,
                        TARGET_STATUS_ERROR,
                        f"Scrape failed @ {get_timestamp_full()}",
                    )
                    stats["errors"] += 1

                elif sheets.is_duplicate(nickname):
                    existing = sheets.existing_profiles[nickname.lower()]
                    existing_row = existing["row"]

                    log_msg(
                        f"[INFO] Duplicate detected: {nickname} (original row {existing_row})"
                    )

                    note_text = f"Duplicate attempt @ {get_timestamp_full()}"
                    sheets.add_note_to_cell(existing_row, 0, note_text)
                    sheets.update_runlist_status(
                        row,
                        TARGET_STATUS_DONE,
                        f"Duplicate (row {existing_row}) @ {get_timestamp_full()}",
                    )
                    stats["duplicates"] += 1

                else:
                    result = sheets.append_profile(profile, source=target["source"])

                    if result["status"] == "new":
                        log_msg(f"[OK] New profile added: {nickname}")
                        sheets.update_runlist_status(
                            row,
                            TARGET_STATUS_DONE,
                            f"New profile @ {get_timestamp_full()}",
                        )
                        stats["new_profiles"] += 1
                    else:
                        print_error(f"Write failed for {nickname}: {result['message']}")
                        sheets.update_runlist_status(
                            row,
                            TARGET_STATUS_ERROR,
                            f"Write failed @ {get_timestamp_full()}",
                        )
                        stats["errors"] += 1

            except KeyboardInterrupt:
                log_msg("[INFO] Interrupted by user")
                sheets.update_runlist_status(
                    row,
                    TARGET_STATUS_ERROR,
                    f"Interrupted @ {get_timestamp_full()}",
                )
                raise
            except Exception as exc:  # pragma: no cover - defensive logging
                log_msg(
                    f"[ERROR] Unexpected error processing {nickname}: {str(exc)[:60]}"
                )
                sheets.update_runlist_status(
                    row,
                    TARGET_STATUS_ERROR,
                    f"Error: {str(exc)[:40]}",
                )
                stats["errors"] += 1

            stats["processed"] += 1

            if (
                batch_size > 0
                and stats["processed"] % batch_size == 0
                and stats["processed"] < len(targets_to_process)
            ):
                adaptive_delay.on_batch_complete()
                log_msg("[INFO] Batch complete, pausing for stability...")
                time.sleep(3)

            adaptive_delay.on_success()
            adaptive_delay.sleep()

        print_separator()
        log_msg("[COMPLETE] Sheet mode scraping finished")
        log_msg(f"  Total Processed: {stats['processed']}")
        log_msg(f"  New Profiles:    {stats['new_profiles']}")
        log_msg(f"  Duplicates:      {stats['duplicates']}")
        log_msg(f"  Errors:          {stats['errors']}")
        print_separator()

        return stats
