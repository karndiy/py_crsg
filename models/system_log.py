from datetime import datetime, timezone

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SystemLog(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(16), nullable=False, default="INFO", index=True)
    module = db.Column(db.String(64), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    def __repr__(self) -> str:
        return f"<SystemLog {self.level} {self.module}>"
