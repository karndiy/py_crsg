"""Background worker process entrypoint.

Runs the SMS reader, call monitor, announcement processor, and audio
playback worker (CLAUDE.md §17, systemd unit
`community-radio-worker.service`). Never serves HTTP — that is app.py's
job, running as a separate OS process (`community-radio.service`).
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import runtime
from app import create_app
from extensions import db
from models import Announcement
from modules.announcement.processor import AnnouncementProcessor
from modules.announcement.queue import AnnouncementQueueManager
from modules.announcement.scheduler import (
    MultipartSweeper,
    PendingAnnouncementPoller,
    recover_pending_queue,
)
from modules.audio.audio_player import AudioPlayer
from modules.audio.playback_queue import PlaybackQueue
from modules.call_gateway.call_monitor import CallMonitor
from modules.sms_gateway.modem import AtCommandManager, SerialModemTransport
from modules.sms_gateway.multipart import MultipartReassembler
from modules.sms_gateway.sms_reader import SmsReaderWorker
from modules.tts.piper_engine import PiperEngine
from services import call_service, sms_service

logger = logging.getLogger(__name__)

STOP_WATCH_INTERVAL = 1.0


def _build_playback_callbacks(app):
    def on_start(announcement_id: int) -> None:
        with app.app_context():
            announcement = db.session.get(Announcement, announcement_id)
            if announcement is None:
                return
            announcement.status = "playing"
            db.session.commit()

    def on_finish(announcement_id: int, success: bool, error: Optional[str]) -> None:
        with app.app_context():
            announcement = db.session.get(Announcement, announcement_id)
            if announcement is None:
                return
            announcement.stop_requested_at = None
            if error == "cancelled":
                announcement.status = "cancelled"
            elif success:
                announcement.status = "played"
                announcement.played_at = datetime.now(timezone.utc)
            else:
                announcement.status = "failed"
                announcement.error_message = error
            db.session.commit()

    return on_start, on_finish


class StopSignalWatcher:
    """Bridges the dashboard's "Stop" button (a DB flag — the dashboard
    runs in a different OS process, see runtime.py) to the worker's
    in-process PlaybackQueue, which is the only thing that can actually
    terminate the running `aplay` subprocess.
    """

    def __init__(self, app, playback_queue: PlaybackQueue, interval: float = STOP_WATCH_INTERVAL) -> None:
        self._app = app
        self._playback_queue = playback_queue
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, name="stop-signal-watcher", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_loop(self) -> None:
        with self._app.app_context():
            while not self._stop_event.wait(self._interval):
                playing = Announcement.query.filter(
                    Announcement.status == "playing",
                    Announcement.stop_requested_at.isnot(None),
                ).all()
                for announcement in playing:
                    logger.info("Stop requested for announcement %s", announcement.public_id)
                    self._playback_queue.stop_current()


def main() -> None:
    app = create_app()

    queue_manager = AnnouncementQueueManager()
    reassembler = MultipartReassembler(timeout_seconds=app.config["MULTIPART_TIMEOUT_SECONDS"])
    player = AudioPlayer(
        player_executable=app.config["AUDIO_PLAYER"], device=app.config["AUDIO_DEVICE"]
    )
    on_start, on_finish = _build_playback_callbacks(app)
    playback_queue = PlaybackQueue(player, on_start, on_finish)

    runtime.configure_worker_runtime(
        queue_manager=queue_manager, reassembler=reassembler, playback=playback_queue
    )

    recover_pending_queue(app, queue_manager)

    tts_engine = PiperEngine(
        executable=app.config["PIPER_EXECUTABLE"], model_path=app.config["PIPER_MODEL"]
    )
    processor = AnnouncementProcessor(
        app, queue_manager, tts_engine, playback_queue, app.config["AUDIO_OUTPUT_DIR"]
    )

    components = [
        playback_queue,
        processor,
        PendingAnnouncementPoller(app, queue_manager),
        MultipartSweeper(reassembler),
        StopSignalWatcher(app, playback_queue),
    ]

    at_manager = None

    if app.config["SMS_ENABLED"] or app.config["CALL_ENABLED"]:
        transport = SerialModemTransport(port=app.config["SMS_PORT"], baudrate=app.config["SMS_BAUD"])
        at_manager = AtCommandManager(transport)
        at_manager.connect()

        if app.config["SMS_ENABLED"]:
            def handle_incoming_sms(sms, index):
                with app.app_context():
                    sms_service.process_incoming_sms(sms, index)

            sms_worker = SmsReaderWorker(
                at_manager, handle_incoming_sms, auto_delete=app.config["SMS_AUTO_DELETE"]
            )
            sms_worker.initialize()
            components.append(sms_worker)

        if app.config["CALL_ENABLED"]:
            def handle_incoming_call(caller_number):
                with app.app_context():
                    call_service.process_incoming_call(caller_number)

            call_monitor = CallMonitor(
                at_manager, handle_incoming_call, auto_reject=app.config["CALL_AUTO_REJECT"]
            )
            call_monitor.initialize()
            components.append(call_monitor)
    else:
        logger.warning("SMS and Call gateways are both disabled (SMS_ENABLED=false, CALL_ENABLED=false)")

    for component in components:
        component.start()

    logger.info("Community Radio worker started")

    stop_event = threading.Event()

    def _handle_signal(signum, _frame):
        logger.info("Received signal %s, shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        for component in components:
            component.stop()
        if at_manager is not None:
            at_manager.disconnect()
        logger.info("Community Radio worker stopped")


if __name__ == "__main__":
    main()
