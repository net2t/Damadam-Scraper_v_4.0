"""High-level scraping modes exposed for the DamaDam scraper."""

from .sheet_mode import run_sheet_mode
from .online_mode import run_online_mode, fetch_online_nicknames

__all__ = [
    "run_sheet_mode",
    "run_online_mode",
    "fetch_online_nicknames",
]
