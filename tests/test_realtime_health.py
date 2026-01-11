from fastapi.testclient import TestClient

from services.realtime.app import app


def test_realtime_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
