import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from metadata_platform.seed import build_platform  # noqa: E402
from metadata_platform.service import create_app  # noqa: E402


@pytest.fixture()
def client():
    catalog, glossary, lineage, access, _audit = build_platform()
    return TestClient(create_app(catalog, glossary, lineage, access))


def test_health_and_search(client):
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/search", params={"q": "orders"})
    assert response.status_code == 200
    assert response.json()[0]["asset_id"] == "tbl-orders"


def test_impact_endpoint(client):
    response = client.get("/lineage/tbl-orders/impact")
    assert response.json()["downstream"] == ["dash-revenue", "model-churn"]


def test_access_request_endpoint(client):
    response = client.post("/access-requests", json={
        "asset_id": "tbl-orders",
        "requester": "jordan-lee",
        "justification": "analysis",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "requested"
