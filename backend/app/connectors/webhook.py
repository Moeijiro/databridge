"""Webhook source (inbound POST /hooks/{token}) and webhook destination (outbound POST)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from app.connectors import http
from app.connectors.auth import ResolvedAuth
from app.connectors.base import FetchResult, SendResult, TestResult, WebhookDestinationConfig, WebhookSourceConfig
from app.connectors.rest import deliver, extract_records
from app.core.config import settings


class WebhookSource:
    """Records arrive in the request body; there's nothing to fetch."""

    type = "webhook"
    config_model = WebhookSourceConfig

    async def fetch(self, config: WebhookSourceConfig, auth: ResolvedAuth, inbound: Any = None) -> FetchResult:
        return FetchResult(extract_records(inbound, config.records_path)[: settings.max_records_per_run])

    async def test(self, config: WebhookSourceConfig, auth: ResolvedAuth) -> TestResult:
        return TestResult(True, "Ready — POST JSON to the webhook URL to trigger a run")


def signature(secret: str, timestamp: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


class WebhookDestination:
    """POSTs {event, integration, data} to a URL. If a credential is attached, its
    secret signs the body (X-DataBridge-Signature) instead of being sent."""

    type = "webhook"
    config_model = WebhookDestinationConfig

    async def send(self, config: WebhookDestinationConfig, auth: ResolvedAuth, record: dict[str, Any], context: dict[str, Any]) -> SendResult:
        body = {"event": "record.synced", "integration": context.get("integration"), "data": record}
        headers = {**config.headers, "X-DataBridge-Delivery": uuid.uuid4().hex}
        # Serialise once and send exactly these bytes, so the signature can be verified.
        raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
        if auth.secret:
            timestamp = str(int(time.time()))
            headers |= {"X-DataBridge-Timestamp": timestamp, "X-DataBridge-Signature": signature(auth.secret, timestamp, raw)}
        return await deliver("POST", str(config.url), headers, body, record, content=raw)

    async def test(self, config: WebhookDestinationConfig, auth: ResolvedAuth) -> TestResult:
        try:
            response = await http.request("POST", str(config.url), headers=config.headers,
                                          json_body={"event": "databridge.test", "data": {}})
        except (http.UnsafeURL, http.RequestFailed) as exc:
            return TestResult(False, str(exc))
        return TestResult(response.ok, "Connected" if response.ok else f"HTTP {response.status}: {response.error_message()}",
                          response.status, response.elapsed_ms)
