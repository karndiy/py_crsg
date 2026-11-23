"""Phone number normalization for matching caller ID against the whitelist.

Re-exports the shared implementation from modules.sms_gateway so SMS
and call validation always normalize numbers the same way.
"""

from __future__ import annotations

from modules.sms_gateway.sender_validator import normalize_phone_number

__all__ = ["normalize_phone_number", "numbers_match"]


def numbers_match(candidate: str, whitelisted: str) -> bool:
    return normalize_phone_number(candidate) == normalize_phone_number(whitelisted)
