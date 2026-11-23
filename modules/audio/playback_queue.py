"""Priority-ordered playback queue, fed by the announcement processor.

Only one announcement plays at a time; whatever is currently playing is
never interrupted by a later arrival regardless of its priority
(CLAUDE.md §10). New items are simply ordered by priority
(EMERGENCY > HIGH > NORMAL, then arrival order) for whichever plays
*next*.

This class knows nothing about Flask or the database — `on_start` /
`on_finish` are plain callbacks the caller (worker.py) wires up to
update announcement status, so this stays unit-testable with a fake
player.
"""

from __future__ import annotations

import heapq
import itertools
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional, Set

from modules.announcement.priority import PRIORITY_ORDER

OnPlaybackStart = Callable[[int], None]
OnPlaybackFinish = Callable[[int, bool, Optional[str]], None]


@dataclass(order=True)
class _PlaybackItem:
    sort_key: tuple
    announcement_id: int = field(compare=False)
    wav_path: str = field(compare=False)


class PlaybackQueue:
    def __init__(self, player, on_start: OnPlaybackStart, on_finish: OnPlaybackFinish) -> None:
        self._player = player
        self._on_start = on_start
        self._on_finish = on_finish
        self._heap: list[_PlaybackItem] = []
        self._counter = itertools.count()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cancelled_ids: Set[int] = set()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, name="playback-queue", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._not_empty:
            self._not_empty.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def enqueue(self, announcement_id: int, priority: str, wav_path: str) -> None:
        sort_key = (PRIORITY_ORDER.get(priority, 99), next(self._counter))
        with self._not_empty:
            heapq.heappush(self._heap, _PlaybackItem(sort_key, announcement_id, wav_path))
            self._not_empty.notify()

    def cancel(self, announcement_id: int) -> None:
        with self._lock:
            self._cancelled_ids.add(announcement_id)

    def stop_current(self) -> bool:
        return self._player.stop()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            item = self._wait_for_next()
            if item is None:
                continue
            if self._consume_cancelled(item.announcement_id):
                self._on_finish(item.announcement_id, False, "cancelled")
                continue
            self._on_start(item.announcement_id)
            result = self._player.play(item.wav_path)
            self._on_finish(item.announcement_id, result.success, result.error)

    def _wait_for_next(self) -> Optional[_PlaybackItem]:
        with self._not_empty:
            if not self._heap:
                self._not_empty.wait(timeout=1.0)
            if not self._heap:
                return None
            return heapq.heappop(self._heap)

    def _consume_cancelled(self, announcement_id: int) -> bool:
        with self._lock:
            if announcement_id in self._cancelled_ids:
                self._cancelled_ids.discard(announcement_id)
                return True
            return False
