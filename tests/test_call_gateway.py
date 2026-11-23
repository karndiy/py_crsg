from dataclasses import dataclass
from typing import Optional

import pytest

from modules.call_gateway.call_command import CallCommandError, resolve_call_command
from modules.call_gateway.caller_validator import normalize_phone_number, numbers_match


@dataclass
class FakeSender:
    phone_number: str
    is_active: bool = True
    can_call: bool = True
    default_call_command_id: Optional[int] = 1


@dataclass
class FakeCommand:
    command_code: str
    announcement_text: str
    is_active: bool = True


def test_resolve_call_command_success():
    sender = FakeSender(phone_number="0812345678")
    command = FakeCommand(command_code="CALL_001", announcement_text="Daily announcement")

    result = resolve_call_command(sender, lambda command_id: command)

    assert result.command_code == "CALL_001"
    assert result.announcement_text == "Daily announcement"


def test_resolve_call_command_rejects_disabled_sender():
    sender = FakeSender(phone_number="0812345678", is_active=False)
    with pytest.raises(CallCommandError):
        resolve_call_command(sender, lambda command_id: FakeCommand("X", "Y"))


def test_resolve_call_command_rejects_sender_without_call_rights():
    sender = FakeSender(phone_number="0812345678", can_call=False)
    with pytest.raises(CallCommandError):
        resolve_call_command(sender, lambda command_id: FakeCommand("X", "Y"))


def test_resolve_call_command_rejects_missing_command():
    sender = FakeSender(phone_number="0812345678")
    with pytest.raises(CallCommandError):
        resolve_call_command(sender, lambda command_id: None)


def test_resolve_call_command_rejects_inactive_command():
    sender = FakeSender(phone_number="0812345678")
    command = FakeCommand(command_code="CALL_001", announcement_text="X", is_active=False)
    with pytest.raises(CallCommandError):
        resolve_call_command(sender, lambda command_id: command)


def test_caller_id_normalization_matches_whitelist_formats():
    assert numbers_match("+66812345678", "0812345678")
    assert normalize_phone_number("66812345678") == "0812345678"
