import asyncio
import csv
import io
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from bson import ObjectId

from app.services.auth import hash_password


def seed_report_data(client: TestClient) -> date:
    database = client.app.state.test_database
    asyncio.run(
        database.admins.insert_one(
            {
                "email": "report-viewer@example.com",
                "display_name": "Report viewer",
                "role": "analytics_viewer",
                "is_active": True,
                "password_hash": hash_password("report-viewer-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "report-viewer@example.com", "password": "report-viewer-password"},
    )
    poi_id = ObjectId()
    asyncio.run(
        database.pois.insert_one(
            {
                "_id": poi_id,
                "name": "Report POI",
                "location": {"type": "Point", "coordinates": [106.0, 10.0]},
                "geofence_radius_m": 25,
                "is_active": True,
            }
        )
    )
    today = date.today()
    start = datetime.combine(today, datetime.min.time(), timezone.utc)
    docs = [
        {"event_type": "poi_enter", "poi_id": poi_id, "language": "vi", "created_at": start + timedelta(hours=1)},
        {"event_type": "poi_enter", "poi_id": poi_id, "language": "en", "created_at": start + timedelta(hours=2)},
        {"event_type": "poi_enter", "poi_id": poi_id, "language": "vi", "created_at": start + timedelta(days=1)},
        {"event_type": "visitor_connect", "poi_id": None, "language": "vi", "created_at": start + timedelta(hours=3)},
    ]
    asyncio.run(database.visits.insert_many(docs))
    return today


def test_report_totals_and_groupings_by_poi_language_and_day(client: TestClient) -> None:
    report_date = seed_report_data(client)

    response = client.get(
        "/api/admin/reports",
        params={"start_date": report_date.isoformat(), "end_date": report_date.isoformat()},
    )

    assert response.status_code == 200
    report = response.json()
    assert report["total_visits"] == 2
    assert report["by_poi"] == [
        {"poi_id": report["by_poi"][0]["poi_id"], "name": "Report POI", "visits": 2}
    ]
    assert report["by_language"] == [
        {"language": "en", "visits": 1},
        {"language": "vi", "visits": 1},
    ]
    assert report["by_day"] == [{"date": report_date.isoformat(), "visits": 2}]


def test_visitor_count_counts_connection_events_in_requested_time_range(client: TestClient) -> None:
    report_date = seed_report_data(client)
    start = datetime.combine(report_date, datetime.min.time(), timezone.utc)
    response = client.get(
        "/api/admin/reports/visitor-count",
        params={
            "start": start.isoformat(),
            "end": (start + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json() == {"total_visits": 1}


def test_report_exports_csv_excel_and_pdf(client: TestClient) -> None:
    report_date = seed_report_data(client)
    common_params = {"start_date": report_date.isoformat(), "end_date": report_date.isoformat()}

    csv_response = client.get("/api/admin/reports/export", params={**common_params, "format": "csv"})
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "Total visits".encode("utf-8") in csv_response.content
    rows = list(csv.reader(io.StringIO(csv_response.content.decode("utf-8-sig"))))
    assert ["Total visits", "2"] in rows

    xlsx_response = client.get("/api/admin/reports/export", params={**common_params, "format": "xlsx"})
    assert xlsx_response.status_code == 200
    workbook = load_workbook(io.BytesIO(xlsx_response.content), read_only=True)
    assert workbook["Summary"]["B4"].value == 2
    assert workbook["By POI"]["B2"].value == "Report POI"

    pdf_response = client.get("/api/admin/reports/export", params={**common_params, "format": "pdf"})
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")


def test_empty_report_returns_404_and_invalid_range_returns_422(client: TestClient) -> None:
    login_viewer = asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "empty-viewer@example.com",
                "display_name": "Empty report viewer",
                "role": "analytics_viewer",
                "is_active": True,
                "password_hash": hash_password("empty-viewer-password"),
            }
        )
    )
    assert login_viewer.inserted_id
    client.post(
        "/api/auth/login",
        json={"email": "empty-viewer@example.com", "password": "empty-viewer-password"},
    )
    empty_params = {"start_date": "2026-10-01", "end_date": "2026-10-02"}
    assert client.get("/api/admin/reports", params=empty_params).status_code == 404
    for export_format in ("csv", "xlsx", "pdf"):
        response = client.get(
            "/api/admin/reports/export",
            params={**empty_params, "format": export_format},
        )
        assert response.status_code == 404
    invalid = client.get(
        "/api/admin/reports",
        params={"start_date": "2026-10-02", "end_date": "2026-10-01"},
    )
    assert invalid.status_code == 422
