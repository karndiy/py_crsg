import pytest

from modules.sms_gateway.sender_validator import (
    CommandFormatError,
    normalize_phone_number,
    parse_command,
)


def test_parse_valid_command():
    parsed = parse_command("RADIO#482915#NORMAL#ขอเชิญประชาชนร่วมประชุมหมู่บ้าน")
    assert parsed.pin == "482915"
    assert parsed.priority == "NORMAL"
    assert parsed.message == "ขอเชิญประชาชนร่วมประชุมหมู่บ้าน"


def test_parse_emergency_priority():
    parsed = parse_command("RADIO#482915#HIGH#แจ้งเตือนระดับน้ำในคลองเพิ่มสูงขึ้น")
    assert parsed.priority == "HIGH"


@pytest.mark.parametrize(
    "raw_text",
    [
        "NOTRADIO#1234#NORMAL#hello",
        "RADIO#1234#NORMAL",
        "RADIO#abcd#NORMAL#hello",
        "RADIO#1234#URGENT#hello",
        "RADIO#1234#NORMAL#",
    ],
)
def test_rejects_malformed_commands(raw_text):
    with pytest.raises(CommandFormatError):
        parse_command(raw_text)


@pytest.mark.parametrize(
    "raw_number,expected",
    [
        ("0812345678", "0812345678"),
        ("+66812345678", "0812345678"),
        ("66812345678", "0812345678"),
        ("081-234-5678", "0812345678"),
    ],
)
def test_normalize_phone_number(raw_number, expected):
    assert normalize_phone_number(raw_number) == expected
