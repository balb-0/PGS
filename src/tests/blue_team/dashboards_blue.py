from fastapi.testclient import TestClient

from src.core.api import app


client = TestClient(app)
HEADERS_VALIDOS = {
    "account-key": "conta-teste-123",
    "app-key": "app-teste-456",
}


def test_dashboard_business_retorna_contrato_basico():
    response = client.get("/api/v1/dashboard/business", headers=HEADERS_VALIDOS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboard"] == "business"
    assert "summary" in payload
    assert "trends" in payload


def test_dashboard_system_health_retorna_contrato_basico():
    response = client.get("/api/v1/dashboard/system-health", headers=HEADERS_VALIDOS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboard"] == "system-health"
    assert "summary" in payload
    assert "breakdown" in payload


def test_dashboard_testing_gap_retorna_contrato_basico():
    response = client.get("/api/v1/dashboard/testing-gap", headers=HEADERS_VALIDOS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["dashboard"] == "testing-gap"
    assert "summary" in payload
    assert "coverage" in payload


def test_dashboard_metadata_retorna_filtros():
    response = client.get("/api/v1/dashboard/metadata", headers=HEADERS_VALIDOS)
    assert response.status_code == 200
    payload = response.json()
    assert "dashboards" in payload
    assert "filters" in payload


def test_dashboard_rejeita_interval_invalido():
    response = client.get(
        "/api/v1/dashboard/business?interval=xyz",
        headers=HEADERS_VALIDOS,
    )
    assert response.status_code == 400
