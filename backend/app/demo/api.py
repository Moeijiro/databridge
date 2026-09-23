"""Local demo APIs — a working source and destination with no external services.

    GET  /demo/source/customers        paged; needs Authorization: Bearer demo-source-token
    GET  /demo/source/orders           nested fields, numbers and yes/no stored as text
    POST /demo/destination/customers   needs X-API-Key: demo-destination-key; requires name + email
    POST /demo/destination/orders      requires order_id, total (number), paid (boolean)
    POST /demo/destination/webhook     accepts anything
    GET  /demo/destination/{kind}      what has been received (newest first)

Two behaviours are deliberate, so a demo run shows the failure paths honestly:
record #31 of the customers has no email (a permanent 400), and every record
whose id ends in 7 gets one 503 before succeeding (a transient failure the
retry logic recovers from).
"""

from __future__ import annotations

import random
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter(prefix="/demo", tags=["demo"], include_in_schema=True)

SOURCE_TOKEN = "demo-source-token"
DESTINATION_KEY = "demo-destination-key"

_FIRST = ["John", "Maria", "Aiko", "Liam", "Sofia", "Noah", "Amara", "Mateo", "Elena", "Kofi", "Hana", "Lucas",
          "Priya", "Oscar", "Zara", "Ivan", "Chloe", "Ravi", "Nina", "Tomás", "Leila"]
_LAST = ["Smith", "Garcia", "Tanaka", "Murphy", "Rossi", "Kim", "Okafor", "Silva", "Novak", "Mensah", "Sato",
         "Martin", "Shah", "Berg"]
_CITIES = ["Lisbon", "Berlin", "Austin", "Osaka", "Toronto", "Nairobi", "Madrid", "Oslo", "Seoul", "Dublin"]


def _customers() -> list[dict[str, Any]]:
    rng = random.Random(42)
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    people = []
    for i in range(1, 44):  # 43 customers
        first, last = rng.choice(_FIRST), rng.choice(_LAST)
        person = {
            "id": 1000 + i,
            "first_name": first,
            "last_name": last,
            "mail": f"{first.lower()}.{last.lower()}{i}@example.com",
            "age": str(rng.randint(19, 71)),
            "newsletter": rng.choice(["yes", "no"]),
            "plan": rng.choice(["free", "pro", "team"]),
            "address": {"city": rng.choice(_CITIES), "country": "—"},
            "signed_up": (base + timedelta(days=i * 2)).date().isoformat(),
        }
        if i == 31:
            person.pop("mail")  # the one record the destination will reject
        people.append(person)
    return people


def _orders() -> list[dict[str, Any]]:
    rng = random.Random(7)
    return [
        {
            "order": {"number": f"SO-{5200 + i}", "status": rng.choice(["paid", "pending", "paid", "paid"])},
            "amount": f"{rng.randint(12, 480)}.{rng.choice(['00', '50', '99'])}",
            "is_paid": rng.choice(["yes", "yes", "no"]),
            "customer": {"email": f"buyer{i}@example.com", "country_code": rng.choice(["PT", "DE", "US", "JP"])},
            "items": rng.randint(1, 6),
        }
        for i in range(1, 19)
    ]


CUSTOMERS = _customers()
ORDERS = _orders()
_received: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
_attempts: dict[str, int] = defaultdict(int)


def _unauthorised(message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=401)


@router.get("/source/customers", summary="Demo source: customers (paged)")
def source_customers(
    authorization: str | None = Header(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> Any:
    if authorization != f"Bearer {SOURCE_TOKEN}":
        return _unauthorised("Missing or invalid bearer token")
    start = (page - 1) * per_page
    chunk = CUSTOMERS[start:start + per_page]
    return {"data": chunk, "page": page, "per_page": per_page, "total": len(CUSTOMERS), "has_more": start + per_page < len(CUSTOMERS)}


@router.get("/source/orders", summary="Demo source: orders (no auth)")
def source_orders() -> Any:
    return {"results": {"items": ORDERS, "count": len(ORDERS)}}


def _flaky(key: str) -> bool:
    """One 503 per record whose key ends in 7, then success — a transient failure."""
    if not key.endswith("7"):
        return False
    _attempts[key] += 1
    return _attempts[key] == 1


@router.post("/destination/customers", summary="Demo destination: create a customer")
async def destination_customers(request: Request, x_api_key: str | None = Header(default=None)) -> Any:
    if x_api_key != DESTINATION_KEY:
        return _unauthorised("Invalid API key")
    body = await request.json()
    if not isinstance(body, dict):
        return JSONResponse({"error": "Expected a JSON object"}, status_code=400)
    for field in ("name", "email"):
        if not body.get(field):
            return JSONResponse({"error": f"Missing required field: {field}"}, status_code=400)
    if "@" not in str(body["email"]):
        return JSONResponse({"error": "email is not a valid address"}, status_code=422)
    if _flaky(str(body.get("external_id", ""))):
        return JSONResponse({"error": "Temporarily unavailable"}, status_code=503)
    _received["customers"].appendleft({**body, "_received_at": datetime.now(timezone.utc).isoformat()})
    return JSONResponse({"id": len(_received["customers"]), "status": "created"}, status_code=201)


@router.post("/destination/orders", summary="Demo destination: create an order")
async def destination_orders(request: Request) -> Any:
    body = await request.json()
    problems = []
    if not body.get("order_id"):
        problems.append("order_id is required")
    if not isinstance(body.get("total"), int | float):
        problems.append("total must be a number")
    if not isinstance(body.get("paid"), bool):
        problems.append("paid must be true or false")
    if problems:
        return JSONResponse({"error": "; ".join(problems)}, status_code=422)
    _received["orders"].appendleft({**body, "_received_at": datetime.now(timezone.utc).isoformat()})
    return JSONResponse({"status": "created"}, status_code=201)


@router.post("/destination/webhook", summary="Demo webhook receiver")
async def destination_webhook(request: Request) -> Any:
    raw = await request.body()
    _received["webhook"].appendleft({"headers": {k: v for k, v in request.headers.items() if k.startswith("x-databridge")},
                                     "body": raw.decode(errors="replace")[:2000]})
    return {"received": True}


@router.api_route("/destination/{kind}", methods=["OPTIONS"], include_in_schema=False)
def destination_options(kind: str, x_api_key: str | None = Header(default=None)) -> Response:
    """What "Test destination" calls: reachability and auth, without writing anything."""
    if kind not in ("customers", "orders", "webhook"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if kind == "customers" and x_api_key != DESTINATION_KEY:
        return _unauthorised("Invalid API key")
    return Response(status_code=204, headers={"Allow": "POST, OPTIONS"})


@router.get("/destination/{kind}", summary="What the demo destination has received")
def received(kind: str) -> Any:
    return {"kind": kind, "count": len(_received[kind]), "items": list(_received[kind])[:50]}


def reset() -> None:
    _received.clear()
    _attempts.clear()
