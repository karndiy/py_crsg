"""Per-sender SMS rate limiting policy.

Counting how many messages a sender has sent in the past hour is a
database query (services/sms_service.py); this module only holds the
decision so it is unit-testable without a database.
"""

from __future__ import annotations


class RateLimitExceededError(ValueError):
    pass


def check_rate_limit(recent_count: int, limit_per_hour: int) -> None:
    if recent_count >= limit_per_hour:
        raise RateLimitExceededError(
            f"Rate limit exceeded: {recent_count} messages already sent this hour "
            f"(limit {limit_per_hour})"
        )
