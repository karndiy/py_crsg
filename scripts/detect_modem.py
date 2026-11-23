"""Find the SIM7600's actual serial port.

CLAUDE.md explicitly warns against assuming a fixed device path like
/dev/ttyUSB2 — run this on the target Raspberry Pi to find out which
port is actually right, then put that in SMS_PORT in .env.
"""

from __future__ import annotations

import sys

from modules.sms_gateway.modem import AtCommandManager, SerialModemTransport, discover_serial_ports


def probe_port(port: str, baudrate: int = 115200) -> bool:
    transport = SerialModemTransport(port=port, baudrate=baudrate, timeout=2.0)
    manager = AtCommandManager(transport)
    try:
        manager.connect()
        manager.send_command("AT", timeout=2.0)
        return True
    except Exception:
        return False
    finally:
        manager.disconnect()


def main() -> None:
    ports = discover_serial_ports()
    if not ports:
        print("No serial ports found on this machine.")
        sys.exit(1)

    print(f"Found {len(ports)} serial port(s): {', '.join(ports)}")
    for port in ports:
        print(f"Probing {port} ...", end=" ")
        if probe_port(port):
            print("AT OK -- likely a SIM7600 AT command port")
        else:
            print("no response")


if __name__ == "__main__":
    main()
