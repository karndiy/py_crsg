DASHBOARD_PAGES = ["/", "/inbox", "/announcements", "/senders", "/calls", "/audio", "/settings"]


def _login(client, app):
    return client.post(
        "/login",
        data={"username": app.config["ADMIN_USERNAME"], "password": app.config["ADMIN_PASSWORD"]},
        follow_redirects=True,
    )


def test_dashboard_pages_redirect_to_login_when_unauthenticated(client):
    for path in DASHBOARD_PAGES:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_login_with_bad_credentials_is_rejected(client):
    response = client.post(
        "/login", data={"username": "admin", "password": "wrong"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_dashboard_pages_render_when_authenticated(client, app):
    login_response = _login(client, app)
    assert login_response.status_code == 200

    for path in DASHBOARD_PAGES:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"


def test_announcements_page_renders_with_audio_path(client, app):
    _login(client, app)

    create_response = client.post(
        "/api/v1/announcements",
        json={"message": "test", "priority": "NORMAL"},
        headers={"X-API-Key": app.config["RADIO_API_KEY"]},
    )
    assert create_response.status_code == 201
    public_id = create_response.get_json()["id"]

    from extensions import db
    from models import Announcement

    with app.app_context():
        announcement = Announcement.query.filter_by(public_id=public_id).first()
        announcement.audio_path = "/home/pi/community-radio/static/audio/announcement_test.wav"
        db.session.commit()

    response = client.get("/announcements")
    assert response.status_code == 200
    assert b"/static/audio/announcement_test.wav" in response.data


def test_logout_requires_login_again(client, app):
    _login(client, app)
    client.get("/logout")
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
