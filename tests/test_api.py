from fastapi.testclient import TestClient

from core.app import create_app
from core.config import Settings


def test_health_check() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_score_endpoint_returns_full_result() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/score/test-cell-123")
    body = response.json()
    assert response.status_code == 200
    assert body["cell_id"] == "test-cell-123"
    assert 0 <= body["score"] <= 100
    assert set(body["indicators"]) == {"ndvi", "savi", "evi", "nbr"}


def test_invalid_cell_id_is_rejected() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/score/not valid")
    assert response.status_code == 422


def test_chainlink_score_endpoint_is_compact() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/chainlink/score/test-cell-123")
    assert response.status_code == 200
    assert set(response.json()) == {"score"}
