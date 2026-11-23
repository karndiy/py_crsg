from datetime import datetime, timezone

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SmsMessage(db.Model):
    __tablename__ = "sms_messages"

    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(32), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    encoding = db.Column(db.String(16), nullable=False, default="GSM7")
    received_at = db.Column(db.DateTime, default=_utcnow, index=True)
    modem_index = db.Column(db.Integer, nullable=True)
    processing_status = db.Column(db.String(32), nullable=False, default="received", index=True)
    raw_pdu = db.Column(db.Text, nullable=True)
    duplicate_key = db.Column(db.String(64), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<SmsMessage {self.id} from {self.sender}>"
