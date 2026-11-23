"""Process-wide handles to background components.

The Flask web process (app.py, serving the dashboard + API under
systemd unit `community-radio.service`) and the background worker
process (worker.py, under `community-radio-worker.service`) are
separate OS processes — see CLAUDE.md §17. They never share Python
memory, only the SQLite database. The *only* in-process state kept
here (`announcement_queue_manager`, `playback_queue`) is private to
whichever process set it up; the dashboard/API talks to the worker
exclusively through DB rows (status flags, `stop_requested_at`), never
by reaching into this module from a different process.
"""

from __future__ import annotations

from typing import Optional

from modules.announcement.queue import AnnouncementQueueManager
from modules.audio.playback_queue import PlaybackQueue
from modules.sms_gateway.multipart import MultipartReassembler

announcement_queue_manager: Optional[AnnouncementQueueManager] = None
multipart_reassembler: Optional[MultipartReassembler] = None
playback_queue: Optional[PlaybackQueue] = None


def configure_worker_runtime(
    *,
    queue_manager: AnnouncementQueueManager,
    reassembler: MultipartReassembler,
    playback: PlaybackQueue,
) -> None:
    global announcement_queue_manager, multipart_reassembler, playback_queue
    announcement_queue_manager = queue_manager
    multipart_reassembler = reassembler
    playback_queue = playback
