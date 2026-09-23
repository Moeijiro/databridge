"""Ownership, secret handling, SSRF protection and connection tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models import Credential
from tests.conftest import DEMO, credential


def test_secrets_are_encrypted_and_never_returned(user: TestClient) -> None:
    created = credential(user, name="Stripe", auth_type="bearer", secret="sk_live_supersecret_9876")
    assert created["secret_hint"] == "••••9876"
    listing = user.get("/api/credentials").text
    assert "supersecret" not in listing and "sk_live" not in listing
    with SessionLocal() as db:
        stored = db.get(Credential, created["id"]).secret_encrypted
    assert "supersecret" not in stored


def test_integrations_never_echo_secrets(user: TestClient, customers_integration: dict) -> None:
    body = user.get(f"/api/integrations/{customers_integration['id']}").text
    assert "demo-source-token" not in body and "demo-destination-key" not in body


def test_other_users_see_nothing(user: TestClient, make_user, customers_integration: dict) -> None:
    run_id = user.post(f"/api/integrations/{customers_integration['id']}/run").json()["id"]
    other = make_user("other@example.com")
    iid, cid = customers_integration["id"], customers_integration["source_credential"]["id"]
    assert other.get(f"/api/integrations/{iid}").status_code == 404
    assert other.post(f"/api/integrations/{iid}/run").status_code == 404
    assert other.delete(f"/api/integrations/{iid}").status_code == 404
    assert other.get(f"/api/runs/{run_id}").status_code == 404
    assert other.get(f"/api/runs/{run_id}/failures").status_code == 404
    assert other.patch(f"/api/credentials/{cid}", json={"name": "mine"}).status_code == 404
    assert other.get("/api/runs").json() == [] and other.get("/api/integrations").json() == []
    # Nor borrow someone else's credential for their own integration.
    stolen = other.post("/api/integrations", json={
        "name": "x", "source_type": "rest", "source_config": {"url": f"{DEMO}/source/orders"}, "source_credential_id": cid,
        "destination_type": "rest", "destination_config": {"url": f"{DEMO}/destination/orders"}})
    assert stolen.status_code == 404


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8080/admin", "http://localhost:6379/", "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/internal", "http://[::1]/", "file:///etc/passwd", "http://user:pass@example.com/",
    "http://printer.local/",
])
def test_internal_targets_are_refused(user: TestClient, url: str) -> None:
    response = user.post("/api/integrations", json={
        "name": "x", "source_type": "rest", "source_config": {"url": url},
        "destination_type": "rest", "destination_config": {"url": f"{DEMO}/destination/orders"}})
    assert response.status_code == 422, url


def test_secret_headers_must_use_a_credential(user: TestClient) -> None:
    response = user.post("/api/integrations", json={
        "name": "x", "source_type": "rest",
        "source_config": {"url": f"{DEMO}/source/orders", "headers": {"Authorization": "Bearer oops"}},
        "destination_type": "rest", "destination_config": {"url": f"{DEMO}/destination/orders"}})
    assert response.status_code == 422 and "stored credential" in response.json()["error"]["message"]


def test_connection_tests_report_status_and_time_without_secrets(user: TestClient) -> None:
    good = credential(user, name="CRM", auth_type="bearer", secret="demo-source-token")
    ok = user.post("/api/connections/test-source", json={
        "type": "rest", "config": {"url": f"{DEMO}/source/customers", "records_path": "data"}, "credential_id": good["id"]}).json()
    assert ok["ok"] and ok["status"] == 200 and ok["elapsed_ms"] is not None
    assert "mail" in ok["details"]["fields"]
    assert "demo-source-token" not in str(ok)

    bad = user.post("/api/connections/test-destination", json={
        "type": "rest", "config": {"url": f"{DEMO}/destination/customers"}}).json()
    assert not bad["ok"] and bad["status"] == 401 and "rejected" in bad["message"]


def test_mapping_preview_shows_output_or_the_error(user: TestClient) -> None:
    rules = [{"source": "first_name", "target": "name"}, {"source": "age", "target": "age", "transform": "to_number"}]
    ok = user.post("/api/mapping/preview", json={"sample": {"first_name": "John", "age": "42"}, "mapping": rules}).json()
    assert ok == {"ok": True, "output": {"name": "John", "age": 42}, "error": None}
    bad = user.post("/api/mapping/preview", json={"sample": {"first_name": "John", "age": "old"}, "mapping": rules}).json()
    assert not bad["ok"] and "can't convert 'old'" in bad["error"]


def test_webhook_sources_cannot_be_scheduled(user: TestClient) -> None:
    response = user.post("/api/integrations", json={
        "name": "x", "source_type": "webhook", "schedule": "hourly",
        "destination_type": "webhook", "destination_config": {"url": f"{DEMO}/destination/webhook"}})
    assert response.status_code == 422
