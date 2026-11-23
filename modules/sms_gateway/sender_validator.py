"""Parsing and structural validation of the SMS command format.

    RADIO#PIN#PRIORITY#MESSAGE

This module only parses and validates *structure*. Looking the sender up
against the whitelist and checking the PIN hash is the caller's job
(see modules/security and services/sms_service.py) — this keeps the
command grammar independent of the database.
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_PRIORITIES = ("NORMAL", "HIGH", "EMERGENCY")
COMMAND_PREFIX = "RADIO"


class CommandFormatError(ValueError):
    """Raised when an SMS body does not match the expected command grammar."""


@dataclass
class ParsedCommand:
    pin: str
    priority: str
    message: str


_THAI_COUNTRY_CODE = "66"


def normalize_phone_number(raw_number: str) -> str:
    """Normalize a phone number for whitelist comparison.

    Numbers arrive in local ("0812345678") or international
    ("+66812345678" / "66812345678") form depending on carrier and
    modem firmware. Caller ID / sender ID can also be spoofed on some
    network paths (CLAUDE.md §8) — this only normalizes for comparison,
    it does not claim to authenticate the sender.
    """
    number = raw_number.strip().replace(" ", "").replace("-", "")
    if number.startswith("+"):
        number = number[1:]
    if number.startswith(_THAI_COUNTRY_CODE) and len(number) > 9:
        number = "0" + number[len(_THAI_COUNTRY_CODE):]
    return number


def parse_command(raw_text: str) -> ParsedCommand:
    if raw_text is None:
        raise CommandFormatError("Empty message")

    parts = raw_text.strip().split("#", 3)
    if len(parts) != 4:
        raise CommandFormatError(
            "Command must match RADIO#PIN#PRIORITY#MESSAGE"
        )

    prefix, pin, priority, message = parts
    if prefix.strip().upper() != COMMAND_PREFIX:
        raise CommandFormatError(f"Unknown command prefix: {prefix!r}")

    pin = pin.strip()
    if not pin or not pin.isdigit():
        raise CommandFormatError("PIN must be numeric")

    priority = priority.strip().upper()
    if priority not in VALID_PRIORITIES:
        raise CommandFormatError(
            f"Priority must be one of {VALID_PRIORITIES}, got {priority!r}"
        )

    message = message.strip()
    if not message:
        raise CommandFormatError("Message body is empty")

    return ParsedCommand(pin=pin, priority=priority, message=message)
