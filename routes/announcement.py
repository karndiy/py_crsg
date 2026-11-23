from flask import Blueprint, jsonify, request

from models import Announcement
from modules.security.api_key import api_key_required
from services import announcement_service

announcement_bp = Blueprint("announcements", __name__, url_prefix="/api/v1/announcements")


@announcement_bp.get("")
@api_key_required
def list_announcements():
    items = announcement_service.list_announcements()
    return jsonify([_serialize(a) for a in items])


@announcement_bp.get("/<public_id>")
@api_key_required
def get_announcement(public_id):
    announcement = announcement_service.get_announcement(public_id)
    if announcement is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(_serialize(announcement))


@announcement_bp.post("")
@api_key_required
def create_announcement():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    priority = (data.get("priority") or "NORMAL").upper()
    if not message:
        return jsonify({"error": "message is required"}), 400
    if priority not in ("NORMAL", "HIGH", "EMERGENCY"):
        return jsonify({"error": "invalid priority"}), 400
    announcement = announcement_service.create_manual_announcement(message, priority)
    return jsonify(_serialize(announcement)), 201


@announcement_bp.post("/<public_id>/play")
@api_key_required
def play_announcement(public_id):
    return _run_action(announcement_service.request_play, public_id)


@announcement_bp.post("/<public_id>/stop")
@api_key_required
def stop_announcement(public_id):
    return _run_action(announcement_service.request_stop, public_id)


@announcement_bp.post("/<public_id>/cancel")
@api_key_required
def cancel_announcement(public_id):
    return _run_action(announcement_service.request_cancel, public_id)


def _run_action(action, public_id):
    try:
        announcement = action(public_id)
    except announcement_service.AnnouncementActionError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize(announcement))


def _serialize(a: Announcement) -> dict:
    return {
        "id": a.public_id,
        "source_type": a.source_type,
        "message": a.message,
        "priority": a.priority,
        "status": a.status,
        "audio_path": a.audio_path,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "played_at": a.played_at.isoformat() if a.played_at else None,
        "error_message": a.error_message,
    }
