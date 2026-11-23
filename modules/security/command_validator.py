"""Validation rules for incoming announcement commands that don't belong
to command-grammar parsing (modules/sms_gateway/sender_validator.py) or
PIN checking (models.AuthorizedSender): message length and duplicate
detection.
"""

from __future__ import annotations

import hashlib


class MessageTooLongError(ValueError):
    pass


def validate_message_length(message: str, max_length: int) -> None:
    if len(message) > max_length:
        raise MessageTooLongError(
            f"Message is {len(message)} characters, exceeds limit of {max_length}"
        )


def compute_duplicate_key(sender: str, message: str) -> str:
    digest_input = f"{sender}:{message}".encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()
