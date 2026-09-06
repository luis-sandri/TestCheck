from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


def test_health_check(monkeypatch) -> None:
    monkeypatch.setattr(main, "ensure_database_ready", lambda: None)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
