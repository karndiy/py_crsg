# Technical Audit — Community Radio SMS Gateway (Offline Edition)

**Date:** 2026-11-23
**Phase:** 1 — Source Code Audit (per CLAUDE.md §20, §24)

## Scope of this audit

CLAUDE.md's "First Task" (§24) assumes an existing demo with Flask, SQLite,
a dashboard, a webhook, and an announcement API already in place, and asks
for those to be inventoried before extending them with SIM7600, the Thai
PDU decoder, sender whitelist, Piper TTS, speaker playback, and the phone
call gateway.

**Finding: no such demo exists.** The working directory (`D:\py\py-crsg`)
contained only `CLAUDE.md.txt` (the spec itself) prior to this audit, with
no Python source, no Flask app, no SQLite database, no templates, and no
git history. The paired GitHub remote
(`https://github.com/karndiy/py_crsg.git`) was checked via `git ls-remote`
and is also empty — zero refs, zero commits.

**Conclusion:** this is a greenfield build, not an extension of prior work.
§24's Step 1–3 ("inspect existing code," "audit what exists vs. is
missing") therefore has nothing to inspect. This document records that
baseline so later phases aren't built on a false assumption of reused
code, and so the "don't delete or overwrite the existing system
unnecessarily" rule (§3 #3) is understood to not apply yet.

## Current repository state

| Item | Status |
|---|---|
| Source code (app.py, models/, modules/, routes/, services/) | Absent — none created |
| SQLite database / instance/ | Absent |
| Flask routes / REST API (§14) | Absent |
| Dashboard templates/static assets | Absent |
| Tests (unit/integration/hardware) | Absent |
| Git repository | Initialized this session (`git init`, `main` branch) |
| Remote | `origin` → `https://github.com/karndiy/py_crsg.git` (empty, added this session) |
| `.env` / `.env.example` | Absent |
| `requirements.txt` | Absent |
| CLAUDE.md | Present (renamed from `CLAUDE.md.txt` this session) |

## Dependencies

None declared yet — no `requirements.txt`, no `pyproject.toml`, no lockfile.

## Configuration

None present. CLAUDE.md §22 documents the intended `.env.example` shape
(`SMS_PORT`, `PIPER_MODEL`, `RATE_LIMIT_PER_HOUR`, etc.) but no file exists
on disk yet.

## What's missing relative to CLAUDE.md's full spec

Everything in §5 (Recommended Project Structure) needs to be created from
scratch: `app.py`, `config.py`, `extensions.py`, the `models/`, `modules/`,
`routes/`, `services/`, `templates/`, `static/`, `scripts/`, `tests/`,
and `systemd/` trees, plus `requirements.txt` and `.env.example`.

## Recommendation

Proceed to **Phase 2 (SIM7600 SMS Gateway)** per the roadmap in §20, but
treat it as new development rather than an extension — there is no
existing Serial Manager, AT Command Manager, or SMS Reader to build on.
Suggest starting with the Flask app skeleton + SQLite models (§13) first,
since Phases 2–7 all depend on having the database layer in place to
persist what they read.

Before any hardware-facing work (SIM7600, Piper, ALSA), note CLAUDE.md's
own constraint (§19): hardware tests must not be reported as PASS without
running on real Raspberry Pi + SIM7600 hardware. This development
environment is Windows, not a Raspberry Pi, so all hardware-dependent
modules will need mock-based unit tests (§4 "Hardware Module ต้อง
สามารถ Mock ได้ใน Unit Tests") until they can be verified on-device.
