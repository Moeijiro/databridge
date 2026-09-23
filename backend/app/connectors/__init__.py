"""Connectors: where records come from and where they go.

Adding a connector means implementing ``SourceConnector`` or
``DestinationConnector`` from ``base.py`` and registering it below. The runner,
the API and the UI work from the registry.
"""

from app.connectors.base import DestinationConnector, FetchResult, SendResult, SourceConnector, TestResult
from app.connectors.rest import RestDestination, RestSource
from app.connectors.webhook import WebhookDestination, WebhookSource

SOURCES: dict[str, SourceConnector] = {"rest": RestSource(), "webhook": WebhookSource()}
DESTINATIONS: dict[str, DestinationConnector] = {"rest": RestDestination(), "webhook": WebhookDestination()}

__all__ = ["DESTINATIONS", "SOURCES", "DestinationConnector", "FetchResult", "SendResult", "SourceConnector", "TestResult"]
