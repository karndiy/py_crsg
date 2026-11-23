"""API key verification for programmatic access to /api/v1 endpoints."""

from __future__ import annotations

import hmac
from functools import wraps
from typing import Callable

from flask import current_app, jsonify, request

API_KEY_HEADER = "X-API-Key"


def verify_api_key(provided_key: str) -> bool:
    expected_key = current_app.config["RADIO_API_KEY"]
    if not provided_key:
        return False
    return hmac.compare_digest(provided_key, expected_key)


def api_key_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        provided_key = request.headers.get(API_KEY_HEADER, "")
        if not verify_api_key(provided_key):
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped
