def test_health_does_not_require_api_key(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_sms_list_requires_api_key(client):
    response = client.get("/api/v1/sms")
    assert response.status_code == 401


def test_sender_crud_flow(client, api_headers):
    create_response = client.post(
        "/api/v1/senders",
        json={"phone_number": "0812345678", "pin": "482915", "can_sms": True, "can_call": False},
        headers=api_headers,
    )
    assert create_response.status_code == 201
    sender_id = create_response.get_json()["id"]

    list_response = client.get("/api/v1/senders", headers=api_headers)
    assert list_response.status_code == 200
    assert any(s["phone_number"] == "0812345678" for s in list_response.get_json())

    update_response = client.put(
        f"/api/v1/senders/{sender_id}",
        json={"is_active": False},
        headers=api_headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["is_active"] is False

    delete_response = client.delete(f"/api/v1/senders/{sender_id}", headers=api_headers)
    assert delete_response.status_code == 204


def test_sender_create_rejects_duplicate_phone_number(client, api_headers):
    payload = {"phone_number": "0899999999", "pin": "123456"}
    first = client.post("/api/v1/senders", json=payload, headers=api_headers)
    assert first.status_code == 201

    second = client.post("/api/v1/senders", json=payload, headers=api_headers)
    assert second.status_code == 409


def test_announcement_create_and_lifecycle(client, api_headers):
    create_response = client.post(
        "/api/v1/announcements",
        json={"message": "ทดสอบระบบ", "priority": "HIGH"},
        headers=api_headers,
    )
    assert create_response.status_code == 201
    body = create_response.get_json()
    assert body["status"] == "queued"
    assert body["priority"] == "HIGH"
    public_id = body["id"]

    get_response = client.get(f"/api/v1/announcements/{public_id}", headers=api_headers)
    assert get_response.status_code == 200

    cancel_response = client.post(
        f"/api/v1/announcements/{public_id}/cancel", headers=api_headers
    )
    assert cancel_response.status_code == 200
    assert cancel_response.get_json()["status"] == "cancelled"

    second_cancel = client.post(
        f"/api/v1/announcements/{public_id}/cancel", headers=api_headers
    )
    assert second_cancel.status_code == 400


def test_announcement_create_rejects_invalid_priority(client, api_headers):
    response = client.post(
        "/api/v1/announcements",
        json={"message": "hello", "priority": "URGENT"},
        headers=api_headers,
    )
    assert response.status_code == 400


def test_announcement_create_rejects_empty_message(client, api_headers):
    response = client.post(
        "/api/v1/announcements", json={"message": "  "}, headers=api_headers
    )
    assert response.status_code == 400
