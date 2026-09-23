"""Fixtures. Outbound HTTP is routed back into the app itself (httpx ASGITransport),
so tests exercise the real demo APIs end to end with no network."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable, Iterator

import httpx
import pytest

_TMP = tempfile.mkdtemp(prefix="databridge-tests-")
os.environ.update(
    ENVIRONMENT="development",
    DATABASE_URL=f"sqlite:///{_TMP}/test.db",
    SECRET_KEY="test-secret-not-used-anywhere-else-0123456789",
    PUBLIC_API_URL="http://localhost:8000",
    APP_URL="http://localhost:3000",
    RETRY_BASE_DELAY_SECONDS="0",
    SCHEDULER_ENABLED="false",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.connectors import http as outbound  # noqa: E402
from app.core.rate_limit import reset_rate_limits  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.demo import api as demo_api  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "correct-horse-battery"
DEMO = "http://localhost:8000/demo"


@pytest.fixture(autouse=True)
def fresh_state() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    demo_api.reset()
    outbound.set_transport(httpx.ASGITransport(app=app))
    yield
    outbound.set_transport(None)


def new_client() -> TestClient:
    return TestClient(app, base_url="http://localhost:8000")


@pytest.fixture
def make_user() -> Callable[[str], TestClient]:
    clients: list[TestClient] = []

    def _make(email: str = "dev@example.com") -> TestClient:
        c = new_client().__enter__()
        clients.append(c)
        assert c.post("/api/auth/register", json={"email": email, "password": PASSWORD, "name": "Dev"}).status_code == 201
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def user(make_user) -> TestClient:
    return make_user()


def credential(c: TestClient, **body) -> dict:  # noqa: ANN003
    response = c.post("/api/credentials", json=body)
    assert response.status_code == 201, response.text
    return response.json()


CUSTOMER_MAPPING = [
    {"source": "first_name", "target": "name"},
    {"source": "mail", "target": "email"},
    {"source": "age", "target": "age", "transform": "to_number"},
    {"source": "newsletter", "target": "subscribed", "transform": "to_boolean"},
    {"source": "address.city", "target": "location.city"},
    {"source": "id", "target": "external_id", "transform": "to_string"},
]


@pytest.fixture
def customers_integration(user: TestClient) -> dict:
    source_cred = credential(user, name="CRM", auth_type="bearer", secret="demo-source-token")
    dest_cred = credential(user, name="Marketing", auth_type="api_key", header_name="X-API-Key", secret="demo-destination-key")
    response = user.post("/api/integrations", json={
        "name": "Customers → Marketing",
        "source_type": "rest",
        "source_config": {"url": f"{DEMO}/source/customers", "records_path": "data", "pagination": "page",
                          "params": {"per_page": "20"}},
        "source_credential_id": source_cred["id"],
        "destination_type": "rest",
        "destination_config": {"url": f"{DEMO}/destination/customers", "method": "POST"},
        "destination_credential_id": dest_cred["id"],
        "mapping": CUSTOMER_MAPPING,
    })
    assert response.status_code == 201, response.text
    return response.json()


def wait_for_run(c: TestClient, run_id: int, timeout: float = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = c.get(f"/api/runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} didn't finish")
