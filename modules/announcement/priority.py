"""Shared priority ordering for the announcement and playback queues.

Lower number = plays sooner. EMERGENCY and HIGH only affect which
item is picked up *next* — a currently playing announcement is never
interrupted, regardless of what arrives after it (CLAUDE.md §10).
"""

from __future__ import annotations

PRIORITY_ORDER = {"EMERGENCY": 0, "HIGH": 1, "NORMAL": 2}
