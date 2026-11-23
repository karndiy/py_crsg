from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthorizedSender(db.Model):
    __tablename__ = "authorized_senders"

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(128), nullable=True)
    pin_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    can_sms = db.Column(db.Boolean, nullable=False, default=True)
    can_call = db.Column(db.Boolean, nullable=False, default=False)
    default_call_command_id = db.Column(
        db.Integer, db.ForeignKey("call_commands.id"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    default_call_command = db.relationship("CallCommand")

    def set_pin(self, raw_pin: str) -> None:
        self.pin_hash = generate_password_hash(raw_pin)

    def verify_pin(self, raw_pin: str) -> bool:
        return check_password_hash(self.pin_hash, raw_pin)

    def __repr__(self) -> str:
        return f"<AuthorizedSender {self.phone_number}>"
