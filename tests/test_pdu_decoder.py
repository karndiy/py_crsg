from modules.sms_gateway.pdu_decoder import (
    PduDecodeError,
    decode_gsm7,
    decode_pdu,
    decode_ucs2,
)


def test_decode_gsm7_known_vector():
    # Widely-cited GSM 03.38 7-bit packing example.
    data = bytes.fromhex("C8F71D14969741F977FD07")
    assert decode_gsm7(data, 12) == "How are you?"


def test_decode_ucs2_roundtrip():
    text = "สวัสดี"
    data = text.encode("utf-16-be")
    assert decode_ucs2(data) == text


def test_decode_full_sms_deliver_pdu_gsm7():
    parts = [
        "00",  # SMSC length = 0
        "04",  # PDU type: SMS-DELIVER, no UDH
        "0A",  # sender length = 10 digits
        "81",  # sender type-of-address (national)
        "8021436587",  # sender number semi-octets -> 0812345678
        "00",  # TP-PID
        "00",  # TP-DCS = GSM7
        "52605121030082",  # TP-SCTS -> 2025-06-15 12:30:00 +07:00
        "0C",  # TP-UDL = 12 septets
        "C8F71D14969741F977FD07",  # "How are you?"
    ]
    sms = decode_pdu("".join(parts))

    assert sms.sender == "0812345678"
    assert sms.encoding == "GSM7"
    assert sms.text == "How are you?"
    assert sms.concatenation is None
    assert sms.timestamp.isoformat() == "2025-06-15T12:30:00+07:00"


def test_decode_full_sms_deliver_pdu_ucs2_with_concatenation():
    thai_text = "สวัสดี"
    body = thai_text.encode("utf-16-be")

    udh_ref, udh_total, udh_seq = 0xAB, 2, 1
    header_inner = bytes([0x00, 0x03, udh_ref, udh_total, udh_seq])
    udh = bytes([len(header_inner)]) + header_inner
    user_data = udh + body

    parts = [
        "00",
        "44",  # PDU type: SMS-DELIVER with UDHI set
        "0A",
        "81",
        "8021436587",
        "00",
        "08",  # TP-DCS = UCS2
        "52605121030082",
        f"{len(user_data):02X}",
        user_data.hex().upper(),
    ]
    sms = decode_pdu("".join(parts))

    assert sms.encoding == "UCS2"
    assert sms.text == thai_text
    assert sms.concatenation.reference == udh_ref
    assert sms.concatenation.total_parts == udh_total
    assert sms.concatenation.sequence == udh_seq


def test_decode_pdu_rejects_invalid_hex():
    try:
        decode_pdu("not-hex")
    except PduDecodeError:
        return
    assert False, "expected PduDecodeError"


def test_decode_pdu_rejects_non_deliver_mti():
    # TP-MTI bits = 01 (SMS-SUBMIT), which this decoder does not support.
    parts = ["00", "01", "00"]
    try:
        decode_pdu("".join(parts))
    except PduDecodeError:
        return
    assert False, "expected PduDecodeError for non SMS-DELIVER PDU"
