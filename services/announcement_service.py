"""Business logic behind the announcement REST endpoints and dashboard.

Runs in the web process. It never touches the worker process's
in-memory queue managers (see runtime.py) — play/stop/cancel only set
flags on the Announcement/AnnouncementQueueEntry rows, and the worker
process notices them via modules/announcement/scheduler.py's pollers
and worker.py's stop-signal watcher.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from extensions import db
from models import Announcement, AnnouncementQueueEntry

_CANCELLABLE_STATUSES = ("received", "validated", "queued", "generating", "ready")


class AnnouncementActionError(ValueError):
    pass


def list_announcements(limit: int = 100) -> List[Announcement]:
    return Announcement.query.order_by(Announcement.created_at.desc()).limit(limit).all()


def get_announcement(public_id: str) -> Optional[Announcement]:
    return Announcement.query.filter_by(public_id=public_id).first()


def create_manual_announcement(message: str, priority: str = "NORMAL") -> Announcement:
    announcement = Announcement(
        source_type="manual",
        message=message,
        priority=priority,
        status="queued",
    )
    db.session.add(announcement)
    db.session.flush()

    db.session.add(
        AnnouncementQueueEntry(
            announcement_id=announcement.id,
            priority=priority,
            queue_status="pending",
        )
    )
    db.session.commit()
    return announcement


def request_play(public_id: str) -> Announcement:
    announcement = _require_announcement(public_id)
    if announcement.status == "playing":
        raise AnnouncementActionError("Announcement is already playing")

    announcement.status = "queued"
    announcement.error_message = None
    db.session.add(
        AnnouncementQueueEntry(
            announcement_id=announcement.id,
            priority=announcement.priority,
            queue_status="pending",
        )
    )
    db.session.commit()
    return announcement


def request_stop(public_id: str) -> Announcement:
    announcement = _require_announcement(public_id)
    if announcement.status != "playing":
        raise AnnouncementActionError(f"Cannot stop an announcement in status {announcement.status!r}")

    announcement.stop_requested_at = datetime.now(timezone.utc)
    db.session.commit()
    return announcement


def request_cancel(public_id: str) -> Announcement:
    announcement = _require_announcement(public_id)
    if announcement.status not in _CANCELLABLE_STATUSES:
        raise AnnouncementActionError(f"Cannot cancel an announcement in status {announcement.status!r}")

    announcement.status = "cancelled"
    queue_entry = (
        AnnouncementQueueEntry.query.filter_by(announcement_id=announcement.id)
        .order_by(AnnouncementQueueEntry.id.desc())
        .first()
    )
    if queue_entry is not None and queue_entry.queue_status in ("pending", "processing"):
        queue_entry.queue_status = "cancelled"
    db.session.commit()
    return announcement


def _require_announcement(public_id: str) -> Announcement:
    announcement = get_announcement(public_id)
    if announcement is None:
        raise AnnouncementActionError("Announcement not found")
    return announcement
