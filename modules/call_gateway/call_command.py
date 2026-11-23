"""Resolves which canned call command an authorized caller triggers.

Calling in cannot submit new free-form announcement text (CLAUDE.md
§9 "Call Command Design") — it can only trigger a pre-configured canned
command. DB access is kept out of this module (a `command_lookup`
callable is passed in) so the resolution logic is unit-testable without
a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Protocol


class CallCommandError(ValueError):
    pass


class AuthorizedSenderLike(Protocol):
    phone_number: str
    is_active: bool
    can_call: bool
    default_call_command_id: Optional[int]


class CallCommandLike(Protocol):
    command_code: str
    announcement_text: str
    is_active: bool


@dataclass
class CallTriggerResult:
    command_code: str
    announcement_text: str


def resolve_call_command(
    sender: AuthorizedSenderLike,
    command_lookup: Callable[[int], Optional[CallCommandLike]],
) -> CallTriggerResult:
    if not sender.is_active:
        raise CallCommandError(f"{sender.phone_number} is disabled")
    if not sender.can_call:
        raise CallCommandError(f"{sender.phone_number} is not authorized for calls")
    if sender.default_call_command_id is None:
        raise CallCommandError(f"{sender.phone_number} has no call command configured")

    command = command_lookup(sender.default_call_command_id)
    if command is None or not command.is_active:
        raise CallCommandError("Configured call command is missing or inactive")

    return CallTriggerResult(
        command_code=command.command_code,
        announcement_text=command.announcement_text,
    )
