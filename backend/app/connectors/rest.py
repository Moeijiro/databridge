"""Generic REST API source and destination."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from app.connectors import http
from app.connectors.auth import ResolvedAuth
from app.connectors.base import (
    ConnectorError,
    FetchResult,
    RestDestinationConfig,
    RestSourceConfig,
    SendResult,
    TestResult,
)
from app.core.config import settings
from app.transforms.paths import MISSING, get_path

_PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_.\-]+)\}")


def extract_records(payload: Any, records_path: str) -> list[dict[str, Any]]:
    data = get_path(payload, records_path) if records_path else payload
    if data is MISSING:
        raise ConnectorError(f"No '{records_path}' in the response")
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ConnectorError(f"'{records_path or 'response'}' isn't a list of records")
    return [item for item in data if isinstance(item, dict)]


class RestSource:
    type = "rest"
    config_model = RestSourceConfig

    async def _page(self, config: RestSourceConfig, auth: ResolvedAuth, page: int | None) -> tuple[list[dict], int]:
        params = dict(config.params)
        if page is not None:
            params[config.page_param] = str(page)
        response, attempts, error = await http.send_with_retries(
            config.method, str(config.url), headers={**config.headers, **auth.headers()}, params=params,
        )
        if response is None:
            raise ConnectorError(f"{error} (after {attempts} attempts)")
        if not response.ok:
            raise ConnectorError(f"Source returned {response.status}: {response.error_message()}")
        try:
            payload = response.json()
        except ValueError:
            raise ConnectorError("Source didn't return JSON") from None
        return extract_records(payload, config.records_path), response.elapsed_ms

    async def fetch(self, config: RestSourceConfig, auth: ResolvedAuth, inbound: Any = None) -> FetchResult:
        if config.pagination == "none":
            records, elapsed = await self._page(config, auth, None)
            return FetchResult(records[: settings.max_records_per_run], 1, elapsed)
        records: list[dict] = []
        total_ms, pages = 0, 0
        for page in range(1, config.max_pages + 1):
            batch, elapsed = await self._page(config, auth, page)
            pages, total_ms = pages + 1, total_ms + elapsed
            records.extend(batch)
            if not batch or len(records) >= settings.max_records_per_run:
                break
        return FetchResult(records[: settings.max_records_per_run], pages, total_ms)

    async def test(self, config: RestSourceConfig, auth: ResolvedAuth) -> TestResult:
        try:
            response = await http.request(config.method, str(config.url), headers={**config.headers, **auth.headers()},
                                          params={**config.params, **({config.page_param: "1"} if config.pagination == "page" else {})})
        except http.UnsafeURL as exc:
            return TestResult(False, str(exc))
        except http.RequestFailed as exc:
            return TestResult(False, str(exc))
        if not response.ok:
            return TestResult(False, f"HTTP {response.status}: {response.error_message()}", response.status, response.elapsed_ms)
        try:
            records = extract_records(response.json(), config.records_path)
        except (ValueError, ConnectorError) as exc:
            return TestResult(False, f"Connected, but {exc}", response.status, response.elapsed_ms)
        sample_fields = sorted({key for record in records[:20] for key in record})[:40]
        return TestResult(True, f"Connected · {len(records)} records on the first page", response.status, response.elapsed_ms,
                          {"records": len(records), "fields": sample_fields, "sample": records[0] if records else None})


def fill_url(template: str, record: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        value = get_path(record, match.group(1))
        if value is MISSING or value is None:
            raise KeyError(match.group(1))
        return quote(str(value), safe="")
    return _PLACEHOLDER.sub(repl, template)


async def deliver(method: str, url_template: str, headers: dict[str, str], body: Any, record: dict[str, Any],
                  content: bytes | None = None) -> SendResult:
    try:
        url = fill_url(url_template, record)
    except KeyError as missing:
        return SendResult(False, None, 0, f"URL placeholder {{{missing.args[0]}}} has no value in the record")
    try:
        if content is not None:
            response, attempts, error = await http.send_with_retries(
                method, url, headers={**headers, "Content-Type": "application/json"}, content=content)
        else:
            response, attempts, error = await http.send_with_retries(method, url, headers=headers, json_body=body)
    except http.UnsafeURL as exc:
        return SendResult(False, None, 0, str(exc))
    if response is None:
        return SendResult(False, None, attempts, error)
    if response.ok:
        return SendResult(True, response.status, attempts, elapsed_ms=response.elapsed_ms)
    return SendResult(False, response.status, attempts, f"Destination returned {response.status}: {response.error_message()}",
                      response.elapsed_ms)


class RestDestination:
    type = "rest"
    config_model = RestDestinationConfig

    async def send(self, config: RestDestinationConfig, auth: ResolvedAuth, record: dict[str, Any], context: dict[str, Any]) -> SendResult:
        return await deliver(config.method, config.url, {**config.headers, **auth.headers()}, record, record)

    async def test(self, config: RestDestinationConfig, auth: ResolvedAuth) -> TestResult:
        """Reachability only — nothing is written. Placeholders are filled with 'test'."""
        url = _PLACEHOLDER.sub("test", config.url)
        try:
            response = await http.request("OPTIONS", url, headers={**config.headers, **auth.headers()})
        except (http.UnsafeURL, http.RequestFailed) as exc:
            return TestResult(False, str(exc))
        reachable = response.status < 500 and response.status not in (401, 403)
        message = "Connected" if reachable else f"HTTP {response.status}: {response.error_message()}"
        if response.status in (401, 403):
            message = f"HTTP {response.status}: the credential was rejected"
        return TestResult(reachable, message, response.status, response.elapsed_ms)
