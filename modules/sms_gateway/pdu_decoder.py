"""Decoder for GSM 03.40 SMS-DELIVER PDUs (GSM-7, UCS2, UDH/concatenation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

GSM7_BASIC_TABLE = (
    "@£$¥èéùìòÇ\nØø\rÅå"
    "Δ_ΦΓΛΩΠΨΣΘΞ\x1bÆæß"
    "É !\"#¤%&'()*+,-./"
    "0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNO"
    "PQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmno"
    "pqrstuvwxyzäöñüà"
)

GSM7_EXTENSION = {
    0x0A: "\x0C",
    0x14: "^",
    0x28: "{",
    0x29: "}",
    0x2F: "\\",
    0x3C: "[",
    0x3D: "~",
    0x3E: "]",
    0x40: "|",
    0x65: "€",
}


class PduDecodeError(ValueError):
    """Raised when a PDU cannot be parsed."""


@dataclass
class ConcatenationInfo:
    reference: int
    total_parts: int
    sequence: int


@dataclass
class DecodedSms:
    sender: str
    timestamp: datetime
    encoding: str
    text: str
    concatenation: Optional[ConcatenationInfo]
    raw_pdu: str


def _swap_nibbles(hex_str: str) -> str:
    out = []
    for i in range(0, len(hex_str), 2):
        pair = hex_str[i:i + 2]
        if len(pair) == 2:
            out.append(pair[1] + pair[0])
        else:
            out.append(pair[0])
    return "".join(out)


def _decode_semi_octet_number(raw: bytes) -> str:
    digits = _swap_nibbles(raw.hex())
    return digits.rstrip("Ff")


def _decode_address(raw: bytes, type_of_address: int) -> str:
    number = _decode_semi_octet_number(raw)
    if (type_of_address & 0x70) == 0x10:
        return "+" + number
    return number


def _decode_timezone_quarter_hours(byte_val: int) -> int:
    low_nibble = byte_val & 0x0F
    high_nibble = (byte_val >> 4) & 0x0F
    sign = -1 if (low_nibble & 0x08) else 1
    tens = low_nibble & 0x07
    units = high_nibble
    return sign * (tens * 10 + units)


def _decode_timestamp(raw: bytes) -> datetime:
    if len(raw) != 7:
        raise PduDecodeError("TP-SCTS must be exactly 7 octets")
    swapped = _swap_nibbles(raw[:6].hex())
    try:
        year = 2000 + int(swapped[0:2])
        month = int(swapped[2:4])
        day = int(swapped[4:6])
        hour = int(swapped[6:8])
        minute = int(swapped[8:10])
        second = int(swapped[10:12])
    except ValueError as exc:
        raise PduDecodeError(f"Invalid timestamp digits: {swapped}") from exc
    quarter_hours = _decode_timezone_quarter_hours(raw[6])
    tz = timezone(timedelta(minutes=quarter_hours * 15))
    return datetime(year, month, day, hour, minute, second, tzinfo=tz)


def _unpack_7bit_septets(data: bytes, septet_count: int, fill_bits: int = 0) -> List[int]:
    bits = "".join(f"{byte:08b}"[::-1] for byte in data)
    if fill_bits:
        bits = bits[fill_bits:]
    values: List[int] = []
    for i in range(septet_count):
        chunk = bits[i * 7:i * 7 + 7]
        if len(chunk) < 7:
            break
        values.append(int(chunk[::-1], 2))
    return values


def _septets_to_text(values: List[int]) -> str:
    chars: List[str] = []
    escape = False
    for value in values:
        if escape:
            if value in GSM7_EXTENSION:
                chars.append(GSM7_EXTENSION[value])
            elif value < len(GSM7_BASIC_TABLE):
                chars.append(GSM7_BASIC_TABLE[value])
            escape = False
            continue
        if value == 0x1B:
            escape = True
            continue
        if value < len(GSM7_BASIC_TABLE):
            chars.append(GSM7_BASIC_TABLE[value])
        else:
            chars.append("?")
    return "".join(chars)


def decode_gsm7(data: bytes, septet_count: int, fill_bits: int = 0) -> str:
    return _septets_to_text(_unpack_7bit_septets(data, septet_count, fill_bits))


def decode_ucs2(data: bytes) -> str:
    usable_len = len(data) - (len(data) % 2)
    return data[:usable_len].decode("utf-16-be", errors="replace")


def _classify_dcs(dcs: int) -> str:
    if (dcs & 0xC0) == 0x00:
        coding_group = (dcs >> 2) & 0x03
        if coding_group == 0x01:
            return "8BIT"
        if coding_group == 0x02:
            return "UCS2"
        return "GSM7"
    if (dcs & 0xF0) in (0xC0, 0xD0):
        return "GSM7"
    if (dcs & 0xF0) == 0xE0:
        return "UCS2"
    return "GSM7"


def _parse_udh(user_data: bytes) -> tuple[Optional[ConcatenationInfo], int]:
    if not user_data:
        return None, 0
    udhl = user_data[0]
    header = user_data[1:1 + udhl]
    total_header_len = 1 + udhl
    if len(header) < udhl:
        raise PduDecodeError("Truncated User Data Header")

    concat: Optional[ConcatenationInfo] = None
    pos = 0
    while pos + 1 < len(header):
        iei = header[pos]
        iedl = header[pos + 1]
        ied = header[pos + 2:pos + 2 + iedl]
        if iei == 0x00 and iedl == 3 and len(ied) == 3:
            concat = ConcatenationInfo(reference=ied[0], total_parts=ied[1], sequence=ied[2])
        elif iei == 0x08 and iedl == 4 and len(ied) == 4:
            reference = (ied[0] << 8) | ied[1]
            concat = ConcatenationInfo(reference=reference, total_parts=ied[2], sequence=ied[3])
        pos += 2 + iedl
    return concat, total_header_len


def decode_pdu(pdu_hex: str) -> DecodedSms:
    """Decode a GSM 03.40 SMS-DELIVER PDU (as returned by AT+CMGR) into a DecodedSms."""
    pdu_hex = pdu_hex.strip().upper()
    try:
        raw = bytes.fromhex(pdu_hex)
    except ValueError as exc:
        raise PduDecodeError(f"PDU is not valid hex: {exc}") from exc

    if len(raw) < 2:
        raise PduDecodeError("PDU too short")

    offset = 0
    smsc_len = raw[offset]
    offset += 1 + smsc_len

    if offset >= len(raw):
        raise PduDecodeError("PDU truncated after SMSC field")

    pdu_type = raw[offset]
    offset += 1
    mti = pdu_type & 0x03
    if mti != 0x00:
        raise PduDecodeError(f"Only SMS-DELIVER PDUs are supported (TP-MTI={mti})")
    udhi = bool(pdu_type & 0x40)

    sender_len_digits = raw[offset]
    offset += 1
    sender_type = raw[offset]
    offset += 1
    sender_octets = (sender_len_digits + 1) // 2
    sender_raw = raw[offset:offset + sender_octets]
    offset += sender_octets
    sender = _decode_address(sender_raw, sender_type)

    offset += 1  # TP-PID
    dcs = raw[offset]
    offset += 1
    encoding = _classify_dcs(dcs)

    scts_raw = raw[offset:offset + 7]
    offset += 7
    timestamp = _decode_timestamp(scts_raw)

    udl = raw[offset]
    offset += 1
    user_data = raw[offset:]

    concat: Optional[ConcatenationInfo] = None
    if udhi:
        concat, header_len = _parse_udh(user_data)
        body = user_data[header_len:]
        if encoding == "UCS2":
            text = decode_ucs2(body)
        elif encoding == "GSM7":
            fill_bits = (7 - (header_len * 8) % 7) % 7
            septets_in_header = (header_len * 8 + fill_bits) // 7
            message_septets = max(udl - septets_in_header, 0)
            text = decode_gsm7(body, message_septets, fill_bits=0)
        else:
            text = body.decode("latin-1", errors="replace")
    else:
        if encoding == "UCS2":
            text = decode_ucs2(user_data)
        elif encoding == "GSM7":
            text = decode_gsm7(user_data, udl)
        else:
            text = user_data.decode("latin-1", errors="replace")

    return DecodedSms(
        sender=sender,
        timestamp=timestamp,
        encoding=encoding,
        text=text,
        concatenation=concat,
        raw_pdu=pdu_hex,
    )
