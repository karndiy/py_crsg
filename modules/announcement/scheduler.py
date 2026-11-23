"""Periodic housekeeping for the announcement pipeline.

- `recover_pending_queue` runs once at worker startup: any
  `announcement_queue` row still marked `processing` means the previous
  process died mid-synthesis/playback, so it is reset to `pending` and
  re-added to the in-memory queue instead of being assumed complete.
  This is what lets the system come back after a Raspberry Pi restart
  without announcing anything twice or losing anything (CLAUDE.md §18).
- `MultipartSweeper` periodically drops multipart SMS groups that never
  arrived in full within the configured timeout.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional, Set

from extensions import db
from models import AnnouncementQueueEntry
from modules.announcement.queue import AnnouncementQueueManager
from modules.sms_gateway.multipart import MultipartReassembler

logger = logging.getLogger(__name__)


def recover_pending_queue(app, queue_manager: AnnouncementQueueManager) -> int:
    with app.app_context():
        stuck_entries = AnnouncementQueueEntry.query.filter(
            AnnouncementQueueEntry.queue_status.in_(("processing", "pending"))
        ).all()
        for entry in stuck_entries:
            entry.queue_status = "pending"
            queue_manager.push(
                entry.id,
                entry.announcement_id,
                entry.priority,
                entry.created_at.timestamp(),
            )
        db.session.commit()
        if stuck_entries:
            logger.info("Recovered %d pending announcement(s) after restart", len(stuck_entries))
        return len(stuck_entries)


class PendingAnnouncementPoller:
    """Picks up announcements created directly by the dashboard/API
    process (e.g. a manually-typed announcement). The web process and
    the worker process are separate OS processes with separate memory
    (CLAUDE.md §17), so a row the dashboard inserts into
    `announcement_queue` is invisible to the worker's in-memory
    AnnouncementQueueManager until something in the worker process
    notices it — this polls the database to do that, instead of
    requiring the dashboard to talk to the worker directly.
    """

    def __init__(
        self,
        app,
        queue_manager: AnnouncementQueueManager,
        interval_seconds: float = 3.0,
    ) -> None:
        self._app = app
        self._queue_manager = queue_manager
        self._interval_seconds = interval_seconds
        self._seen_ids: Set[int] = set()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, name="pending-announcement-poller", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_loop(self) -> None:
        with self._app.app_context():
            while not self._stop_event.wait(self._interval_seconds):
                self._poll_once()

    def _poll_once(self) -> None:
        pending = AnnouncementQueueEntry.query.filter_by(queue_status="pending").all()
        for entry in pending:
            if entry.id in self._seen_ids:
                continue
            self._seen_ids.add(entry.id)
            self._queue_manager.push(
                entry.id, entry.announcement_id, entry.priority, entry.created_at.timestamp()
            )


class MultipartSweeper:
    def __init__(self, reassembler: MultipartReassembler, interval_seconds: float = 60.0) -> None:
        self._reassembler = reassembler
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, name="multipart-sweeper", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            expired = self._reassembler.sweep_expired()
            if expired:
                logger.warning(
                    "Dropped %d incomplete multipart SMS group(s): %s", len(expired), expired
                )
