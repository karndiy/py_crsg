"""Server-rendered dashboard pages (CLAUDE.md §15). Read-heavy pages
query models directly; anything that changes state goes through the
same services layer the REST API uses.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import Announcement, AuthorizedSender, CallLog, SmsMessage
from modules.security.authentication import (
    check_admin_credentials,
    is_admin_logged_in,
    log_in_admin,
    log_out_admin,
    login_required,
)
from services import audio_service

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if is_admin_logged_in():
        return redirect(url_for("dashboard.overview"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if check_admin_credentials(username, password):
            log_in_admin()
            return redirect(url_for("dashboard.overview"))
        flash("Invalid username or password", "error")

    return render_template("login.html")


@dashboard_bp.route("/logout")
@login_required
def logout():
    log_out_admin()
    return redirect(url_for("dashboard.login"))


@dashboard_bp.route("/")
@login_required
def overview():
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stats = {
        "sms_today": SmsMessage.query.filter(SmsMessage.received_at >= today_start).count(),
        "announcement_count": Announcement.query.count(),
        "queue_pending": Announcement.query.filter(
            Announcement.status.in_(("queued", "generating"))
        ).count(),
        "audio_status": audio_service.get_status(),
        "last_announcement": Announcement.query.order_by(
            Announcement.created_at.desc()
        ).first(),
    }
    return render_template("dashboard.html", stats=stats)


@dashboard_bp.route("/inbox")
@login_required
def inbox():
    messages = SmsMessage.query.order_by(SmsMessage.received_at.desc()).limit(200).all()
    return render_template("inbox.html", messages=messages)


@dashboard_bp.route("/announcements")
@login_required
def announcements():
    items = Announcement.query.order_by(Announcement.created_at.desc()).limit(200).all()
    return render_template("announcements.html", announcements=items)


@dashboard_bp.route("/senders")
@login_required
def senders():
    items = AuthorizedSender.query.order_by(AuthorizedSender.phone_number).all()
    return render_template("senders.html", senders=items)


@dashboard_bp.route("/calls")
@login_required
def calls():
    items = CallLog.query.order_by(CallLog.received_at.desc()).limit(200).all()
    return render_template("calls.html", calls=items)


@dashboard_bp.route("/audio")
@login_required
def audio():
    devices = audio_service.get_devices()
    status = audio_service.get_status()
    return render_template("audio.html", devices=devices, status=status)


@dashboard_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
