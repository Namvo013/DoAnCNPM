from fastapi.testclient import TestClient


def test_experimental_tourist_app_is_served_with_its_assets(client: TestClient) -> None:
    page = client.get("/experimental-tourist/")
    script = client.get("/experimental-tourist/app.js?v=7")
    stylesheet = client.get("/experimental-tourist/styles.css?v=7")

    assert page.status_code == 200
    assert 'data-view="amenities"' in page.text
    assert script.status_code == 200
    assert "loadNearbyAmenities" in script.text
    assert stylesheet.status_code == 200
    assert ".amenity-card" in stylesheet.text
