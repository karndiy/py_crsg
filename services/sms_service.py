"""Business logic for incoming SMS.

Runs the exact validation order from CLAUDE.md §8: sender number →
active status → command format → PIN → message length → duplicate →
rate limit → priority → save → queue. Always persists an SmsMessage row
(even a rejected one) so the inbox is a complete audit trail.

Called from the worker process by modules/sms_gateway/sms_reader.py's
`on_message` callback — never from a Flask request handler.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app

import runtime
from extensions import db
from models import Announcement, AnnouncementQueueEntry, AuthorizedSender, SmsMessage
from modules.security.command_validator import compute_duplicate_key, validate_message_length
from modules.security.rate_limiter import check_rate_limit
from modules.sms_gateway.pdu_decoder import DecodedSms
from modules.sms_gateway.sender_validator import normalize_phone_number, parse_command

logger = logging.getLogger(__name__)

DUPLICATE_WINDOW = timedelta(hours=24)
RATE_LIMIT_WINDOW = timedelta(hours=1)


class SmsRejected(Exception):
    """Any reason an SMS did not pass validation; carries the reason so
    it can be logged against the persisted SmsMessage row."""


def process_incoming_sms(sms: DecodedSms, modem_index: int) -> Optional[SmsMessage]:
    reassembler = runtime.multipart_reassembler
    complete_sms = reassembler.add_part(sms) if reassembler is not None else sms
    if complete_sms is None:
        logger.info("Buffered multipart segment from %s (awaiting remaining parts)", sms.sender)
        return None

    normalized_sender = normalize_phone_number(complete_sms.sender)
    duplicate_key = compute_duplicate_key(normalized_sender, complete_sms.text)

    record = SmsMessage(
        sender=normalized_sender,
        message=complete_sms.text,
        encoding=complete_sms.encoding,
        modem_index=modem_index,
        raw_pdu=complete_sms.raw_pdu,
        duplicate_key=duplicate_key,
        received_at=complete_sms.timestamp,
        processing_status="received",
    )

    try:
        sender = _require_whitelisted_sender(normalized_sender)
        parsed = parse_command(complete_sms.text)
        if not sender.verify_pin(parsed.pin):
            raise SmsRejected(f"Invalid PIN from {normalized_sender}")
        validate_message_length(parsed.message, current_app.config["MAX_MESSAGE_LENGTH"])
        _reject_if_duplicate(duplicate_key)
        recent_count = _count_recent_messages(normalized_sender)
        check_rate_limit(recent_count, current_app.config["RATE_LIMIT_PER_HOUR"])
    except Exception as exc:
        record.processing_status = "rejected"
        db.session.add(record)
        db.session.commit()
        logger.info("Rejected SMS from %s: %s", normalized_sender, exc)
        return record

    record.processing_status = "validated"
    db.session.add(record)
    db.session.flush()

    announcement = Announcement(
        source_type="sms",
        source_id=record.id,
        message=parsed.message,
        priority=parsed.priority,
        status="queued",
    )
    db.session.add(announcement)
    db.session.flush()

    queue_entry = AnnouncementQueueEntry(
        announcement_id=announcement.id,
        priority=parsed.priority,
        queue_status="pending",
    )
    db.session.add(queue_entry)
    db.session.commit()

    if runtime.announcement_queue_manager is not None:
        runtime.announcement_queue_manager.push(
            queue_entry.id,
            announcement.id,
            parsed.priority,
            queue_entry.created_at.timestamp(),
        )

    logger.info(
        "Queued announcement %s from %s (priority=%s)",
        announcement.public_id,
        normalized_sender,
        parsed.priority,
    )
    return record


def _require_whitelisted_sender(normalized_sender: str) -> AuthorizedSender:
    sender = AuthorizedSender.query.filter_by(phone_number=normalized_sender).first()
    if sender is None:
        raise SmsRejected(f"{normalized_sender} is not in the sender whitelist")
    if not sender.is_active:
        raise SmsRejected(f"{normalized_sender} is disabled")
    if not sender.can_sms:
        raise SmsRejected(f"{normalized_sender} is not authorized to send SMS commands")
    return sender


def _reject_if_duplicate(duplicate_key: str) -> None:
    cutoff = datetime.now(timezone.utc) - DUPLICATE_WINDOW
    existing = SmsMessage.query.filter(
        SmsMessage.duplicate_key == duplicate_key,
        SmsMessage.received_at >= cutoff,
        SmsMessage.processing_status != "rejected",
    ).first()
    if existing is not None:
        raise SmsRejected("Duplicate message within the last 24 hours")


def _count_recent_messages(normalized_sender: str) -> int:
    cutoff = datetime.now(timezone.utc) - RATE_LIMIT_WINDOW
    return SmsMessage.query.filter(
        SmsMessage.sender == normalized_sender,
        SmsMessage.received_at >= cutoff,
        SmsMessage.processing_status != "rejected",
    ).count()
