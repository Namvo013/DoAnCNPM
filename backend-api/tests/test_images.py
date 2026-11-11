import asyncio

from app.services.images import MAX_IMAGE_BYTES
from app.services.auth import hash_password

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def login_admin(client) -> None:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "image-admin@example.com",
                "display_name": "Image admin",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password("image-test-password"),
            }
        )
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "image-admin@example.com", "password": "image-test-password"},
    )
    assert response.status_code == 200


def test_admin_uploads_image_and_can_fetch_it(client) -> None:
    login_admin(client)

    response = client.post(
        "/api/admin/images/upload",
        files={"file": ("poi.png", PNG_BYTES + b"trailing image metadata", "image/png")},
    )

    assert response.status_code == 200
    image_url = response.json()["image_url"]
    assert image_url.startswith("/media/images/")
    assert client.get(image_url).content == PNG_BYTES + b"trailing image metadata"
    poi_response = client.post(
        "/api/admin/pois",
        json={
            "name": "Photo POI",
            "coordinates": {"latitude": 10, "longitude": 106},
            "geofence_radius_m": 25,
            "image_url": image_url,
            "category": "museum",
            "content": {"vi": "Nội dung có ảnh."},
        },
    )
    assert poi_response.status_code == 201
    public_poi = client.get(f"/api/pois/{poi_response.json()['id']}").json()
    assert public_poi["image_url"] == image_url


def test_image_upload_requires_admin_and_rejects_invalid_or_oversized_files(client) -> None:
    unauthorized = client.post(
        "/api/admin/images/upload",
        files={"file": ("poi.png", PNG_BYTES, "image/png")},
    )
    assert unauthorized.status_code == 401

    login_admin(client)
    invalid = client.post(
        "/api/admin/images/upload",
        files={"file": ("fake.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 415

    oversized = client.post(
        "/api/admin/images/upload",
        files={"file": ("large.png", PNG_BYTES + b"\x00" * MAX_IMAGE_BYTES, "image/png")},
    )
    assert oversized.status_code == 413
