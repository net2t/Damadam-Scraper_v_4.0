"""
================================================================================
LOGGER.PY - LOGGING & CONSOLE OUTPUT
================================================================================
PURPOSE: Centralized logging system with rich formatting for console output.
         Handles different log levels (INFO, OK, ERROR, SCRAPING, etc.)

FEATURES:
  - Color-coded messages based on log type
  - Emoji icons for visual distinction
  - Timestamp formatting (PKT timezone)
  - CI/CD mode support (plain text output for GitHub Actions)
  - Rich console formatting for local development
================================================================================
"""

import sys
import warnings
from datetime import datetime, timedelta, timezone
from colorama import Fore, Style, init as colorama_init
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from pathlib import Path

# Initialize colorama for Windows compatibility
colorama_init(autoreset=True)

# Rich console for fancy formatting
console = Console()

# Import to check if CI/CD mode
import os
IS_CI = bool(os.getenv('GITHUB_ACTIONS'))

# Try to get config, fallback if not available yet
try:
    from .config import IS_CI as CONFIG_IS_CI
    IS_CI = CONFIG_IS_CI
except ImportError:
    pass

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ==================== TIME UTILITIES ====================

def get_pkt_time():
    """
    PURPOSE: Get current time in Pakistan Standard Time (UTC+5)
    
    LOGIC:
      - Get current UTC time
      - Add 5 hours for PKT timezone
      - Remove timezone info for compatibility
    
    RETURNS:
      datetime: Current time in PKT
    """
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)


def get_timestamp_short():
    """
    PURPOSE: Get short timestamp format (HH:MM:SS)
    
    RETURNS:
      str: Formatted time string
    """
    return get_pkt_time().strftime('%H:%M:%S')


def get_timestamp_full():
    """
    PURPOSE: Get full timestamp format (DD-MMM-YY HH:MM AM/PM)
    
    RETURNS:
      str: Formatted time string
    """
    return get_pkt_time().strftime('%d-%b-%y %I:%M %p')

# ==================== LOGGING FUNCTIONS ====================

def log_msg(message: str, style: str = None):
    """
    PURPOSE: Log a message with automatic level detection and formatting
    
    LOGIC:
      - Parse message for log level indicators ([OK], [ERROR], etc.)
      - Assign color and emoji based on level
      - Output to console with formatting or plain text (if CI/CD)
    
    ARGS:
      message (str): Message to log
      style (str, optional): Rich style override
    
    RETURNS:
      None
    """
    ts = get_timestamp_short()
    text = str(message)
    detected_style = style
    icon = "ℹ️ "  # Added space after info emoji
    
    # Auto-detect log level from message content
    upper = text.upper()
    if "[OK]" in upper:
        detected_style = "green"
        icon = "✅"
    elif "[ERROR]" in upper or "FATAL" in upper:
        detected_style = "red"
        icon = "❌"
    elif "[SCRAPING]" in upper:
        detected_style = "cyan"
        icon = "🕵️"
    elif "[TIMEOUT]" in upper:
        detected_style = "yellow"
        icon = "⏱️"
    elif "[BROWSER_ERROR]" in upper:
        detected_style = "red"
        icon = "🧯"
    elif "[COMPLETE]" in upper:
        detected_style = "magenta"
        icon = "🏁"
    elif "[API]" in upper:
        detected_style = "blue"
        icon = "🌐"
    elif "[LOGIN]" in upper:
        detected_style = "cyan"
        icon = "🔐"
    
    # Output format based on environment
    if IS_CI:
        # Plain text for GitHub Actions
        print(f"[{ts}] {text}")
        sys.stdout.flush()
    else:
        # Rich formatting for local development
        console.print(f"[bold]{ts}[/bold] {icon}  {text}", style=detected_style)


def print_header(title: str, data: dict = None):
    """
    PURPOSE: Print a formatted header panel with configuration/status info
    
    LOGIC:
      - Create a table grid layout
      - Add title and data rows
      - Display as a rich panel
    
    ARGS:
      title (str): Header title
      data (dict, optional): Key-value pairs to display
    
    RETURNS:
      None
    """
    if IS_CI:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}")
        if data:
            for key, value in data.items():
                print(f"  {key}: {value}")
        return
    
    header = Table.grid(padding=(0, 2))
    header.add_column(justify="left")
    header.add_row(title)
    if data:
        for key, value in data.items():
            header.add_row(f"{key}: {value}")
    
    console.print(Panel(header, title=title, border_style="magenta"))


def print_separator(char: str = "="):
    """
    PURPOSE: Print a separator line for visual clarity
    
    ARGS:
      char (str): Character to use for separator
    
    RETURNS:
      None
    """
    print(char * 70)


def print_success(message: str):
    """
    PURPOSE: Print a success message with green styling
    
    ARGS:
      message (str): Success message
    
    RETURNS:
      None
    """
    log_msg(f"[OK] {message}")


def print_error(message: str):
    """
    PURPOSE: Print an error message with red styling
    
    ARGS:
      message (str): Error message
    
    RETURNS:
      None
    """
    log_msg(f"[ERROR] {message}")


def print_info(message: str):
    """
    PURPOSE: Print an info message
    
    ARGS:
      message (str): Info message
    
    RETURNS:
      None
    """
    log_msg(f"[INFO] {message}")
