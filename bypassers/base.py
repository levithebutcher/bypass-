"""Base class for all shortener bypasser plugins."""

from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlparse


class BaseBypasser(ABC):
    """
    Abstract base class for all link bypassers.
    Each plugin in bypassers/ implements this interface.
    """

    # Human-readable name of the service
    name: str = "Unknown"
    
    # Priority for matching (higher number = checked earlier; default 10)
    priority: int = 10

    # List of primary domain patterns or hostnames handled by this plugin
    domains: List[str] = []

    def match(self, url: str) -> bool:
        """
        Determines if the given URL should be processed by this plugin.
        Default implementation checks hostname against self.domains.
        Subclasses can override with custom regex matching.
        """
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
            return any(
                hostname == d.lower() or hostname.endswith("." + d.lower())
                for d in self.domains
            )
        except Exception:
            return False

    @abstractmethod
    async def bypass(self, url: str) -> str:
        """
        Executes the bypass flow for the given shortener link.
        Returns the resolved final destination URL.
        Raises BypassError (or subclass) on failure.
        """
        pass
