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
    assert "status_hero" in data
    assert "bento" in data
    assert "running_now" in data


def test_status():
    r = client.get("/api/v1/status?heavy=false")
    assert r.status_code == 200
    assert "summary" in r.json()


def test_cron():
    r = client.get("/api/v1/cron")
    assert r.status_code == 200
    assert "items" in r.json()


def test_plugins():
    r = client.get("/api/v1/plugins")
    assert r.status_code == 200


def test_insights_cost():
    r = client.get("/api/v1/insights/cost")
    assert r.status_code == 200
    assert "total_usd" in r.json()


def test_search():
    r = client.get("/api/v1/search?q=mission")
    assert r.status_code == 200


def test_tasks_list():
    r = client.get("/api/v1/tasks")
    assert r.status_code == 200
    assert "items" in r.json()


def test_insights_repos():
    r = client.get("/api/v1/insights/repos")
    assert r.status_code == 200
    assert "items" in r.json()
