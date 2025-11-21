import json
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_natal_characteristics_smoke():
    payload = {
        "name": "Amit",
        "dateOfBirth": "1991-07-14",
        "timeOfBirth": "22:35:00",
        "placeOfBirth": "Mumbai, IN",
        "timeZone": "Asia/Kolkata",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }
    r = client.post("/api/natal/characteristics", json=payload)
    assert r.status_code == 200, f"Unexpected {r.status_code}: {r.text}"
    data = r.json()
    assert "meta" in data and "data" in data
    assert "description" in data["data"] and "kpis" in data["data"]
