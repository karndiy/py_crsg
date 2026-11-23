from flask import Blueprint, jsonify

from models import SmsMessage
from modules.security.api_key import api_key_required

sms_bp = Blueprint("sms", __name__, url_prefix="/api/v1/sms")


@sms_bp.get("")
@api_key_required
def list_sms():
    messages = SmsMessage.query.order_by(SmsMessage.received_at.desc()).limit(200).all()
    return jsonify([_serialize(m) for m in messages])


@sms_bp.get("/<int:sms_id>")
@api_key_required
def get_sms(sms_id):
    message = SmsMessage.query.get_or_404(sms_id)
    return jsonify(_serialize(message))


def _serialize(message: SmsMessage) -> dict:
    return {
        "id": message.id,
        "sender": message.sender,
        "message": message.message,
        "encoding": message.encoding,
        "received_at": message.received_at.isoformat() if message.received_at else None,
        "processing_status": message.processing_status,
    }
