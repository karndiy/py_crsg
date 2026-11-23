from datetime import datetime, timezone

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AudioFile(db.Model):
    __tablename__ = "audio_files"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=True, index=True)
    file_path = db.Column(db.String(256), nullable=False)
    duration_seconds = db.Column(db.Float, nullable=True)
    voice_model = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    announcement = db.relationship("Announcement", backref="audio_files")

    def __repr__(self) -> str:
        return f"<AudioFile {self.file_path}>"
