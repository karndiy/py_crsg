"""Serial transport and AT command manager for the SIM7600 modem.

A single AtCommandManager instance must be shared by every part of the
system that talks to the modem (SMS reader, call monitor) so that AT
commands and responses are never interleaved on the shared serial port.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Callable, List, Optional, Protocol

logger = logging.getLogger(__name__)

try:
    import serial  # type: ignore
    import serial.tools.list_ports  # type: ignore
except ImportError:  # pragma: no cover - pyserial is a hard runtime dependency
    serial = None


class ModemConnectionError(RuntimeError):
    """Raised when the serial port cannot be opened or is lost."""


class AtCommandError(RuntimeError):
    """Raised when the modem returns ERROR or times out for a command."""


class ModemTransport(Protocol):
    def open(self) -> None: ...
    def close(self) -> None: ...
    def write_line(self, line: str) -> None: ...
    def read_line(self, timeout: float) -> Optional[str]: ...
    @property
    def is_open(self) -> bool: ...


class SerialModemTransport:
    """Real transport backed by pyserial. Port is never assumed fixed —
    callers must supply the actual device path discovered on the target
    Raspberry Pi (see scripts/detect_modem.py), not a hardcoded default.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> None:
        if serial is None:
            raise ModemConnectionError("pyserial is not installed")
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._conn: Optional["serial.Serial"] = None

    def open(self) -> None:
        try:
            self._conn = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=self._timeout,
                write_timeout=self._timeout,
            )
        except serial.SerialException as exc:
            raise ModemConnectionError(f"Could not open {self._port}: {exc}") from exc

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def write_line(self, line: str) -> None:
        if self._conn is None:
            raise ModemConnectionError("Serial port is not open")
        self._conn.write((line + "\r").encode("utf-8", errors="ignore"))

    def read_line(self, timeout: float) -> Optional[str]:
        if self._conn is None:
            raise ModemConnectionError("Serial port is not open")
        self._conn.timeout = timeout
        raw = self._conn.readline()
        if not raw:
            return None
        return raw.decode("utf-8", errors="ignore").strip()

    @property
    def is_open(self) -> bool:
        return self._conn is not None and self._conn.is_open


class AtCommandManager:
    """Owns the shared serial port and is the *only* thing allowed to read
    or write it.

    A single background thread continuously reads lines from the
    transport. While a command is in flight, lines are routed into that
    command's response buffer; otherwise they are matched against
    registered unsolicited-result-code (URC) handlers (e.g. `+CMTI` for
    new SMS, `RING`/`+CLIP` for incoming calls). This lets the SMS reader
    and the call monitor share one physical port safely, since every
    caller goes through `send_command` and the lock it holds rather than
    touching the transport directly.
    """

    def __init__(self, transport: ModemTransport) -> None:
        self._transport = transport
        self._send_lock = threading.RLock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._urc_handlers: List[tuple[re.Pattern, Callable[[str], None]]] = []

        self._pending_terminators: tuple[str, ...] = ()
        self._pending_lines: Optional[List[str]] = None
        self._response_ready = threading.Event()

    def register_urc_handler(self, pattern: str, handler: Callable[[str], None]) -> None:
        self._urc_handlers.append((re.compile(pattern), handler))

    def connect(self) -> None:
        self._transport.open()
        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._reader_loop, name="at-command-reader", daemon=True
        )
        self._reader_thread.start()

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=5)
            self._reader_thread = None
        self._transport.close()

    @property
    def is_connected(self) -> bool:
        return self._transport.is_open

    def send_command(
        self,
        command: str,
        timeout: float = 5.0,
        terminators: tuple[str, ...] = ("OK", "ERROR"),
    ) -> List[str]:
        """Send a single AT command and block until a terminator line
        ("OK"/"ERROR", or a custom one such as the ">" SMS prompt) is
        seen or the timeout expires.

        Must never be called from within a URC handler running on the
        reader thread itself — that would deadlock waiting for a
        response the reader thread is the only one able to deliver.
        """
        with self._send_lock:
            if not self._transport.is_open:
                raise ModemConnectionError("Modem is not connected")

            self._pending_lines = []
            self._pending_terminators = terminators
            self._response_ready.clear()

            self._transport.write_line(command)

            if not self._response_ready.wait(timeout):
                self._pending_lines = None
                raise AtCommandError(f"Timed out waiting for response to {command!r}")

            lines = self._pending_lines or []
            self._pending_lines = None

            if lines and lines[-1].startswith("ERROR"):
                raise AtCommandError(f"Modem returned ERROR for {command!r}: {lines}")

            return lines

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                line = self._transport.read_line(timeout=0.5)
            except ModemConnectionError:
                logger.error("Lost connection to modem in reader thread")
                return
            if not line:
                continue

            if self._pending_lines is not None:
                self._pending_lines.append(line)
                if any(line.startswith(t) for t in self._pending_terminators):
                    self._response_ready.set()
                continue

            self._dispatch_urc(line)

    def _dispatch_urc(self, line: str) -> None:
        for pattern, handler in self._urc_handlers:
            if pattern.match(line):
                try:
                    handler(line)
                except Exception:
                    logger.exception("URC handler raised for line: %s", line)
                return
        logger.debug("Unhandled line from modem: %s", line)


def discover_serial_ports() -> List[str]:
    """List candidate serial ports on this machine. Used by
    scripts/detect_modem.py — never assume the SIM7600 is on a fixed
    device path such as /dev/ttyUSB2.
    """
    if serial is None:
        return []
    return [p.device for p in serial.tools.list_ports.comports()]
