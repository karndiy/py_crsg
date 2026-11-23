"""Flask application factory: dashboard + REST API.

Flask never touches the serial port directly (CLAUDE.md §4) — SMS/call
handling and TTS/audio playback run in the separate worker process
(worker.py). This process only reads/writes SQLite and renders pages.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Flask

from config import get_config
from extensions import db, migrate
from routes.announcement import announcement_bp
from routes.api import api_bp
from routes.dashboard import dashboard_bp
from routes.sender import sender_bp
from routes.settings import settings_bp
from routes.sms import sms_bp


def create_app(config_name: Optional[str] = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    logging.basicConfig(level=app.config["LOG_LEVEL"])

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(sms_bp)
    app.register_blueprint(announcement_bp)
    app.register_blueprint(sender_bp)
    app.register_blueprint(settings_bp)

    @app.template_filter("basename")
    def basename_filter(path: Optional[str]) -> str:
        # Announcement.audio_path is an absolute filesystem path (Piper
        # and aplay need a real path); templates need just the filename
        # to build a /static/audio/... URL from it.
        return os.path.basename(path) if path else ""

    with app.app_context():
        import models  # noqa: F401  (registers models with SQLAlchemy before create_all)

        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["APP_HOST"], port=app.config["APP_PORT"])
