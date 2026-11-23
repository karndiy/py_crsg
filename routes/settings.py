from flask import Blueprint, current_app, jsonify, request

from extensions import db
from models import CallCommand, CallLog
from modules.security.api_key import api_key_required
from services import audio_service

settings_bp = Blueprint("settings", __name__, url_prefix="/api/v1")


@settings_bp.get("/calls")
@api_key_required
def list_calls():
    calls = CallLog.query.order_by(CallLog.received_at.desc()).limit(200).all()
    return jsonify([_serialize_call(c) for c in calls])


@settings_bp.get("/call-commands")
@api_key_required
def list_call_commands():
    commands = CallCommand.query.order_by(CallCommand.command_code).all()
    return jsonify([_serialize_command(c) for c in commands])


@settings_bp.post("/call-commands")
@api_key_required
def create_call_command():
    data = request.get_json(silent=True) or {}
    command_code = (data.get("command_code") or "").strip()
    title = (data.get("title") or "").strip()
    announcement_text = (data.get("announcement_text") or "").strip()
    if not command_code or not title or not announcement_text:
        return jsonify({"error": "command_code, title and announcement_text are required"}), 400
    if CallCommand.query.filter_by(command_code=command_code).first() is not None:
        return jsonify({"error": "command_code already exists"}), 409

    command = CallCommand(
        command_code=command_code, title=title, announcement_text=announcement_text
    )
    db.session.add(command)
    db.session.commit()
    return jsonify(_serialize_command(command)), 201


@settings_bp.get("/audio/devices")
@api_key_required
def audio_devices():
    devices = audio_service.get_devices()
    return jsonify(
        [
            {"card": d.card, "device": d.device, "name": d.name, "description": d.description}
            for d in devices
        ]
    )


@settings_bp.get("/audio/status")
@api_key_required
def audio_status():
    return jsonify(audio_service.get_status())


@settings_bp.post("/audio/test")
@api_key_required
def audio_test():
    data = request.get_json(silent=True) or {}
    wav_path = data.get("wav_path") or "static/audio/test_tone.wav"
    result = audio_service.test_playback(wav_path)
    status_code = 200 if result.success else 500
    return jsonify({"success": result.success, "error": result.error}), status_code


@settings_bp.get("/settings")
@api_key_required
def get_settings():
    return jsonify(
        {
            "sms_port": current_app.config["SMS_PORT"],
            "sms_baud": current_app.config["SMS_BAUD"],
            "piper_model": current_app.config["PIPER_MODEL"],
            "audio_device": current_app.config["AUDIO_DEVICE"],
            "max_message_length": current_app.config["MAX_MESSAGE_LENGTH"],
            "rate_limit_per_hour": current_app.config["RATE_LIMIT_PER_HOUR"],
            "auto_announce": current_app.config["AUTO_ANNOUNCE"],
            "sms_enabled": current_app.config["SMS_ENABLED"],
            "call_enabled": current_app.config["CALL_ENABLED"],
        }
    )


def _serialize_call(c: CallLog) -> dict:
    return {
        "id": c.id,
        "phone_number": c.phone_number,
        "call_status": c.call_status,
        "command_id": c.command_id,
        "received_at": c.received_at.isoformat() if c.received_at else None,
        "processed_at": c.processed_at.isoformat() if c.processed_at else None,
    }


def _serialize_command(c: CallCommand) -> dict:
    return {
        "id": c.id,
        "command_code": c.command_code,
        "title": c.title,
        "announcement_text": c.announcement_text,
        "is_active": c.is_active,
    }
