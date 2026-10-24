import asyncio

import pytest
from fastapi.testclient import TestClient

from app import metadata
from app.config import Settings
from app.main import create_app
from app.metadata import parse_metadata

CONTAINER_METADATA = {
    "Name": "web",
    "Image": "public.ecr.aws/example/aws-ecs-helloworld:1.0.0",
    "StartedAt": "2026-10-24T21:00:00Z",
    "Networks": [{"NetworkMode": "awsvpc", "IPv4Addresses": ["10.0.2.100"]}],
}
TASK_METADATA = {
    "Cluster": "arn:aws:ecs:us-east-1:111122223333:cluster/demo",
    "TaskARN": "arn:aws:ecs:us-east-1:111122223333:task/demo/158d1c8083dd49d6b527399fd6414f5c",
    "Family": "helloworld",
    "Revision": "7",
    "ServiceName": "helloworld-svc",
    "AvailabilityZone": "us-east-1a",
    "LaunchType": "FARGATE",
    "Limits": {"CPU": 0.25, "Memory": 512},
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ECS_CONTAINER_METADATA_URI_V4", raising=False)
    monkeypatch.setenv("MESSAGE", "Hello <ECS>")
    with TestClient(create_app(Settings.from_env())) as test_client:
        yield test_client


@pytest.fixture
def ecs_client(monkeypatch):
    async def fake_fetch(timeout):
        return parse_metadata(CONTAINER_METADATA, TASK_METADATA)

    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setattr("app.main.fetch_ecs_metadata", fake_fetch)
    with TestClient(create_app(Settings.from_env())) as test_client:
        yield test_client


def test_index_renders_html_and_escapes_values(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Hello &lt;ECS&gt;" in response.text
    assert "Running locally" in response.text
    assert "$" not in response.text
    assert "Content-Security-Policy" in response.headers


def test_index_shows_ecs_badge(ecs_client):
    assert "Running on Amazon ECS" in ecs_client.get("/").text


@pytest.mark.parametrize("path", ["/health", "/ready"])
def test_health_endpoints(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert client.head(path).status_code == 200


def test_ready_returns_503_before_startup(monkeypatch):
    monkeypatch.delenv("ECS_CONTAINER_METADATA_URI_V4", raising=False)
    response = TestClient(create_app(Settings.from_env())).get("/ready")
    assert response.status_code == 503


def test_info_outside_ecs(client):
    body = client.get("/api/info").json()
    assert body["ecs"] is None
    assert body["app"]["name"] == "aws-ecs-helloworld"
    assert body["runtime"]["uptime_seconds"] >= 0


def test_info_on_ecs(ecs_client):
    ecs = ecs_client.get("/api/info").json()["ecs"]
    assert ecs["cluster"] == "demo"
    assert ecs["region"] == "us-east-1"


def test_request_id_is_propagated(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_parse_metadata(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    result = parse_metadata(CONTAINER_METADATA, TASK_METADATA)
    assert result.cluster == "demo"
    assert result.task_id == "158d1c8083dd49d6b527399fd6414f5c"
    assert result.task_definition == "helloworld:7"
    assert result.region == "us-east-1"
    assert result.private_ip == "10.0.2.100"


def test_parse_metadata_tolerates_missing_fields():
    result = parse_metadata({}, {})
    assert result.cluster is None
    assert result.private_ip is None


def test_fetch_returns_none_outside_ecs(monkeypatch):
    monkeypatch.delenv(metadata.METADATA_ENV, raising=False)
    assert asyncio.run(metadata.fetch_ecs_metadata(timeout=1)) is None
