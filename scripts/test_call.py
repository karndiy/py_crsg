"""Manual test: connect to the modem and print caller ID for every
incoming call, without running the full call_service pipeline. Run on
the target Raspberry Pi with the real SIM7600 attached.

Usage: python scripts/test_call.py [serial_port]
"""

from __future__ import annotations

import logging
import sys
import time

from config import Config
from modules.call_gateway.call_monitor import CallMonitor
from modules.sms_gateway.modem import AtCommandManager, SerialModemTransport


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    port = sys.argv[1] if len(sys.argv) > 1 else Config.SMS_PORT
    transport = SerialModemTransport(port=port, baudrate=Config.SMS_BAUD)
    manager = AtCommandManager(transport)
    manager.connect()

    def on_call(caller_number):
        print(f"Incoming call from: {caller_number}")

    monitor = CallMonitor(manager, on_call, auto_reject=True)
    monitor.initialize()
    monitor.start()

    print(f"Listening for calls on {port}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()
        manager.disconnect()


if __name__ == "__main__":
    main()
