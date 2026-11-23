"""In-memory ordering layer for announcements waiting on TTS + playback.

This class only decides *order*; persisting queue_status transitions to
the `announcement_queue` table is the caller's job (see
modules/announcement/processor.py), which is what lets the system
recover pending work from SQLite after a restart instead of relying on
whatever happened to still be in memory (CLAUDE.md §18).
"""

from __future__ import annotations

import heapq
import itertools
import threading
from dataclasses import dataclass, field
from typing import Optional

from modules.announcement.priority import PRIORITY_ORDER


@dataclass(order=True)
class QueueItem:
    sort_key: tuple
    queue_entry_id: int = field(compare=False)
    announcement_id: int = field(compare=False)


class AnnouncementQueueManager:
    def __init__(self) -> None:
        self._heap: list[QueueItem] = []
        self._counter = itertools.count()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def push(
        self,
        queue_entry_id: int,
        announcement_id: int,
        priority: str,
        created_at_ordinal: float,
    ) -> None:
        sort_key = (PRIORITY_ORDER.get(priority, 99), created_at_ordinal, next(self._counter))
        with self._not_empty:
            heapq.heappush(self._heap, QueueItem(sort_key, queue_entry_id, announcement_id))
            self._not_empty.notify()

    def pop(self, timeout: Optional[float] = None) -> Optional[QueueItem]:
        with self._not_empty:
            if not self._heap:
                self._not_empty.wait(timeout=timeout)
            if not self._heap:
                return None
            return heapq.heappop(self._heap)

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)
