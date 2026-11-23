"""Background call monitor for the SIM7600 phone-call gateway.

Listens for RING / +CLIP unsolicited notifications on the shared AT
command channel, hands the caller ID to a callback (which validates it
against the whitelist and triggers the matching canned call command),
then rejects/hangs up the call. The system never answers a call or
opens a microphone (CLAUDE.md §9 functional requirement #10).

The URC handlers run on the AtCommandManager's reader thread and must
never call `send_command` directly (that would deadlock waiting for a
response only that same thread can deliver) — so they only enqueue
work for a dedicated worker thread, same pattern as the SMS reader.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
from typing import Callable, Optional

from modules.sms_gateway.modem import AtCommandError, AtCommandManager

logger = logging.getLogger(__name__)

RING_PATTERN = r"RING"
CLIP_PATTERN = r'\+CLIP:\s*"([^"]*)"'
_CLIP_RE = re.compile(CLIP_PATTERN)

OnCallCallback = Callable[[str], None]


class CallMonitor:
    def __init__(
        self,
        at_manager: AtCommandManager,
        on_incoming_call: OnCallCallback,
        auto_reject: bool = True,
    ) -> None:
        self._at = at_manager
        self._on_incoming_call = on_incoming_call
        self._auto_reject = auto_reject
        self._caller_queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._current_call_handled = False

    def initialize(self) -> None:
        self._at.register_urc_handler(RING_PATTERN, self._on_ring_line)
        self._at.register_urc_handler(CLIP_PATTERN, self._on_clip_line)
        try:
            self._at.send_command("AT+CLIP=1")
        except AtCommandError as exc:
            logger.error("Call monitor init command AT+CLIP=1 failed: %s", exc)

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._process_queue, name="call-monitor-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._caller_queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _on_ring_line(self, line: str) -> None:
        # RING alone carries no caller ID; +CLIP (sent alongside each RING
        # while the SIM module has AT+CLIP=1 enabled) carries the number.
        return

    def _on_clip_line(self, line: str) -> None:
        match = _CLIP_RE.match(line)
        if not match:
            return
        if self._current_call_handled:
            return
        self._current_call_handled = True
        self._caller_queue.put(match.group(1))

    def _process_queue(self) -> None:
        while not self._stop_event.is_set():
            caller_number = self._caller_queue.get()
            if caller_number is None:
                continue
            self._handle_call(caller_number)

    def _handle_call(self, caller_number: str) -> None:
        try:
            self._on_incoming_call(caller_number)
        except Exception:
            logger.exception("on_incoming_call handler failed for %s", caller_number)
        finally:
            if self._auto_reject:
                self._reject_call()
            self._current_call_handled = False

    def _reject_call(self) -> None:
        try:
            self._at.send_command("AT+CHUP", timeout=5.0)
        except AtCommandError as exc:
            logger.error("Failed to hang up/reject call: %s", exc)
