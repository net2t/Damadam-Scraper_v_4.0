"""
================================================================================
SHEETS.PY - GOOGLE SHEETS OPERATIONS
================================================================================
PURPOSE: Handle all Google Sheets API interactions including authentication,
         reading/writing data, and managing profile/target sheet operations.

FEATURES:
  - Google Sheets API authentication (file + raw JSON)
  - Read/write profile data with duplicate detection
  - Manage RunList (targets) with status tracking
  - Add notes to cells for tracking changes
  - Dynamic sheet creation if missing
================================================================================
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from gspread import Spreadsheet, Worksheet
from gspread.exceptions import WorksheetNotFound, APIError
from google.oauth2.service_account import Credentials

try:
    from .config import (
        GOOGLE_SHEET_URL, GOOGLE_CRED_PATH, GOOGLE_CREDENTIALS_JSON,
        SHEET_PROFILES, SHEET_RUNLIST, SHEET_ONLINE_LOG,
        COLUMN_ORDER, COLUMN_TO_INDEX,
        TARGET_STATUS_PENDING, TARGET_STATUS_DONE, TARGET_STATUS_ERROR,
        STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_BANNED,
        SHEET_WRITE_DELAY, SCRIPT_DIR
    )
    from .logger import log_msg, print_error, get_timestamp_full, get_pkt_time
except ImportError:
    from core.config import (
        GOOGLE_SHEET_URL, GOOGLE_CRED_PATH, GOOGLE_CREDENTIALS_JSON,
        SHEET_PROFILES, SHEET_RUNLIST, SHEET_ONLINE_LOG,
        COLUMN_ORDER, COLUMN_TO_INDEX,
        TARGET_STATUS_PENDING, TARGET_STATUS_DONE, TARGET_STATUS_ERROR,
        STATUS_VERIFIED, STATUS_UNVERIFIED, STATUS_BANNED,
        SHEET_WRITE_DELAY, SCRIPT_DIR
    )
    from core.logger import log_msg, print_error, get_timestamp_full, get_pkt_time

import gspread

# ==================== GOOGLE AUTH ====================

def authenticate_google():
    """
    PURPOSE: Authenticate with Google Sheets API using service account.
             Supports both local credentials file and GitHub Secrets raw JSON.
    
    LOGIC:
      - Check if local credentials.json exists
      - Fall back to raw JSON from environment variable
      - Authorize gspread client with required scopes
      - Return authenticated client
    
    RETURNS:
      gspread.Client: Authenticated Sheets client
    
    RAISES:
      SystemExit: If credentials not found or authentication fails
    """
    try:
        log_msg("[INFO] Authenticating with Google Sheets API...")
        
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = None
        cred_source = None
        
        # Try local credentials file first
        if GOOGLE_CRED_PATH and Path(GOOGLE_CRED_PATH).exists():
            log_msg(f"[INFO] Using credentials from: {GOOGLE_CRED_PATH}")
            credentials = Credentials.from_service_account_file(
                GOOGLE_CRED_PATH, scopes=scope
            )
            cred_source = "local file"
        
        # Fall back to raw JSON from environment
        elif GOOGLE_CREDENTIALS_JSON:
            log_msg("[INFO] Using credentials from GitHub Secrets")
            cred_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
            credentials = Credentials.from_service_account_info(cred_dict, scopes=scope)
            cred_source = "GitHub Secrets"
        
        else:
            print_error(
                f"Google credentials not found.\n"
                f"  Checked: {GOOGLE_CRED_PATH}\n"
                f"  Also checked: GOOGLE_CREDENTIALS_JSON env var"
            )
            exit(1)
        
        client = gspread.authorize(credentials)
        log_msg(f"[OK] Google Sheets authenticated ({cred_source})")
        return client
        
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in credentials: {e}")
        exit(1)
    except Exception as e:
        print_error(f"Google authentication failed: {e}")
        exit(1)


# ==================== SHEETS MANAGER CLASS ====================

class SheetsManager:
    """
    PURPOSE: Centralized manager for all Google Sheets operations.
             Handles profiles, targets, and sheet structure.
    
    ATTRIBUTES:
      client (gspread.Client): Authenticated Sheets API client
      ss (Spreadsheet): Active Google Spreadsheet
      profiles_ws (Worksheet): "Profiles" sheet
      runlist_ws (Worksheet): "RunList" sheet (targets)
      existing_profiles (dict): Cache of existing profiles by nickname
    """
    
    def __init__(self, client):
        """
        PURPOSE: Initialize SheetsManager and prepare all worksheets.
        
        LOGIC:
          - Open spreadsheet by URL
          - Create/fetch required worksheets
          - Initialize headers if missing
          - Load existing profiles into memory cache
          - Load tags mapping from Tags sheet (optional)
          - Apply formatting (font, colors, alignment)
        """
        log_msg("[INFO] Initializing Google Sheets manager...")
        
        self.client = client
        self.ss = client.open_by_url(GOOGLE_SHEET_URL)
        
        # Get or create worksheets
        self.profiles_ws = self._get_or_create_sheet(SHEET_PROFILES)
        self.runlist_ws = self._get_or_create_sheet(SHEET_RUNLIST)
        self.online_log_ws = self._get_or_create_sheet(SHEET_ONLINE_LOG)

        # Try to get Tags sheet (optional)
        self.tags_ws = self._get_sheet_if_exists("Tags")
        
        # Initialize headers
        self._init_profiles_headers()
        self._init_runlist_headers()
        self._init_online_log_headers()
        
        # Load tags mapping from Tags sheet
        self.tags_mapping = {}
        if self.tags_ws:
            self._load_tags_mapping()
        
        # Cache existing profiles
        self.existing_profiles = {}
        self._load_existing_profiles()
        
        # Apply formatting to all sheets
        self._apply_formatting()
        
        log_msg("[OK] Sheets manager initialized")
    
    
    def _get_or_create_sheet(self, name: str, rows: int = 1000, cols: int = 20):
        """
        PURPOSE: Get existing worksheet or create new one if missing.
        
        ARGS:
          name (str): Worksheet name
          rows (int): Default rows for new sheet
          cols (int): Default columns for new sheet
        
        RETURNS:
          Worksheet: The requested worksheet
        """
        try:
            return self.ss.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"[INFO] Creating new sheet: {name}")
            return self.ss.add_worksheet(title=name, rows=rows, cols=cols)
    
    
    def _get_sheet_if_exists(self, name: str):
        """
        PURPOSE: Get worksheet if it exists, return None otherwise.
        
        ARGS:
          name (str): Worksheet name
        
        RETURNS:
          Worksheet or None
        """
        try:
            return self.ss.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"[INFO] Optional sheet '{name}' not found (skipping tags)")
            return None
    
    
    def _init_profiles_headers(self):
        """
        PURPOSE: Ensure Profiles sheet has correct headers.
                 Initialize if empty.
        """
        try:
            rows = self.profiles_ws.get_all_values()
            if not rows or not rows[0] or all(not c for c in rows[0]):
                log_msg("[INFO] Initializing Profiles sheet headers...")
                self.profiles_ws.append_row(COLUMN_ORDER)
                time.sleep(SHEET_WRITE_DELAY)
        except Exception as e:
            log_msg(f"[ERROR] Header init failed: {e}")
    
    
    def _init_runlist_headers(self):
        """
        PURPOSE: Ensure RunList sheet has correct headers.
                 Initialize if empty.
        """
        try:
            rows = self.runlist_ws.get_all_values()
            headers = ["Nickname", "Status", "Remarks", "Source"]
            
            if not rows or not rows[0] or all(not c for c in rows[0]):
                log_msg("[INFO] Initializing RunList sheet headers...")
                self.runlist_ws.append_row(headers)
                time.sleep(SHEET_WRITE_DELAY)
        except Exception as e:
            log_msg(f"[ERROR] RunList header init failed: {e}")


    def _init_online_log_headers(self):
        """Ensure OnlineLog sheet has headers for presence tracking."""
        try:
            rows = self.online_log_ws.get_all_values()
            headers = ["DATE", "TIME", "NICKNAME", "DATE/TIME"]

            if not rows or not rows[0] or all(not c for c in rows[0]):
                log_msg("[INFO] Initializing OnlineLog sheet headers...")
                self.online_log_ws.append_row(headers)
                time.sleep(SHEET_WRITE_DELAY)
        except Exception as e:
            log_msg(f"[ERROR] OnlineLog header init failed: {e}")

    
    
    def _load_existing_profiles(self):
        """
        PURPOSE: Load all existing profiles into memory cache for
                 duplicate detection and update logic.
        
        LOGIC:
          - Read all rows from Profiles sheet
          - Index by nickname (lowercase) for quick lookup
          - Store row number and data for updates
        """
        try:
            rows = self.profiles_ws.get_all_values()
            
            # Find nickname column
            if not rows:
                return
            
            headers = rows[0]
            nick_col = COLUMN_TO_INDEX.get("NICK NAME", 0)
            
            # Index profiles by lowercase nickname
            for row_idx, row_data in enumerate(rows[1:], start=2):
                if len(row_data) > nick_col and row_data[nick_col].strip():
                    nickname = row_data[nick_col].strip().lower()
                    self.existing_profiles[nickname] = {
                        'row': row_idx,
                        'data': row_data
                    }
            
            log_msg(f"[OK] Loaded {len(self.existing_profiles)} existing profiles")
            
        except Exception as e:
            log_msg(f"[ERROR] Failed to load existing profiles: {e}")
    
    
    def _load_tags_mapping(self):
        """
        PURPOSE: Load tags from Tags sheet and map to nicknames.
                 Tags sheet format: Each column header is a tag name,
                 and column contains nicknames to assign that tag.
        
        LOGIC:
          - Read all rows from Tags sheet
          - Column header = tag name
          - Column values = nicknames to tag
          - Build mapping: nickname -> "tag1, tag2, tag3"
        
        RETURNS:
          None (updates self.tags_mapping)
        """
        self.tags_mapping = {}
        
        if not self.tags_ws:
            return
        
        try:
            all_values = self.tags_ws.get_all_values()
            
            if not all_values or len(all_values) < 2:
                log_msg("[INFO] Tags sheet is empty")
                return
            
            headers = all_values[0]
            
            # Iterate through each column (each is a tag)
            for col_idx, header in enumerate(headers):
                tag_name = (header or "").strip()
                
                if not tag_name:
                    continue
                
                # Get all nicknames in this column
                for row in all_values[1:]:
                    if col_idx < len(row):
                        nickname = (row[col_idx] or "").strip()
                        
                        if nickname:
                            key = nickname.lower()
                            
                            # Add tag to mapping
                            if key in self.tags_mapping:
                                # If tag already exists, add to list
                                if tag_name not in self.tags_mapping[key]:
                                    self.tags_mapping[key] += f", {tag_name}"
                            else:
                                # Create new tag entry
                                self.tags_mapping[key] = tag_name
            
            log_msg(f"[OK] Loaded {len(self.tags_mapping)} tagged profiles")
            
        except Exception as e:
            log_msg(f"[ERROR] Failed to load tags: {e}")
    
    
    def get_pending_runlist(self):
        """
        PURPOSE: Get all pending targets from RunList sheet.
                 Only returns rows with status exactly "Pending" (case sensitive)
        
        RETURNS:
          list: List of dicts with keys: nickname, row, status, source
        """
        try:
            rows = self.runlist_ws.get_all_values()
            pending = []
            
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) < 2:  # Skip rows that don't have enough columns
                    continue
                    
                nickname = row[0].strip() if row[0] else ''
                status = row[1].strip() if len(row) > 1 else ''
                source = row[3].strip() if len(row) > 3 else 'RunList'
                
                # Only include if status is exactly "Pending"
                is_pending = (status == TARGET_STATUS_PENDING)
                
                if nickname and is_pending:
                    pending.append({
                        'nickname': nickname,
                        'row': idx,
                        'status': status,
                        'source': source
                    })
            
            return pending
            
        except Exception as e:
            log_msg(f"[ERROR] Failed to read RunList: {e}")
            return []
    
    
    def is_duplicate(self, nickname: str):
        """
        PURPOSE: Check if profile already exists by nickname.
        
        ARGS:
          nickname (str): Profile nickname to check
        
        RETURNS:
          bool: True if profile exists, False otherwise
        """
        return nickname.lower() in self.existing_profiles
    
    
    def append_profile(self, profile_data: dict, source: str = "RunList"):
        """
        PURPOSE: Append profile to end of Profiles sheet.
                 ALWAYS appends, even if profile exists (for version tracking).
        
        LOGIC:
          - Apply tags from Tags sheet (if available)
          - Set source from RunList column D
          - Check if duplicate (existing profile with same nickname)
          - If duplicate: append as new row AND add notes to changed fields
          - If new: simply append
          - Return result with change information
        
        ARGS:
          profile_data (dict): Profile data with column names as keys
          source (str): Source value from RunList (default: "RunList")
        
        RETURNS:
          dict: Result with keys: status, row, changed_fields, message
        """
        try:
            # Apply tags if available
            nickname = profile_data.get("NICK NAME", "").strip().lower()
            if nickname in self.tags_mapping:
                profile_data["TAGS"] = self.tags_mapping[nickname]
            
            # Apply source from RunList
            profile_data["SOURCE"] = source
            
            # Build row in correct column order
            row_values = []
            for col in COLUMN_ORDER:
                val = profile_data.get(col, "")
                row_values.append(str(val).strip() if val else "")
            
            # Check if this is a duplicate
            is_duplicate = nickname in self.existing_profiles
            changed_fields = []
            
            if is_duplicate:
                # Get original profile data
                existing = self.existing_profiles[nickname]
                old_data = existing['data']
                
                # Find which fields changed
                for col_idx, col_name in enumerate(COLUMN_ORDER):
                    if col_idx < len(old_data) and col_idx < len(row_values):
                        old_val = (old_data[col_idx] or "").strip()
                        new_val = (row_values[col_idx] or "").strip()
                        
                        # If values differ, record change
                        if old_val != new_val and old_val and new_val:
                            changed_fields.append({
                                'col_idx': col_idx,
                                'col_name': col_name,
                                'old_val': old_val,
                                'new_val': new_val
                            })
            
            # ALWAYS append new row (even if duplicate)
            self.profiles_ws.append_row(row_values)
            time.sleep(SHEET_WRITE_DELAY)
            
            # Get new row number
            all_rows = self.profiles_ws.get_all_values()
            new_row_num = len(all_rows)
            
            # If duplicate with changes, add notes to changed field cells
            if is_duplicate and changed_fields:
                for change in changed_fields:
                    col_idx = change['col_idx']
                    col_name = change['col_name']
                    old_val = change['old_val']
                    new_val = change['new_val']
                    
                    # Add note to the new row at the changed column
                    note_text = f"Changed from: {old_val}\nNew: {new_val}\nTime: {get_timestamp_full()}"
                    self.add_note_to_cell(new_row_num, col_idx, note_text)
                
                status_type = "updated_duplicate"
                message = f"Duplicate appended with {len(changed_fields)} changes"
            elif is_duplicate:
                status_type = "unchanged_duplicate"
                message = "Duplicate appended (no changes)"
            else:
                status_type = "new"
                message = "New profile appended"
            
            # Update cache
            self.existing_profiles[nickname] = {
                'row': new_row_num,
                'data': row_values
            }
            
            return {
                'status': status_type,
                'row': new_row_num,
                'changed_fields': changed_fields,
                'message': message
            }
            
        except Exception as e:
            log_msg(f"[ERROR] Failed to append profile: {e}")
            return {'status': 'error', 'changed_fields': [], 'message': str(e)}


    def log_online_presence(self, nickname: str, timestamp: Optional[datetime] = None):
        """Append a presence entry for an online nickname."""
        try:
            ts = timestamp or get_pkt_time()
            date_str = ts.strftime("%Y-%m-%d")
            time_str = ts.strftime("%H:%M:%S")
            combined = ts.strftime("%d-%b-%y %I:%M %p")
            self.online_log_ws.append_row([date_str, time_str, nickname, combined])
            time.sleep(SHEET_WRITE_DELAY)
            return True
        except Exception as e:
            log_msg(f"[ERROR] Failed to log online nickname '{nickname}': {e}")
            return False

    
    
    def add_note_to_cell(self, row: int, col: int, note_text: str):
        """
        PURPOSE: Add a note to a specific cell to track changes/duplicates.
        
        ARGS:
          row (int): Row number (1-indexed)
          col (int): Column number (0-indexed)
          note_text (str): Note content
        
        RETURNS:
          bool: True if successful
        """
        try:
            reqs = [{
                "updateCells": {
                    "range": {
                        "sheetId": self.profiles_ws.id,
                        "startRowIndex": row - 1,
                        "endRowIndex": row,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1
                    },
                    "rows": [{
                        "values": [{
                            "note": note_text
                        }]
                    }],
                    "fields": "note"
                }
            }]
            
            self.ss.batch_update({"requests": reqs})
            return True
            
        except Exception as e:
            log_msg(f"[ERROR] Failed to add note: {e}")
            return False
    
    
    def _apply_formatting(self):
        """
        PURPOSE: Apply basic formatting to all sheets:
                 - Set column widths
                 - Set text alignment
        
        LOGIC:
          - Get all worksheets
          - Set column widths based on sheet type
          - Set text alignment based on column type
        """
        try:
            log_msg("[INFO] Applying formatting...")
            
            sheets = self.ss.worksheets()
            reqs = []
            
            for ws in sheets:
                sheet_id = ws.id
                
                # Apply Quantico font to all cells
                reqs.append({
                    "repeatCell": {
                        "range": {"sheetId": sheet_id},
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "fontFamily": "Quantico",
                                    "fontSize": 10
                                },
                                "verticalAlignment": "MIDDLE"
                            }
                        },
                        "fields": "userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment"
                    }
                })
                
                # Set column widths and alignments based on sheet type
                if ws.title == "RunList":
                    # Set specific column widths for RunList
                    column_widths = [160, 100, 300, 100]
                    for i, width in enumerate(column_widths):
                        reqs.append({
                            "updateDimensionProperties": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "COLUMNS",
                                    "startIndex": i,
                                    "endIndex": i + 1
                                },
                                "properties": {"pixelSize": width},
                                "fields": "pixelSize"
                            }
                        })
                    
                    # Set specific alignments for RunList columns
                    alignments = ["LEFT", "CENTER", "LEFT", "CENTER"]
                    for i, alignment in enumerate(alignments):
                        reqs.append({
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startColumnIndex": i,
                                    "endColumnIndex": i + 1
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "verticalAlignment": "MIDDLE",
                                        "horizontalAlignment": alignment
                                    }
                                },
                                "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment"
                            }
                        })
                        
                elif ws.title == "Profiles":
                    # Set specific column widths for Profiles sheet
                    column_widths = [180, 92, 140, 100, 70, 36, 80, 50, 70, 50, 40, 90, 150, 40, 100, 40, 40, 40]
                    alignments = ["LEFT", "LEFT", "LEFT", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", 
                                "CENTER", "LEFT", "CENTER", "CENTER", "LEFT", "CENTER", "LEFT", "LEFT", "LEFT"]
                    
                    # Apply column widths
                    for i, width in enumerate(column_widths):
                        reqs.append({
                            "updateDimensionProperties": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "COLUMNS",
                                    "startIndex": i,
                                    "endIndex": i + 1
                                },
                                "properties": {"pixelSize": width},
                                "fields": "pixelSize"
                            }
                        })
                    
                    # Apply column alignments
                    for i, alignment in enumerate(alignments):
                        reqs.append({
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startColumnIndex": i,
                                    "endColumnIndex": i + 1
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "verticalAlignment": "MIDDLE",
                                        "horizontalAlignment": alignment,
                                        "wrapStrategy": "WRAP"
                                    }
                                },
                                "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.wrapStrategy"
                            }
                        })
                        
                elif ws.title == "Tags":
                    # Set column widths for Tags sheet (200px for 4 columns)
                    for i in range(4):  # First 4 columns
                        reqs.append({
                            "updateDimensionProperties": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "COLUMNS",
                                    "startIndex": i,
                                    "endIndex": i + 1
                                },
                                "properties": {"pixelSize": 200},
                                "fields": "pixelSize"
                            }
                        })
                    
                    # Center align all cells in Tags sheet
                    reqs.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "startColumnIndex": 0,
                                "endColumnIndex": 4  # First 4 columns
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "verticalAlignment": "MIDDLE",
                                    "horizontalAlignment": "CENTER"
                                }
                            },
                            "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment"
                        }
                    })
                    
                elif ws.title == SHEET_ONLINE_LOG:
                    column_widths = [100, 80, 180, 140]
                    for i, width in enumerate(column_widths):
                        reqs.append({
                            "updateDimensionProperties": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "COLUMNS",
                                    "startIndex": i,
                                    "endIndex": i + 1
                                },
                                "properties": {"pixelSize": width},
                                "fields": "pixelSize"
                            }
                        })

                    reqs.append({
                        "repeatCell": {
                            "range": {"sheetId": sheet_id},
                            "cell": {
                                "userEnteredFormat": {
                                    "verticalAlignment": "MIDDLE",
                                    "horizontalAlignment": "CENTER",
                                    "wrapStrategy": "WRAP"
                                }
                            },
                            "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.wrapStrategy"
                        }
                    })

                else:
                    # Default formatting for other sheets
                    reqs.append({
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 0,
                                "endIndex": 50
                            },
                            "properties": {"pixelSize": 120},
                            "fields": "pixelSize"
                        }
                    })
                    
                    reqs.append({
                        "repeatCell": {
                            "range": {"sheetId": sheet_id},
                            "cell": {
                                "userEnteredFormat": {
                                    "verticalAlignment": "MIDDLE",
                                    "horizontalAlignment": "LEFT"
                                }
                            },
                            "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment"
                        }
                    })
                # Freeze header row
                reqs.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                })
            
            # Apply all formatting
            if reqs:
                self.ss.batch_update({"requests": reqs})
                log_msg("[OK] Formatting applied to all sheets")
            
        except Exception as e:
            log_msg(f"[ERROR] Formatting failed: {e}")
    
    
    def update_runlist_status(self, row: int, status: str, remarks: str = ""):
        """
        PURPOSE: Update RunList status and remarks for a target.
        
        ARGS:
          row (int): Row number in RunList
          status (str): New status value
          remarks (str, optional): Remarks/notes
        
        RETURNS:
          bool: True if successful
        """
        try:
            # Normalize status value
            status = self._normalize_status(status)
            
            # Retry logic for API quota
            for attempt in range(3):
                try:
                    self.runlist_ws.update(
                        values=[[status]],
                        range_name=f"B{row}"
                    )
                    if remarks:
                        self.runlist_ws.update(
                            values=[[remarks]],
                            range_name=f"C{row}"
                        )
                    time.sleep(SHEET_WRITE_DELAY)
                    return True
                    
                except APIError as e:
                    if '429' in str(e):
                        log_msg("[API] 429 Quota exceeded, waiting 60s...")
                        time.sleep(60)
                    else:
                        raise
            
            return False
            
        except Exception as e:
            log_msg(f"[ERROR] Failed to update status: {e}")
            return False
    
    
    def _normalize_status(self, status: str):
        """
        PURPOSE: Normalize status string to standard values.
        
        ARGS:
          status (str): Input status
        
        RETURNS:
          str: Normalized status
        """
        lower = (status or "").lower().strip()
        
        if "done" in lower or "complete" in lower:
            return TARGET_STATUS_DONE
        elif "error" in lower or "unverified" in lower or "banned" in lower:
            return TARGET_STATUS_ERROR
        else:
            return TARGET_STATUS_PENDING
