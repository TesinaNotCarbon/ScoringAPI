from fastapi.testclient import TestClient

from core.app import create_app
from core.config import Settings


def test_health_check() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_score_endpoint_returns_simplified_result() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/score/test-cell-123")
    body = response.json()
    assert response.status_code == 200
    assert set(body) == {"score", "criticality", "description", "measurement_date"}
    assert 0 <= body["score"] <= 100
    assert body["criticality"] in {"low", "medium", "high"}
    assert body["description"]


def test_invalid_cell_id_is_rejected() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/score/not valid")
    assert response.status_code == 422


def test_chainlink_score_endpoint_returns_consensus_payload_without_description() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/chainlink/score/test-cell-123")
    body = response.json()
    assert response.status_code == 200
    assert set(body) == {
        "cell_id",
        "score",
        "criticality",
        "criticality_code",
        "decision",
        "flags",
        "measurement_date",
        "schema_version",
    }
    assert "description" not in body
    assert body["criticality_code"] in {0, 1, 2}
    assert body["decision"] in {"approve", "review", "reject"}


def test_previous_score_regression_is_sent_to_ai_analysis() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.post("/score", json={"cell_id": "test-cell-123", "previous_score": 100})
    body = response.json()
    assert response.status_code == 200
    assert body["criticality"] in {"medium", "high"}
    assert "score_regression" in body["description"]


def test_drastic_improvement_is_sent_to_ai_analysis() -> None:
    app = create_app(Settings(environment="test", drastic_improvement_threshold=1))
    with TestClient(app) as client:
        response = client.get("/score/healthy-forest-cell?previous_score=0")
    body = response.json()
    assert response.status_code == 200
    assert body["criticality"] == "medium"
    assert "suspicious_score_improvement" in body["description"]


def test_measurement_date_query_param_affects_mock_observation() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        dry_response = client.get("/score/healthy-forest-cell?measurement_date=2026-07-15")
        wet_response = client.get("/score/healthy-forest-cell?measurement_date=2026-01-15")

    dry = dry_response.json()
    wet = wet_response.json()
    assert dry_response.status_code == 200
    assert wet_response.status_code == 200
    assert dry["measurement_date"] == "2026-07-15"
    assert wet["measurement_date"] == "2026-01-15"
    assert dry["score"] != wet["score"]
