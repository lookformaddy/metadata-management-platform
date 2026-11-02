"""Synthetic demo data. All names, owners, and schemas are invented.

Used by demo.py and the CLI; nothing here represents a real company,
dataset, or employee.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .access import AccessManager
from .audit import AuditLog
from .catalog import Catalog
from .glossary import Glossary
from .lineage import LineageGraph
from .models import Asset, AssetType, Classification, SchemaField


def build_platform(now: datetime | None = None):
    """Return (catalog, glossary, lineage, access, audit) seeded synthetically."""
    ref = now or datetime.utcnow()
    audit = AuditLog()
    catalog = Catalog()
    glossary = Glossary(catalog=catalog, audit=audit)
    lineage = LineageGraph()
    access = AccessManager(catalog=catalog, audit=audit)

    def days_ago(n: int) -> datetime:
        return ref - timedelta(days=n)

    assets = [
        Asset(
            asset_id="tbl-orders",
            name="orders",
            asset_type=AssetType.TABLE,
            owner="data-platform-team",
            steward="priya-sharma",
            tags=("sales", "transactions", "gold"),
            classification=Classification.CONFIDENTIAL,
            description="Curated order transactions, one row per order line.",
            last_updated=days_ago(1),
            staleness_threshold_days=2,
            quality_score=0.97,
        ),
        Asset(
            asset_id="tbl-customers",
            name="customers",
            asset_type=AssetType.TABLE,
            owner="data-platform-team",
            steward="priya-sharma",
            tags=("crm", "pii", "gold"),
            classification=Classification.RESTRICTED,
            description="Customer master records with consent flags.",
            last_updated=days_ago(12),
            staleness_threshold_days=7,
            quality_score=0.88,
        ),
        Asset(
            asset_id="topic-order-events",
            name="order-events",
            asset_type=AssetType.TOPIC,
            owner="streaming-team",
            steward="leo-chen",
            tags=("sales", "events", "bronze"),
            classification=Classification.INTERNAL,
            description="Raw order lifecycle events from the storefront.",
            last_updated=days_ago(0),
            staleness_threshold_days=1,
            quality_score=0.99,
        ),
        Asset(
            asset_id="dash-revenue",
            name="revenue-overview",
            asset_type=AssetType.DASHBOARD,
            owner="analytics-team",
            steward="ana-garcia",
            tags=("sales", "finance", "reporting"),
            classification=Classification.INTERNAL,
            description="Weekly revenue overview for regional managers.",
            last_updated=days_ago(3),
            staleness_threshold_days=7,
            quality_score=0.91,
        ),
        Asset(
            asset_id="model-churn",
            name="churn-predictor",
            asset_type=AssetType.ML_MODEL,
            owner="ml-team",
            steward="sam-okafor",
            tags=("churn", "ml", "scoring"),
            classification=Classification.CONFIDENTIAL,
            description="Weekly churn-risk scores for the retention program.",
            last_updated=days_ago(20),
            staleness_threshold_days=14,
            quality_score=0.83,
        ),
    ]
    for asset in assets:
        catalog.register(asset)

    catalog.require("tbl-orders").add_schema_version(
        [
            SchemaField("order_id", "string", nullable=False),
            SchemaField("customer_id", "string", nullable=False),
            SchemaField("order_total", "decimal"),
            SchemaField("ordered_at", "timestamp", nullable=False),
        ],
        change_note="Initial curated schema",
    )
    catalog.require("tbl-customers").add_schema_version(
        [
            SchemaField("customer_id", "string", nullable=False),
            SchemaField("email_hash", "string"),
            SchemaField("consent_marketing", "boolean"),
        ],
        change_note="Initial master schema",
    )

    lineage.add_link("topic-order-events", "tbl-orders")
    lineage.add_link("tbl-orders", "dash-revenue")
    lineage.add_link("tbl-customers", "dash-revenue")
    lineage.add_link("tbl-orders", "model-churn")
    lineage.add_link("tbl-customers", "model-churn")

    return catalog, glossary, lineage, access, audit
