from fastapi.testclient import TestClient

from app.main import app


client=TestClient(app)


def test_dataset_and_metric_endpoints():
    assert client.get("/api/v1/datasets").status_code==200
    response=client.get("/api/v1/datasets/hmda_2025_de/metrics/applications")
    assert response.status_code==200
    assert response.json()["rows"][0]["value"]==55183


def test_missing_import_returns_service_unavailable(tmp_path):
    response=client.get("/api/v1/datasets/not-found")
    assert response.status_code==404


def test_disabled_analysis_is_actionable_not_server_error():
    response=client.get("/api/v1/datasets/hmda_2025_de/funnel")
    assert response.status_code==422
    assert "需要用户" in response.json()["detail"]

