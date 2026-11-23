"""Business logic for incoming phone calls.

Validates the caller against the whitelist, resolves the canned call
command, logs the call, and queues an announcement. Called from the
worker process by modules/call_gateway/call_monitor.py's
`on_incoming_call` callback.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import runtime
from extensions import db
from models import Announcement, AnnouncementQueueEntry, AuthorizedSender, CallCommand, CallLog
from modules.call_gateway.call_command import CallCommandError, resolve_call_command
from modules.call_gateway.caller_validator import normalize_phone_number

logger = logging.getLogger(__name__)


def process_incoming_call(caller_number: str) -> CallLog:
    normalized = normalize_phone_number(caller_number)
    log = CallLog(phone_number=normalized, call_status="rejected")

    sender = AuthorizedSender.query.filter_by(phone_number=normalized).first()
    if sender is None:
        db.session.add(log)
        db.session.commit()
        logger.info("Rejected call from unknown number %s", normalized)
        return log

    try:
        result = resolve_call_command(
            sender, lambda command_id: db.session.get(CallCommand, command_id)
        )
    except CallCommandError as exc:
        db.session.add(log)
        db.session.commit()
        logger.info("Rejected call from %s: %s", normalized, exc)
        return log

    log.call_status = "authorized"
    log.command_id = sender.default_call_command_id
    log.processed_at = datetime.now(timezone.utc)
    db.session.add(log)
    db.session.flush()

    announcement = Announcement(
        source_type="call",
        source_id=log.id,
        message=result.announcement_text,
        priority="NORMAL",
        status="queued",
    )
    db.session.add(announcement)
    db.session.flush()

    queue_entry = AnnouncementQueueEntry(
        announcement_id=announcement.id,
        priority=announcement.priority,
        queue_status="pending",
    )
    db.session.add(queue_entry)
    db.session.commit()

    if runtime.announcement_queue_manager is not None:
        runtime.announcement_queue_manager.push(
            queue_entry.id,
            announcement.id,
            announcement.priority,
            queue_entry.created_at.timestamp(),
        )

    logger.info("Call from %s triggered command %s", normalized, result.command_code)
    return log
