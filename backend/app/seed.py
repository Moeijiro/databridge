"""Demo workspace: ``python -m app.seed [--reset]``.

Creates the demo account, three credentials and three integrations wired to the
local demo APIs, then executes real runs through them (in-process, so no server
needs to be up) and spreads those runs over the past week.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import timedelta

import httpx
from sqlalchemy import select, update

from app.connectors import http as outbound
from app.core.config import settings
from app.core.security import encrypt_secret, generate_webhook_token, hash_password, hash_token, mask
from app.db.base import utcnow
from app.db.session import SessionLocal, init_db
from app.demo import api as demo_api
from app.models import Credential, Integration, SyncRun, User
from app.scheduler.schedule import next_run_after
from app.services import runner

EMAIL, PASSWORD = "demo@databridge.dev", "databridge-demo-1234"


def _credential(db, owner: User, name: str, auth_type: str, secret: str, header: str | None = None) -> Credential:  # noqa: ANN001
    row = Credential(owner_id=owner.id, name=name, auth_type=auth_type, header_name=header,
                     secret_encrypted=encrypt_secret(secret), secret_hint=mask(secret))
    db.add(row)
    db.flush()
    return row


async def build(reset: bool) -> None:
    init_db()
    demo = f"{settings.public_api_url}/demo"
    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.email == EMAIL)).scalar_one_or_none()
        if existing and not reset:
            print("Demo account exists. Re-run with --reset to rebuild it.")
            return
        if existing:
            db.delete(existing)
            db.commit()
        user = User(email=EMAIL, name="Demo Studio", password_hash=hash_password(PASSWORD), is_demo=True)
        db.add(user)
        db.flush()
        crm = _credential(db, user, "Demo CRM — bearer token", "bearer", demo_api.SOURCE_TOKEN)
        marketing = _credential(db, user, "Demo marketing API key", "api_key", demo_api.DESTINATION_KEY, "X-API-Key")
        signing = _credential(db, user, "Webhook signing secret", "bearer", "whsec_demo_4b1f7a9c2e")

        customers = Integration(
            owner_id=user.id, name="CRM customers → Marketing platform",
            description="Nightly-style sync of CRM contacts into the email marketing tool.",
            source_type="rest",
            source_config={"url": f"{demo}/source/customers", "method": "GET", "headers": {}, "params": {"per_page": "20"},
                           "records_path": "data", "pagination": "page", "page_param": "page", "max_pages": 10},
            source_credential_id=crm.id,
            destination_type="rest",
            destination_config={"url": f"{demo}/destination/customers", "method": "POST", "headers": {}},
            destination_credential_id=marketing.id,
            mapping=[
                {"source": "first_name", "target": "name", "transform": "trim", "argument": None, "required": True, "default": None},
                {"source": "mail", "target": "email", "transform": "lowercase", "argument": None, "required": False, "default": None},
                {"source": "age", "target": "age", "transform": "to_number", "argument": None, "required": False, "default": None},
                {"source": "newsletter", "target": "subscribed", "transform": "to_boolean", "argument": None, "required": False, "default": None},
                {"source": "address.city", "target": "location.city", "transform": "none", "argument": None, "required": False, "default": None},
                {"source": "plan", "target": "segment", "transform": "prefix", "argument": "plan-", "required": False, "default": None},
                {"source": "id", "target": "external_id", "transform": "to_string", "argument": None, "required": True, "default": None},
            ],
            schedule="hourly",
        )
        orders = Integration(
            owner_id=user.id, name="Shop orders → Accounting",
            description="Paid and pending orders pushed to the bookkeeping API with typed amounts.",
            source_type="rest",
            source_config={"url": f"{demo}/source/orders", "method": "GET", "headers": {}, "params": {},
                           "records_path": "results.items", "pagination": "none", "page_param": "page", "max_pages": 10},
            destination_type="rest",
            destination_config={"url": f"{demo}/destination/orders", "method": "POST", "headers": {"X-Source": "databridge"}},
            mapping=[
                {"source": "order.number", "target": "order_id", "transform": "none", "argument": None, "required": True, "default": None},
                {"source": "amount", "target": "total", "transform": "to_number", "argument": None, "required": True, "default": None},
                {"source": "is_paid", "target": "paid", "transform": "to_boolean", "argument": None, "required": False, "default": "no"},
                {"source": "customer.email", "target": "customer.email", "transform": "none", "argument": None, "required": False, "default": None},
                {"source": "customer.country_code", "target": "customer.country", "transform": "lowercase", "argument": None, "required": False, "default": None},
                {"source": "items", "target": "line_items", "transform": "to_number", "argument": None, "required": False, "default": None},
            ],
            schedule="daily",
        )
        token = generate_webhook_token()
        forms = Integration(
            owner_id=user.id, name="Website form → Slack-style webhook",
            description="Contact-form submissions forwarded as signed webhooks.",
            source_type="webhook", source_config={"records_path": ""},
            destination_type="webhook",
            destination_config={"url": f"{demo}/destination/webhook", "headers": {}},
            destination_credential_id=signing.id,
            mapping=[
                {"source": "name", "target": "contact.name", "transform": "trim", "argument": None, "required": True, "default": None},
                {"source": "email", "target": "contact.email", "transform": "lowercase", "argument": None, "required": True, "default": None},
                {"source": "message", "target": "text", "transform": "none", "argument": None, "required": False, "default": None},
                {"source": "source", "target": "channel", "transform": "prefix", "argument": "web-", "required": False, "default": "form"},
            ],
            schedule="manual", webhook_token_encrypted=encrypt_secret(token), webhook_token_hash=hash_token(token),
        )
        db.add_all([customers, orders, forms])
        db.commit()
        ids = customers.id, orders.id, forms.id

    # Execute real runs through the demo APIs, in-process.
    from app.main import app

    outbound.set_transport(httpx.ASGITransport(app=app))
    history: list[tuple[int, float]] = []  # (run id, hours ago)
    plan = [(ids[0], h) for h in (150, 126, 102, 78, 54, 30, 6, 1)] + [(ids[1], h) for h in (140, 116, 92, 44, 20)]
    outage = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "Service unavailable"}))
    for integration_id, hours_ago in plan:
        demo_api.reset()
        # One run hits an outage at the source, so the history has a failed run too.
        outbound.set_transport(outage if (integration_id, hours_ago) == (ids[1], 92) else httpx.ASGITransport(app=app))
        with SessionLocal() as db:
            run = runner.start_run(db, db.get(Integration, integration_id), "schedule")
        await runner.execute(run.id)
        history.append((run.id, hours_ago))
    outbound.set_transport(httpx.ASGITransport(app=app))
    # Two webhook deliveries.
    for hours_ago, payload in ((70, {"name": " Ana Costa ", "email": "ANA@EXAMPLE.COM", "message": "Pricing for 20 seats?", "source": "pricing"}),
                               (3, [{"name": "Kofi Mensah", "email": "kofi@example.com", "message": "Demo request"},
                                    {"name": "", "email": "no-name@example.com", "message": "…"}])):
        with SessionLocal() as db:
            run = runner.start_run(db, db.get(Integration, ids[2]), "webhook")
        await runner.execute(run.id, inbound=payload)
        history.append((run.id, hours_ago))
    outbound.set_transport(None)
    demo_api.reset()

    now = utcnow()
    with SessionLocal() as db:
        for run_id, hours_ago in history:
            run = db.get(SyncRun, run_id)
            duration = run.finished_at - run.started_at
            started = now - timedelta(hours=hours_ago)
            db.execute(update(SyncRun).where(SyncRun.id == run_id).values(started_at=started, finished_at=started + duration))
        for integration_id in ids:
            integration = db.get(Integration, integration_id)
            last = db.execute(select(SyncRun).where(SyncRun.integration_id == integration_id)
                              .order_by(SyncRun.started_at.desc())).scalars().first()
            integration.last_run_at = last.finished_at if last else None
            integration.last_run_status = last.status if last else None
            integration.next_run_at = next_run_after(integration.schedule, now + timedelta(minutes=25)) if integration.schedule != "manual" else None
        db.commit()
    print("Demo workspace ready.")
    print(f"  {EMAIL} / {PASSWORD}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true")
    asyncio.run(build(parser.parse_args().reset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
