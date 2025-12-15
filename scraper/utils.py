"""Utility helpers shared across scraper modes."""

from __future__ import annotations

import random
import time
from typing import Optional


class AdaptiveDelay:
    """Adaptive delay system to avoid rate limiting."""

    def __init__(self, min_delay: float, max_delay: float):
        self.base_min = min_delay
        self.base_max = max_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.hits = 0
        self.last_reset = time.time()

    def on_success(self):
        if self.hits > 0:
            self.hits -= 1
        if time.time() - self.last_reset > 10:
            self.min_delay = max(self.base_min, self.min_delay * 0.95)
            self.max_delay = max(self.base_max, self.max_delay * 0.95)
            self.last_reset = time.time()

    def on_batch_complete(self):
        self.min_delay = min(3.0, max(self.base_min, self.min_delay * 1.1))
        self.max_delay = min(6.0, max(self.base_max, self.max_delay * 1.1))

    def sleep(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)


def calculate_eta(processed: int, total: int, start_time: float) -> str:
    """Return a human-readable ETA string."""
    if processed == 0:
        return "Calculating..."

    elapsed = time.time() - start_time
    rate = processed / elapsed if elapsed > 0 else 0
    remaining = max(total - processed, 0)
    eta_seconds = remaining / rate if rate > 0 else 0

    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    if eta_seconds < 3600:
        return f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
    hours = int(eta_seconds // 3600)
    minutes = int((eta_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"
