"""Bypassers package exposing BypasserManager and base abstractions."""

from bypassers.base import BaseBypasser
from bypassers.manager import bypasser_manager, BypasserManager
from bypassers.exceptions import (
    BypassError,
    LinkDeadError,
    CaptchaRequiredError,
    UnsupportedSiteError,
    SafetyBlockedError,
)

__all__ = [
    "BaseBypasser",
    "bypasser_manager",
    "BypasserManager",
    "BypassError",
    "LinkDeadError",
    "CaptchaRequiredError",
    "UnsupportedSiteError",
    "SafetyBlockedError",
]
