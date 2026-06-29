"""SQLite metrics store (PRD §8.1)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    category TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    tags TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT,
    severity TEXT
);
CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    agent TEXT NOT NULL,
    tokens_input INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    run_id TEXT
);
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric TEXT NOT NULL,
    expected_value REAL NOT NULL,
    actual_value REAL NOT NULL,
    deviation_percent REAL NOT NULL,
    severity TEXT NOT NULL,
    resolved_at DATETIME,
    resolution TEXT
);
"""


def db_path() -> Path:
    return Path(settings.hermes_data_dir) / "metrics.db"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=5)
    con.row_factory = sqlite3.Row
    con.executescript(_SCHEMA)
    return con


def record_cost(provider: str, model: str, agent: str, tokens_in: int, tokens_out: int, cost_usd: float, run_id: str = "") -> None:
    with _connect() as con:
        con.execute(
            "INSERT INTO costs (provider, model, agent, tokens_input, tokens_output, cost_usd, run_id) VALUES (?,?,?,?,?,?,?)",
            (provider, model, agent, tokens_in, tokens_out, cost_usd, run_id),
        )


def cost_summary(days: int = 7) -> dict:
    with _connect() as con:
        total = con.execute(
            "SELECT coalesce(sum(cost_usd),0), coalesce(sum(tokens_input+tokens_output),0) FROM costs "
            "WHERE timestamp >= datetime('now', ?)",
            (f"-{days} days",),
        ).fetchone()
        daily = con.execute(
            "SELECT date(timestamp) as day, sum(cost_usd) as cost FROM costs "
            "WHERE timestamp >= datetime('now', ?) GROUP BY day ORDER BY day",
            (f"-{days} days",),
        ).fetchall()
    return {
        "total_usd": float(total[0] or 0),
        "total_tokens": int(total[1] or 0),
        "daily": [{"day": r["day"], "cost_usd": r["cost"]} for r in daily],
    }


def ingest_session_cost(stats: dict) -> None:
    if not stats.get("cost"):
        return
    record_cost("hermes", "aggregate", "sessions", int(stats.get("tokens", 0)), 0, float(stats.get("cost", 0)))


def record_system_metrics() -> None:
    import subprocess

    try:
        load = subprocess.run(["bash", "-lc", "cat /proc/loadavg | awk '{print $1}'"], capture_output=True, text=True, timeout=3)
        load_val = float((load.stdout or "0").strip() or 0)
    except Exception:
        load_val = 0.0
    with _connect() as con:
        con.execute(
            "INSERT INTO metrics (category, metric, value, unit) VALUES ('system','load_1m',?,'')",
            (load_val,),
        )


def list_anomalies(limit: int = 20) -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM anomalies WHERE resolved_at IS NULL ORDER BY detected_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_repos() -> list[dict]:
    import json
    import os
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return []
    try:
        req = Request(
            "https://api.github.com/user/repos?per_page=10&sort=updated",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [
            {"name": r.get("full_name"), "private": r.get("private"), "updated_at": r.get("updated_at")}
            for r in data[:10]
        ]
    except (URLError, OSError, json.JSONDecodeError, TimeoutError):
        return []
