from fastapi.testclient import TestClient

from core.app import create_app
from core.config import Settings

PROJECT_ID = "0x0000000000000000000000000000000000000001"


def test_health_check() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_score_endpoint_receives_project_id_only() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get(f"/score/{PROJECT_ID}")
    body = response.json()
    assert response.status_code == 200
    assert set(body) == {"project_id", "cell_id", "scoring", "fraud_scoring", "measurement_date"}
    assert body["project_id"] == PROJECT_ID
    assert body["cell_id"] == "test-cell-123"
    assert body["scoring"] == "0.80"
    assert body["fraud_scoring"] in {"0.10", "0.50"}
    assert isinstance(body["measurement_date"], int)


def test_invalid_project_id_is_rejected() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/score/not-valid")
    assert response.status_code == 422


def test_post_score_accepts_only_project_id() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.post("/score", json={"project_id": PROJECT_ID})
    assert response.status_code == 200
    assert response.json()["project_id"] == PROJECT_ID


def test_old_cell_id_payload_is_rejected() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.post("/score", json={"cell_id": "test-cell-123", "previous_score": 100})
    assert response.status_code == 422


def test_chainlink_score_endpoint_returns_scaled_contract_payload() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get(f"/chainlink/score/{PROJECT_ID}")
    body = response.json()
    assert response.status_code == 200
    assert set(body) == {"project_id", "cell_id", "scoring", "fraud_scoring", "measurement_date", "schema_version"}
    assert body["scoring"] == 80
    assert body["fraud_scoring"] in {10, 50}
    assert body["schema_version"] == "chainlink-project-scoring-v1"
