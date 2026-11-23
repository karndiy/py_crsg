"""Dashboard admin authentication.

Admin credentials come from environment variables (CLAUDE.md §22), not
the database — there is no multi-user accounts table in this system's
design. Comparison is constant-time to avoid timing side-channels.
"""

from __future__ import annotations

import hmac
from functools import wraps
from typing import Callable

from flask import current_app, redirect, session, url_for

SESSION_KEY = "is_admin"


def check_admin_credentials(username: str, password: str) -> bool:
    expected_username = current_app.config["ADMIN_USERNAME"]
    expected_password = current_app.config["ADMIN_PASSWORD"]
    username_ok = hmac.compare_digest(username, expected_username)
    password_ok = hmac.compare_digest(password, expected_password)
    return username_ok and password_ok


def log_in_admin() -> None:
    session[SESSION_KEY] = True


def log_out_admin() -> None:
    session.pop(SESSION_KEY, None)


def is_admin_logged_in() -> bool:
    return bool(session.get(SESSION_KEY))


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin_logged_in():
            return redirect(url_for("dashboard.login"))
        return view(*args, **kwargs)

    return wrapped
