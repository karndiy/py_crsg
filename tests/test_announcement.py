import time

from modules.announcement.queue import AnnouncementQueueManager
from modules.audio.audio_player import PlaybackResult
from modules.audio.playback_queue import PlaybackQueue


class FakePlayer:
    def __init__(self):
        self.played = []

    def play(self, wav_path):
        self.played.append(wav_path)
        return PlaybackResult(success=True)

    def stop(self):
        return True


def test_announcement_queue_orders_by_priority_then_fifo():
    manager = AnnouncementQueueManager()
    manager.push(queue_entry_id=1, announcement_id=1, priority="NORMAL", created_at_ordinal=1.0)
    manager.push(queue_entry_id=2, announcement_id=2, priority="EMERGENCY", created_at_ordinal=2.0)
    manager.push(queue_entry_id=3, announcement_id=3, priority="HIGH", created_at_ordinal=3.0)

    first = manager.pop()
    second = manager.pop()
    third = manager.pop()

    assert [first.announcement_id, second.announcement_id, third.announcement_id] == [2, 3, 1]


def test_announcement_queue_pop_returns_none_when_empty_after_timeout():
    manager = AnnouncementQueueManager()
    assert manager.pop(timeout=0.05) is None


def test_playback_queue_plays_items_in_priority_order():
    player = FakePlayer()
    started = []
    finished = []

    queue = PlaybackQueue(
        player, on_start=started.append, on_finish=lambda *args: finished.append(args)
    )
    # Enqueue both before starting the consumer thread, so ordering is
    # decided by priority rather than a race against the thread start.
    queue.enqueue(announcement_id=1, priority="NORMAL", wav_path="a.wav")
    queue.enqueue(announcement_id=2, priority="EMERGENCY", wav_path="b.wav")

    queue.start()
    try:
        deadline = time.monotonic() + 2
        while len(finished) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
    finally:
        queue.stop()

    assert player.played == ["b.wav", "a.wav"]
    assert started == [2, 1]


def test_playback_queue_skips_cancelled_item():
    player = FakePlayer()
    finished = []

    queue = PlaybackQueue(
        player, on_start=lambda *_: None, on_finish=lambda *args: finished.append(args)
    )
    queue.enqueue(announcement_id=99, priority="NORMAL", wav_path="c.wav")
    queue.cancel(99)

    queue.start()
    try:
        deadline = time.monotonic() + 2
        while not finished and time.monotonic() < deadline:
            time.sleep(0.02)
    finally:
        queue.stop()

    assert finished == [(99, False, "cancelled")]
    assert player.played == []
