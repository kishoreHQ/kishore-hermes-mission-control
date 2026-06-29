"""API integration tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_today():
    r = client.get("/api/v1/today")
    assert r.status_code == 200
    data = r.json()
    assert "greeting" in data
    assert "metrics" in data


def test_plugins():
    r = client.get("/api/v1/plugins")
    assert r.status_code == 200
    assert "items" in r.json()
