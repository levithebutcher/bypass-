"""Custom exceptions for the bypasser subsystem."""


class BypassError(Exception):
    """Base exception for all bypass errors."""
    pass


class LinkDeadError(BypassError):
    """Raised when the original short link is dead or returned 404."""
    pass


class CaptchaRequiredError(BypassError):
    """Raised when a manual interactive captcha is required to proceed."""
    pass


class UnsupportedSiteError(BypassError):
    """Raised when a link is not supported and generic solver fails."""
    pass


class SafetyBlockedError(BypassError):
    """Raised when the destination target is a dangerous executable file."""
    pass
