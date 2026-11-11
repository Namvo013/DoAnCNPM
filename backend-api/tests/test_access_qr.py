from fastapi.testclient import TestClient

from app.routers import access_qr


def test_mobile_access_qr_uses_lan_address_for_localhost(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(access_qr, "get_lan_ip", lambda: "192.168.1.25")

    response = client.get("/access-qr", headers={"host": "localhost:8000"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "http://192.168.1.25:8000/tourist-pwa/tour.html" in response.text
    assert "<svg" in response.text


def test_mobile_access_qr_preserves_public_tunnel_origin(client: TestClient) -> None:
    response = client.get("https://tour.example.com/access-qr")

    assert response.status_code == 200
    assert "https://tour.example.com/tourist-pwa/tour.html" in response.text
