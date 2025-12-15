"""
================================================================================
SHEETS_MANAGER.PY - HIGH LEVEL GOOGLE SHEETS INTERFACES
================================================================================
PURPOSE: Provide a single import point for Google Sheets authentication and
         helper utilities.  Internally this simply re-exports the battle-tested
         implementation that lives in ``core.sheets`` while giving the project
         the flatter structure requested by the user.
================================================================================
"""

from core.sheets import authenticate_google, SheetsManager

__all__ = ["authenticate_google", "SheetsManager"]
