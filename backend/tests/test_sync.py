"""Full sync runs against the demo APIs: fetch, map, send, retries and failures."""

from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.connectors import http as outbound
from app.demo import api as demo_api
from tests.conftest import DEMO, credential, wait_for_run


def run(c: TestClient, integration_id: int) -> dict:
    started = c.post(f"/api/integrations/{integration_id}/run")
    assert started.status_code == 202, started.text
    return wait_for_run(c, started.json()["id"])


def test_a_run_fetches_every_page_maps_and_delivers(user: TestClient, customers_integration: dict) -> None:
    result = run(user, customers_integration["id"])
    assert result["records_read"] == 43, "three pages of 20/20/3"
    assert (result["records_successful"], result["records_failed"]) == (42, 1)
    assert result["status"] == "partial"

    received = demo_api._received["customers"]
    sample = next(r for r in received if r["external_id"] == "1001")
    source = demo_api.CUSTOMERS[0]
    assert sample["name"] == source["first_name"] and sample["email"] == source["mail"]
    assert isinstance(sample["age"], int) and isinstance(sample["subscribed"], bool)
    assert sample["location"] == {"city": source["address"]["city"]}


def test_the_failed_record_is_inspectable_and_masked(user: TestClient, customers_integration: dict) -> None:
    result = run(user, customers_integration["id"])
    [failure] = user.get(f"/api/runs/{result['id']}/failures").json()
    assert failure["record_index"] == 31 and failure["stage"] == "send"
    assert failure["status_code"] == 400
    assert failure["error"] == "Destination returned 400: Missing required field: email"
    assert failure["attempts"] == 1, "a 400 is permanent — never retried"
    assert failure["preview"]["first_name"] == demo_api.CUSTOMERS[30]["first_name"]
    assert failure["preview"]["address"] == "••• hidden", "personal fields aren't exposed"
    assert "Missing required field: email" in result["error_summary"]


def test_transient_failures_are_retried_and_succeed(user: TestClient, customers_integration: dict) -> None:
    result = run(user, customers_integration["id"])
    flaky = [c for c in demo_api.CUSTOMERS if str(c["id"]).endswith("7") and "mail" in c]
    assert result["retries"] == len(flaky) > 0
    received_ids = {r["external_id"] for r in demo_api._received["customers"]}
    assert {str(c["id"]) for c in flaky} <= received_ids


def test_retries_give_up_after_the_configured_attempts(user: TestClient, customers_integration: dict) -> None:
    calls = []

    def always_down(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503, json={"error": "down"})

    outbound.set_transport(httpx.MockTransport(always_down))
    result = run(user, customers_integration["id"])
    assert result["status"] == "failed"
    assert len(calls) == 3, "the source fetch: 3 attempts, then the run fails"
    assert result["error_summary"].startswith("Fetch failed: Source returned 503")


def test_a_bad_source_credential_fails_the_whole_run(user: TestClient, customers_integration: dict) -> None:
    user.patch(f"/api/credentials/{customers_integration['source_credential']['id']}", json={"secret": "wrong"})
    result = run(user, customers_integration["id"])
    assert result["status"] == "failed" and result["records_read"] == 0
    assert "401" in result["error_summary"]


def test_transform_failures_are_recorded_per_record(user: TestClient) -> None:
    created = user.post("/api/integrations", json={
        "name": "Orders", "source_type": "rest",
        "source_config": {"url": f"{DEMO}/source/orders", "records_path": "results.items"},
        "destination_type": "rest", "destination_config": {"url": f"{DEMO}/destination/orders"},
        "mapping": [
            {"source": "order.number", "target": "order_id", "required": True},
            {"source": "amount", "target": "total", "transform": "to_number"},
            {"source": "is_paid", "target": "paid", "transform": "to_boolean"},
            {"source": "customer.email", "target": "email"},
            {"source": "customer.phone", "target": "phone", "required": True},  # no order has one
        ],
    }).json()
    result = run(user, created["id"])
    assert (result["records_read"], result["records_failed"], result["status"]) == (18, 18, "failed")
    failure = user.get(f"/api/runs/{result['id']}/failures").json()[0]
    assert failure["stage"] == "transform" and failure["error"] == "phone: Missing required field: customer.phone"


def test_webhook_source_runs_on_post(user: TestClient) -> None:
    signing = credential(user, name="Signing", auth_type="bearer", secret="whsec_test_123456")
    created = user.post("/api/integrations", json={
        "name": "Form → webhook", "source_type": "webhook", "source_config": {"records_path": "submissions"},
        "destination_type": "webhook", "destination_config": {"url": f"{DEMO}/destination/webhook"},
        "destination_credential_id": signing["id"],
        "mapping": [{"source": "full_name", "target": "name"}, {"source": "email", "target": "email", "transform": "lowercase"}],
    }).json()
    token = created["webhook_url"].rsplit("/", 1)[-1]

    anonymous = TestClient(user.app, base_url="http://localhost:8000")
    accepted = anonymous.post(f"/hooks/{token}", json={"submissions": [{"full_name": "Ana", "email": "ANA@EXAMPLE.COM"}]})
    assert accepted.status_code == 202
    result = wait_for_run(user, accepted.json()["run_id"])
    assert (result["trigger"], result["status"], result["records_successful"]) == ("webhook", "success", 1)

    [delivery] = demo_api._received["webhook"]
    assert '"email":"ana@example.com"' in delivery["body"]
    assert delivery["headers"]["x-databridge-signature"].startswith("sha256=")

    from app.connectors.webhook import signature

    expected = signature("whsec_test_123456", delivery["headers"]["x-databridge-timestamp"], delivery["body"].encode())
    assert delivery["headers"]["x-databridge-signature"] == expected, "the receiver can verify what it got"

    assert anonymous.post("/hooks/not-a-real-token", json={}).status_code == 404
    assert anonymous.post(f"/hooks/{token}", content=b"not json", headers={"Content-Type": "application/json"}).status_code == 400
    big = b'{"x":"' + b"a" * (1024 * 1024) + b'"}'
    assert anonymous.post(f"/hooks/{token}", content=big, headers={"Content-Type": "application/json"}).status_code == 413


def test_scheduled_integrations_run_when_due(user: TestClient, customers_integration: dict) -> None:
    import asyncio

    from app.db.base import utcnow
    from app.db.session import SessionLocal
    from app.models import Integration
    from app.scheduler.loop import tick

    user.patch(f"/api/integrations/{customers_integration['id']}", json={"schedule": "hourly"})
    assert asyncio.run(tick(wait=True)) == [], "not due yet"
    with SessionLocal() as db:
        db.get(Integration, customers_integration["id"]).next_run_at = utcnow()
        db.commit()
    [run_id] = asyncio.run(tick(wait=True))
    assert user.get(f"/api/runs/{run_id}").json()["trigger"] == "schedule"
    with SessionLocal() as db:
        assert db.get(Integration, customers_integration["id"]).next_run_at > utcnow()
