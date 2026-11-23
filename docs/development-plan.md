# Development Plan — Community Radio SMS Gateway

**Phase:** 3 — Plan (per CLAUDE.md §24, following the Phase 1 audit in
`docs/technical-audit.md`)

## What changed since the audit

Phase 1 found an empty repository (no prior demo to extend). Given that,
and the direct request to "create the program from CLAUDE.md," this
plan covers building the whole MVP in one pass rather than gating each
roadmap phase (§20) behind a separate approval — there was no existing
system whose compatibility needed preserving step by step. Each phase's
deliverable from §20 is still called out below so progress against the
original roadmap is traceable.

## Files added

```
app.py, worker.py, config.py, extensions.py, runtime.py
requirements.txt, .env.example

models/ (sms_message, authorized_sender, announcement, call_command,
         audio_file, system_log)

modules/sms_gateway/  (modem, pdu_decoder, multipart, sender_validator,
                        sms_reader)
modules/call_gateway/ (call_monitor, caller_validator, call_command)
modules/announcement/ (processor, queue, scheduler, priority)
modules/tts/           (piper_engine, audio_converter)
modules/audio/         (audio_player, device_manager, playback_queue)
modules/security/      (authentication, api_key, rate_limiter,
                         command_validator)

routes/    (dashboard, api, sms, announcement, sender, settings)
services/  (sms_service, call_service, announcement_service,
            audio_service)

templates/ (base, login, dashboard, inbox, announcements, senders,
            calls, audio, settings)
static/css/style.css

scripts/ (detect_modem, test_sms, test_call, test_tts, test_audio,
          create_admin)
tests/   (conftest, test_pdu_decoder, test_multipart,
          test_sender_validator, test_call_gateway, test_announcement,
          test_api)

systemd/ (community-radio.service, community-radio-worker.service)
models_voice/README.md, logs/.gitkeep
```

## Roadmap phase mapping (CLAUDE.md §20)

| Phase | Deliverable | Status |
|---|---|---|
| 1. Source Code Audit | `docs/technical-audit.md` | Done |
| 2. SIM7600 SMS Gateway | Serial Manager, AT Command Manager, SMS Reader | Code complete; **not yet run against real hardware** |
| 3. Thai PDU Decoder | GSM-7, UCS2, UDH, multipart, duplicate detection | Code complete, unit-tested against known-good vectors |
| 4. Sender Whitelist | CRUD, PIN hash, command parser, auth, rate limit | Code complete, unit/integration-tested |
| 5. Piper Offline TTS | Piper integration, WAV generation, error handling | Code complete; **Piper binary/voice model not installed in this environment** |
| 6. Speaker Playback | ALSA/aplay, playback queue, stop/retry | Code complete; **no ALSA on this (Windows) dev machine** |
| 7. Phone Call Gateway | Incoming call detection, whitelist, call command, logs | Code complete; **not yet run against real hardware** |
| 8. Dashboard | Overview, inbox, announcements, senders, calls, audio, settings | Code complete (server-rendered, Bootstrap 5) |
| 9. Production Deployment | systemd units, restart policy, offline operation | systemd units written; not yet deployed |

## Key design decisions beyond the literal spec

These fill gaps the spec left open, noted here rather than silently:

- **Cross-process control.** The Flask dashboard/API (`app.py`) and the
  background worker (`worker.py`) are separate OS processes per
  CLAUDE.md §17's systemd split. There's no message broker in the
  stated stack, so "Stop"/"Cancel" actions from the dashboard write a
  flag to SQLite (`Announcement.stop_requested_at`, `status`) and the
  worker polls for it (`worker.py`'s `StopSignalWatcher`,
  `modules/announcement/scheduler.py`'s pollers) rather than calling
  into the worker's in-memory queue directly.
- **Call → announcement mapping.** The schema in §13 has no column
  linking a caller's phone number to *which* canned call command fires.
  Since DTMF/IVR is explicitly out of scope (§9), `AuthorizedSender`
  gained a `default_call_command_id` FK.
- **AT command multiplexing.** A single reader thread inside
  `AtCommandManager` demultiplexes command responses from unsolicited
  notifications (`+CMTI`, `RING`/`+CLIP`), which is what lets the SMS
  reader and call monitor share one serial port safely (§6's "AT
  Command Manager" requirement).
- **Admin password hashing** uses a constant-time compare against the
  `.env` value directly (not bcrypt) since the admin credential's
  source of truth already *is* the `.env` file, not a database row;
  authorized-sender PINs, which *are* stored in the database, use
  `werkzeug.security.generate_password_hash`.

## Known limitations / explicitly deferred

- No hardware test has been run (no SIM7600, no Raspberry Pi, no ALSA,
  no Piper binary in this environment) — CLAUDE.md forbids reporting a
  hardware test as passing without one, so none is claimed here. See
  the Test Plan in the final report for what to run on-device.
- GSM-7 decoding with a concatenated-SMS header (multipart + GSM-7
  simultaneously) has lower test confidence than the UCS2 path, which
  is what Thai text actually uses — see the PDU decoder test file for
  what is and isn't covered by a verified vector.
- The dashboard's Play/Stop/Cancel buttons are plain HTML forms that
  POST to the API; the API requires an `X-API-Key` header a browser
  form can't send. They're wired up for a future small JS layer
  (`fetch()` with the key) rather than functioning today — flagged
  directly in `templates/announcements.html`.
- "Replay" of an already-synthesized announcement re-runs Piper rather
  than reusing the cached WAV file.
