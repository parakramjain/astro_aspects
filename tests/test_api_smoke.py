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
    headers = {
        "Authorization": "Bearer test-token",
        "X-Correlation-ID": "11111111-2222-3333-4444-555555555555",
        "X-Transaction-ID": "txn-test-01",
        "X-Session-ID": "sess-test-01",
        "X-App-ID": "pytest",
    }
    r = client.post("/api/natal/characteristics", json=payload, headers=headers)
    assert r.status_code == 200, f"Unexpected {r.status_code}: {r.text}"
    data = r.json()
    assert "data" in data
    assert "description" in data["data"]
