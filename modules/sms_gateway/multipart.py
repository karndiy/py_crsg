"""Reassembly of concatenated (multipart) SMS messages."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from modules.sms_gateway.pdu_decoder import DecodedSms

PartKey = Tuple[str, int, int]  # sender, concatenation reference, total_parts


@dataclass
class _PendingGroup:
    parts: Dict[int, DecodedSms] = field(default_factory=dict)
    first_seen: float = field(default_factory=time.monotonic)


class MultipartReassembler:
    """Collects concatenated SMS parts and reassembles them once complete.

    Thread-safe: the SMS reader worker calls `add_part` from a single
    background thread in practice, but the lock makes it safe even if a
    housekeeping/timeout sweep runs concurrently.
    """

    def __init__(self, timeout_seconds: int = 300) -> None:
        self._timeout_seconds = timeout_seconds
        self._pending: Dict[PartKey, _PendingGroup] = {}
        self._lock = threading.Lock()

    def add_part(self, sms: DecodedSms) -> Optional[DecodedSms]:
        """Add a decoded SMS part. Returns the reassembled DecodedSms once
        every segment has arrived, otherwise None.
        """
        if sms.concatenation is None:
            return sms

        key: PartKey = (sms.sender, sms.concatenation.reference, sms.concatenation.total_parts)
        with self._lock:
            group = self._pending.setdefault(key, _PendingGroup())
            group.parts[sms.concatenation.sequence] = sms

            if len(group.parts) < sms.concatenation.total_parts:
                return None

            ordered = [group.parts[i] for i in sorted(group.parts)]
            del self._pending[key]

        combined_text = "".join(part.text for part in ordered)
        first = ordered[0]
        return DecodedSms(
            sender=first.sender,
            timestamp=first.timestamp,
            encoding=first.encoding,
            text=combined_text,
            concatenation=first.concatenation,
            raw_pdu="|".join(part.raw_pdu for part in ordered),
        )

    def sweep_expired(self) -> List[PartKey]:
        """Drop groups that have been incomplete for longer than the
        configured timeout. Returns the keys that were dropped so the
        caller can log/record them.
        """
        now = time.monotonic()
        expired: List[PartKey] = []
        with self._lock:
            for key, group in list(self._pending.items()):
                if now - group.first_seen >= self._timeout_seconds:
                    expired.append(key)
                    del self._pending[key]
        return expired

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)
