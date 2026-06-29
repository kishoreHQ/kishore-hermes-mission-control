"""Deprecated V1 bridge — V1 mission-control.service on :8090 is retired."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

V1_STATUS_URL = "http://127.0.0.1:8090/api/status"


def fetch_v1_status(timeout: int = 8) -> dict | None:
    try:
        with urlopen(V1_STATUS_URL, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
