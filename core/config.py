"""Compatibility shim exposing the new top-level :mod:`config` module.

This file keeps backward compatibility for legacy imports (``from core import
validate_config`` or ``from core.config import DAMADAM_USERNAME``) while the
project transitions to the flattened layout requested by the user.  All
symbols are re-exported from the new :mod:`config` module.
"""

from config import *  # type: ignore  # noqa: F401,F403