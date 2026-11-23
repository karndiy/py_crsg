from datetime import datetime, timezone

from modules.sms_gateway.multipart import MultipartReassembler
from modules.sms_gateway.pdu_decoder import ConcatenationInfo, DecodedSms


def _part(seq: int, total: int, text: str, reference: int = 7) -> DecodedSms:
    return DecodedSms(
        sender="0812345678",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        encoding="UCS2",
        text=text,
        concatenation=ConcatenationInfo(reference=reference, total_parts=total, sequence=seq),
        raw_pdu=f"part{seq}",
    )


def test_single_part_message_passes_through_immediately():
    reassembler = MultipartReassembler()
    sms = DecodedSms(
        sender="0812345678",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        encoding="GSM7",
        text="hello",
        concatenation=None,
        raw_pdu="abc",
    )
    assert reassembler.add_part(sms) is sms


def test_waits_until_all_parts_arrive_then_reassembles_in_order():
    reassembler = MultipartReassembler()

    assert reassembler.add_part(_part(2, 3, "World")) is None
    assert reassembler.add_part(_part(1, 3, "Hello ")) is None

    result = reassembler.add_part(_part(3, 3, "!"))

    assert result is not None
    assert result.text == "Hello World!"
    assert reassembler.pending_count() == 0


def test_different_senders_do_not_interfere():
    reassembler = MultipartReassembler()
    part_a = _part(1, 2, "A1", reference=1)
    part_a.sender = "0811111111"
    part_b = _part(1, 2, "B1", reference=1)
    part_b.sender = "0822222222"

    assert reassembler.add_part(part_a) is None
    assert reassembler.add_part(part_b) is None
    assert reassembler.pending_count() == 2


def test_sweep_expired_drops_incomplete_groups():
    reassembler = MultipartReassembler(timeout_seconds=0)
    reassembler.add_part(_part(1, 2, "only one part"))

    expired = reassembler.sweep_expired()

    assert len(expired) == 1
    assert reassembler.pending_count() == 0
