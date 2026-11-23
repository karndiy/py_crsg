# Community Radio SMS Gateway — Offline Edition

Raspberry Pi + SIM7600 LTE modem + Flask + SQLite + Piper offline TTS.
Receives SMS and phone-call commands from authorized numbers, with no
WAN internet required for core operation, and announces them over a
community speaker. See `CLAUDE.md` for the full specification this was
built from, and `docs/technical-audit.md` / `docs/development-plan.md`
for what exists today vs. what still needs on-device testing.

## Requirements

- Raspberry Pi OS 64-bit (or any Linux host with ALSA, for the worker)
- Python 3.10+
- A SIM7600 LTE modem connected over USB/serial, with a SIM card
- A Piper-compatible Thai voice model (not included — see
  `models_voice/README.md`)
- An audio amplifier + speaker (never wire a passive speaker directly
  into the Pi's audio output)

## Install

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sqlite3 alsa-utils git

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: SECRET_KEY, ADMIN_PASSWORD, RADIO_API_KEY, SMS_PORT, PIPER_MODEL, ...

sudo usermod -aG dialout,audio $USER
# log out and back in for the group change to take effect
```

Find the modem's actual serial port — never assume `/dev/ttyUSB2`:

```bash
python scripts/detect_modem.py
```

## Running

**Local development** (no hardware required — SMS/call gateways
auto-disable if the configured port can't be opened):

```bash
python app.py        # dashboard + API on http://localhost:5000
python worker.py      # background worker (separate terminal)
```

**Production (Raspberry Pi, systemd):**

```bash
sudo cp systemd/community-radio.service systemd/community-radio-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now community-radio.service community-radio-worker.service
journalctl -u community-radio -u community-radio-worker -f
```

Set the dashboard admin credentials:

```bash
python scripts/create_admin.py
```

## Tests

```bash
pytest -q
```

38 unit/integration tests cover the PDU decoder (validated against a
known-good GSM-7 vector, plus UCS2 + concatenation), multipart
reassembly, command parsing, phone-number normalization, call-command
resolution, the priority/playback queues, and the REST API. **None of
this exercises real hardware** — per CLAUDE.md, a hardware test is
never reported as passing without running it on the actual Raspberry
Pi + SIM7600 + speaker setup. On-device, also run:

```bash
python scripts/test_sms.py [port]     # watch decoded SMS arrive live
python scripts/test_call.py [port]    # watch caller ID on incoming calls
python scripts/test_tts.py "ข้อความทดสอบ"
python scripts/test_audio.py static/audio/tts_test.wav
```

## Architecture notes

- `app.py` (Flask dashboard + REST API) and `worker.py` (SMS reader,
  call monitor, TTS, audio playback) are **separate processes** — see
  `systemd/`. They only share state through SQLite, never Python
  memory. Dashboard actions like "Stop" set a DB flag the worker polls
  for; see `docs/development-plan.md` for why.
- A single `AtCommandManager` (`modules/sms_gateway/modem.py`) owns the
  serial port and demultiplexes AT command responses from unsolicited
  notifications (`+CMTI` for new SMS, `RING`/`+CLIP` for calls), so the
  SMS reader and call monitor can safely share one physical port.
- Announcements never overlap in playback regardless of priority; a
  currently-playing announcement is never interrupted, only whichever
  plays *next* is priority-ordered (EMERGENCY > HIGH > NORMAL).

## Troubleshooting

| Symptom | Check |
|---|---|
| `scripts/detect_modem.py` finds no ports | Check USB cable/power to the SIM7600; try `dmesg \| tail` after plugging in |
| AT commands time out | Wrong baud rate or port; confirm with `minicom -D /dev/ttyUSBx -b 115200` |
| SMS never arrives at the dashboard | Check `AT+CPIN?` returns `READY`; check sender is in the whitelist and PIN is correct; check `journalctl -u community-radio-worker` |
| No audio output | `aplay -l` to confirm ALSA sees the device; check `AUDIO_DEVICE` in `.env` matches; confirm amplifier is powered |
| Piper fails | Confirm `PIPER_EXECUTABLE` is on `PATH` and `PIPER_MODEL` points at a file that exists; check the voice model's architecture matches Piper's version |
| Dashboard unreachable from another device on the LAN | Confirm `APP_HOST=0.0.0.0` in `.env` and the Pi's firewall allows the port |

## Security

Do not expose the dashboard or API directly to the public internet
without a reverse proxy, TLS, and a firewall in front of it — this
system is designed for LAN access only. See CLAUDE.md §21 for the full
list of operational safety requirements, and verify compliance with any
applicable broadcasting regulations before using this for public
announcements.
