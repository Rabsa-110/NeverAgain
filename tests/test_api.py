from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_optimizer():
    payload = {
        "demand": [10]*24,
        "solar": [5]*24,
        "tariff": [2]*24,
        "battery_capacity": 100,
        "operator_notes": [
            "Reduce grid usage"
        ]
    }

    response = client.post(
        "/optimize-energy",
        json=payload
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
