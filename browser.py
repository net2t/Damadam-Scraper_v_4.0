"""
================================================================================
BROWSER.PY - HIGH LEVEL BROWSER SESSION MANAGEMENT
================================================================================
PURPOSE: Provide a simplified interface for creating authenticated Selenium
         browser sessions. Wraps the lower-level utilities that live under
         ``core.browser`` and ``core.auth`` while exposing a clean API for the
         reorganised project layout.

FEATURES:
  - Context manager based ``BrowserSession`` for safe setup/teardown
  - Helper to obtain an authenticated driver in a single call
  - Re-exports cookie helpers for convenience
================================================================================
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from core.auth import authenticate as _authenticate
from core.auth import verify_login_status as verify_login_status
from core.browser import clear_cookies, load_cookies, save_cookies
from core.browser import setup_browser as _setup_browser
from core.logger import log_msg, print_error

__all__ = [
    "BrowserSession",
    "get_authenticated_driver",
    "verify_login_status",
    "save_cookies",
    "load_cookies",
    "clear_cookies",
]


class BrowserSession:
    """Context manager that yields an authenticated Selenium driver."""

    def __init__(self, auto_login: bool = True):
        self.auto_login = auto_login
        self.driver = None

    def __enter__(self):
        log_msg("[INFO] Initializing browser session...")
        driver = _setup_browser()
        if not driver:
            raise RuntimeError("Failed to initialize Chrome browser")

        if self.auto_login:
            log_msg("[LOGIN] Starting authentication...")
            if not _authenticate(driver):
                driver.quit()
                raise RuntimeError("Authentication failed - check credentials")

        self.driver = driver
        return driver

    def __exit__(self, exc_type, exc, tb):
        if self.driver:
            try:
                self.driver.quit()
                log_msg("[INFO] Browser closed")
            except Exception:
                pass
            finally:
                self.driver = None
        return False


def get_authenticated_driver(auto_login: bool = True):
    """Return an authenticated Selenium driver (caller must quit)."""
    session = BrowserSession(auto_login=auto_login)
    driver = session.__enter__()

    class _DriverWrapper:
        def __init__(self, drv, session_obj):
            self._driver = drv
            self._session = session_obj

        def __getattr__(self, item):
            return getattr(self._driver, item)

        def quit(self):  # ensures __exit__ logic runs once
            if self._driver:
                try:
                    self._driver.quit()
                    log_msg("[INFO] Browser closed")
                finally:
                    self._driver = None
                    session.__exit__(None, None, None)

    return _DriverWrapper(driver, session)


@contextmanager
def browser_session(auto_login: bool = True) -> Iterator:
    """Yield an authenticated driver using a context manager helper."""
    with BrowserSession(auto_login=auto_login) as driver:
        yield driver
