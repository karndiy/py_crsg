"""Background SMS reader worker.

Watches for +CMTI unsolicited notifications (and sweeps for anything
already stored on the SIM at startup), reads each message with
AT+CMGR, decodes it, and hands it to the caller-supplied callback.

Must run as a background worker/thread, never inside a Flask request
handler (see CLAUDE.md architectural requirements).
"""

from __future__ import annotations

import logging
import queue
import re
import threading
from typing import Callable, List, Optional

from modules.sms_gateway.modem import AtCommandError, AtCommandManager
from modules.sms_gateway.pdu_decoder import DecodedSms, PduDecodeError, decode_pdu

logger = logging.getLogger(__name__)

CMTI_PATTERN = r'\+CMTI:\s*"(\w+)",(\d+)'
_CMTI_RE = re.compile(CMTI_PATTERN)
_CMGL_INDEX_RE = re.compile(r"\+CMGL:\s*(\d+)")

OnMessageCallback = Callable[[DecodedSms, int], None]


class SmsReaderWorker:
    def __init__(
        self,
        at_manager: AtCommandManager,
        on_message: OnMessageCallback,
        auto_delete: bool = True,
    ) -> None:
        self._at = at_manager
        self._on_message = on_message
        self._auto_delete = auto_delete
        self._index_queue: "queue.Queue[Optional[int]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def initialize(self) -> None:
        """Run modem init commands and pick up any SMS already waiting
        on the SIM. Call once after the shared AtCommandManager is
        connected, before start().
        """
        self._at.register_urc_handler(CMTI_PATTERN, self._on_cmti_line)
        for command in ("AT", "AT+CPIN?", "AT+CMGF=0", "AT+CNMI=2,1,0,0,0"):
            try:
                self._at.send_command(command)
            except AtCommandError as exc:
                logger.error("SMS reader init command %r failed: %s", command, exc)
        self._enqueue_existing_messages()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._process_queue, name="sms-reader-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._index_queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _on_cmti_line(self, line: str) -> None:
        match = _CMTI_RE.match(line)
        if match:
            self._index_queue.put(int(match.group(2)))

    def _enqueue_existing_messages(self) -> None:
        try:
            lines = self._at.send_command("AT+CMGL=4", timeout=10.0)
        except AtCommandError as exc:
            logger.warning("Could not list existing SMS on startup: %s", exc)
            return
        for line in lines:
            match = _CMGL_INDEX_RE.match(line)
            if match:
                self._index_queue.put(int(match.group(1)))

    def _process_queue(self) -> None:
        while not self._stop_event.is_set():
            index = self._index_queue.get()
            if index is None:
                continue
            self._read_and_handle(index)

    def _read_and_handle(self, index: int) -> None:
        try:
            lines = self._at.send_command(f"AT+CMGR={index}", timeout=10.0)
        except AtCommandError as exc:
            logger.error("AT+CMGR=%s failed: %s", index, exc)
            return

        pdu_hex = self._extract_pdu(lines)
        if pdu_hex is None:
            logger.error("No PDU payload in AT+CMGR=%s response: %s", index, lines)
            return

        try:
            sms = decode_pdu(pdu_hex)
        except PduDecodeError as exc:
            logger.error("Failed to decode SMS at index %s: %s", index, exc)
            self._maybe_delete(index)
            return

        try:
            self._on_message(sms, index)
        except Exception:
            logger.exception("on_message handler failed for SMS index %s", index)
        finally:
            self._maybe_delete(index)

    def _maybe_delete(self, index: int) -> None:
        if not self._auto_delete:
            return
        try:
            self._at.send_command(f"AT+CMGD={index}")
        except AtCommandError as exc:
            logger.error("Failed to delete SMS index %s: %s", index, exc)

    @staticmethod
    def _extract_pdu(lines: List[str]) -> Optional[str]:
        for line in lines:
            stripped = line.strip()
            if stripped and re.fullmatch(r"[0-9A-Fa-f]+", stripped):
                return stripped
        return None
