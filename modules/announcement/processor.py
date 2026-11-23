"""Pulls queued announcements, synthesizes audio via Piper, and hands
the result to the playback queue.

Runs its own background thread wrapped in a Flask app context (passed
in as `app`) so it can use the same SQLAlchemy models as the web app —
this is the "TTS Worker must be separate from the web request" piece of
the architecture (CLAUDE.md §4).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from extensions import db
from models import Announcement, AnnouncementQueueEntry, AudioFile
from modules.announcement.queue import AnnouncementQueueManager
from modules.audio.playback_queue import PlaybackQueue
from modules.tts.piper_engine import PiperEngine

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnnouncementProcessor:
    def __init__(
        self,
        app,
        queue_manager: AnnouncementQueueManager,
        tts_engine: PiperEngine,
        playback_queue: PlaybackQueue,
        audio_output_dir: str,
    ) -> None:
        self._app = app
        self._queue_manager = queue_manager
        self._tts = tts_engine
        self._playback_queue = playback_queue
        self._audio_output_dir = audio_output_dir
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, name="announcement-processor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_loop(self) -> None:
        with self._app.app_context():
            while not self._stop_event.is_set():
                item = self._queue_manager.pop(timeout=1.0)
                if item is None:
                    continue
                try:
                    self._process_item(item.queue_entry_id, item.announcement_id)
                except Exception:
                    logger.exception(
                        "Unhandled error processing queue entry %s", item.queue_entry_id
                    )
                    db.session.rollback()

    def _process_item(self, queue_entry_id: int, announcement_id: int) -> None:
        entry = db.session.get(AnnouncementQueueEntry, queue_entry_id)
        announcement = db.session.get(Announcement, announcement_id)
        if entry is None or announcement is None:
            logger.error(
                "Queue entry %s / announcement %s missing from database",
                queue_entry_id,
                announcement_id,
            )
            return

        entry.queue_status = "processing"
        entry.started_at = _utcnow()
        announcement.status = "generating"
        db.session.commit()

        output_path = f"{self._audio_output_dir}/announcement_{announcement.public_id}.wav"
        result = self._tts.synthesize(announcement.message, output_path)

        if not result.success:
            self._handle_synthesis_failure(entry, announcement, result.error or "unknown TTS error")
            return

        audio_file = AudioFile(
            announcement_id=announcement.id,
            file_path=result.output_path,
            voice_model=result.voice_model,
        )
        db.session.add(audio_file)
        announcement.audio_path = result.output_path
        announcement.status = "ready"
        entry.queue_status = "ready"
        entry.completed_at = _utcnow()
        db.session.commit()

        self._playback_queue.enqueue(announcement.id, announcement.priority, result.output_path)

    def _handle_synthesis_failure(
        self, entry: AnnouncementQueueEntry, announcement: Announcement, error: str
    ) -> None:
        entry.retry_count += 1
        announcement.error_message = error
        logger.error("TTS synthesis failed for announcement %s: %s", announcement.public_id, error)

        if entry.retry_count >= MAX_RETRIES:
            entry.queue_status = "failed"
            announcement.status = "failed"
            db.session.commit()
            return

        entry.queue_status = "pending"
        announcement.status = "queued"
        db.session.commit()
        self._queue_manager.push(
            entry.id, announcement.id, announcement.priority, entry.created_at.timestamp()
        )
