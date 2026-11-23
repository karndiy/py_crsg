from flask import Blueprint, jsonify, request

from extensions import db
from models import AuthorizedSender
from modules.security.api_key import api_key_required
from modules.sms_gateway.sender_validator import normalize_phone_number

sender_bp = Blueprint("senders", __name__, url_prefix="/api/v1/senders")


@sender_bp.get("")
@api_key_required
def list_senders():
    senders = AuthorizedSender.query.order_by(AuthorizedSender.phone_number).all()
    return jsonify([_serialize(s) for s in senders])


@sender_bp.post("")
@api_key_required
def create_sender():
    data = request.get_json(silent=True) or {}
    phone_number = normalize_phone_number((data.get("phone_number") or "").strip())
    pin = (data.get("pin") or "").strip()
    if not phone_number or not pin:
        return jsonify({"error": "phone_number and pin are required"}), 400
    if AuthorizedSender.query.filter_by(phone_number=phone_number).first() is not None:
        return jsonify({"error": "phone_number already registered"}), 409

    sender = AuthorizedSender(
        phone_number=phone_number,
        display_name=data.get("display_name"),
        can_sms=bool(data.get("can_sms", True)),
        can_call=bool(data.get("can_call", False)),
        default_call_command_id=data.get("default_call_command_id"),
    )
    sender.set_pin(pin)
    db.session.add(sender)
    db.session.commit()
    return jsonify(_serialize(sender)), 201


@sender_bp.put("/<int:sender_id>")
@api_key_required
def update_sender(sender_id):
    sender = AuthorizedSender.query.get_or_404(sender_id)
    data = request.get_json(silent=True) or {}

    if "display_name" in data:
        sender.display_name = data["display_name"]
    if "is_active" in data:
        sender.is_active = bool(data["is_active"])
    if "can_sms" in data:
        sender.can_sms = bool(data["can_sms"])
    if "can_call" in data:
        sender.can_call = bool(data["can_call"])
    if "default_call_command_id" in data:
        sender.default_call_command_id = data["default_call_command_id"]
    if data.get("pin"):
        sender.set_pin(str(data["pin"]))

    db.session.commit()
    return jsonify(_serialize(sender))


@sender_bp.delete("/<int:sender_id>")
@api_key_required
def delete_sender(sender_id):
    sender = AuthorizedSender.query.get_or_404(sender_id)
    db.session.delete(sender)
    db.session.commit()
    return "", 204


def _serialize(s: AuthorizedSender) -> dict:
    return {
        "id": s.id,
        "phone_number": s.phone_number,
        "display_name": s.display_name,
        "is_active": s.is_active,
        "can_sms": s.can_sms,
        "can_call": s.can_call,
        "default_call_command_id": s.default_call_command_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
