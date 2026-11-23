"""Manual test: connect to the modem and print every decoded SMS as it
arrives. Run on the target Raspberry Pi with the real SIM7600 attached
-- CLAUDE.md forbids reporting a hardware test as passing without this.

Usage: python scripts/test_sms.py [serial_port]
"""

from __future__ import annotations

import logging
import sys
import time

from config import Config
from modules.sms_gateway.modem import AtCommandManager, SerialModemTransport
from modules.sms_gateway.sms_reader import SmsReaderWorker


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    port = sys.argv[1] if len(sys.argv) > 1 else Config.SMS_PORT
    transport = SerialModemTransport(port=port, baudrate=Config.SMS_BAUD)
    manager = AtCommandManager(transport)
    manager.connect()

    def on_message(sms, index):
        print(f"[{index}] {sms.sender} ({sms.encoding}): {sms.text}")

    worker = SmsReaderWorker(manager, on_message, auto_delete=False)
    worker.initialize()
    worker.start()

    print(f"Listening for SMS on {port}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        worker.stop()
        manager.disconnect()


if __name__ == "__main__":
    main()
