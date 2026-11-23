from datetime import datetime, timezone

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CallCommand(db.Model):
    __tablename__ = "call_commands"

    id = db.Column(db.Integer, primary_key=True)
    command_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    announcement_text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<CallCommand {self.command_code}>"


class CallLog(db.Model):
    __tablename__ = "call_logs"

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(32), nullable=False, index=True)
    call_status = db.Column(db.String(32), nullable=False)  # authorized | rejected | error
    command_id = db.Column(db.Integer, db.ForeignKey("call_commands.id"), nullable=True)
    received_at = db.Column(db.DateTime, default=_utcnow, index=True)
    processed_at = db.Column(db.DateTime, nullable=True)

    command = db.relationship("CallCommand")

    def __repr__(self) -> str:
        return f"<CallLog {self.phone_number} status={self.call_status}>"
