"""Per-user rate limiter to prevent bot spam."""

import time
from typing import Dict, Tuple
from config import RATE_LIMIT_SECONDS, ADMIN_IDS


class RateLimiter:
    """Tracks user request timestamps and enforces cooldowns."""

    def __init__(self, cooldown: float = RATE_LIMIT_SECONDS):
        self.cooldown = cooldown
        self._user_last_action: Dict[int, float] = {}

    def is_rate_limited(self, user_id: int) -> Tuple[bool, float]:
        """
        Checks if the user must wait before making another request.
        Admins are exempt from rate limiting.
        Returns: (is_limited, remaining_wait_seconds)
        """
        if user_id in ADMIN_IDS:
            return False, 0.0

        current_time = time.monotonic()
        last_time = self._user_last_action.get(user_id, 0.0)
        elapsed = current_time - last_time

        if elapsed < self.cooldown:
            remaining = self.cooldown - elapsed
            return True, remaining

        # Update last action timestamp
        self._user_last_action[user_id] = current_time
        return False, 0.0


# Global singleton instance
rate_limiter = RateLimiter()
