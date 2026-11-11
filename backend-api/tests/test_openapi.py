from fastapi.testclient import TestClient


def test_openapi_documents_request_response_and_file_schemas(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]
    assert "/api/health" in paths
    assert "/api/auth/login" in paths
    assert "/api/admin/pois" in paths
    assert "/api/admin/reports/export" in paths

    login = paths["/api/auth/login"]["post"]
    assert login["requestBody"]["content"]["application/json"]["schema"]
    admin_response = schema["components"]["schemas"]["AdminResponse"]
    assert "password" not in admin_response["properties"]
    assert "password_hash" not in admin_response["properties"]
    export_responses = paths["/api/admin/reports/export"]["get"]["responses"]["200"]["content"]
    assert "text/csv" in export_responses
    assert "application/pdf" in export_responses


def test_cors_allows_dashboard_origins_with_credentials(client: TestClient) -> None:
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert response.headers["access-control-allow-credentials"] == "true"
