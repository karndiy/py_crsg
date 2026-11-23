import uuid
from datetime import datetime, timezone

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_public_id() -> str:
    return uuid.uuid4().hex


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=_new_public_id, index=True)
    source_type = db.Column(db.String(16), nullable=False)  # sms | call | manual
    source_id = db.Column(db.Integer, nullable=True)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(16), nullable=False, default="NORMAL", index=True)
    status = db.Column(db.String(16), nullable=False, default="received", index=True)
    audio_path = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)
    played_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    stop_requested_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Announcement {self.public_id} status={self.status}>"


class AnnouncementQueueEntry(db.Model):
    __tablename__ = "announcement_queue"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False, index=True)
    priority = db.Column(db.String(16), nullable=False, default="NORMAL")
    queue_status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    announcement = db.relationship("Announcement", backref="queue_entries")

    def __repr__(self) -> str:
        return f"<AnnouncementQueueEntry {self.id} status={self.queue_status}>"
