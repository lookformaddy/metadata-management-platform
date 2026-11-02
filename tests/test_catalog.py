from datetime import datetime, timedelta

import pytest

from metadata_platform.catalog import Catalog
from metadata_platform.models import (
    Asset,
    AssetType,
    Classification,
    SchemaField,
)


def make_asset(asset_id="tbl-a", name="orders", **kwargs):
    defaults = dict(
        asset_type=AssetType.TABLE,
        owner="team-a",
        steward="steward-a",
        tags=("sales",),
        classification=Classification.INTERNAL,
        description="order records",
    )
    defaults.update(kwargs)
    return Asset(asset_id=asset_id, name=name, **defaults)


def test_register_and_duplicate_rejected():
    catalog = Catalog()
    catalog.register(make_asset())
    with pytest.raises(ValueError):
        catalog.register(make_asset())


def test_search_ranking_name_beats_tag_beats_description():
    catalog = Catalog()
    catalog.register(make_asset("a1", "sales-report", tags=("other",),
                                description="unrelated"))
    catalog.register(make_asset("a2", "other-report", tags=("sales",),
                                description="unrelated"))
    catalog.register(make_asset("a3", "other-report-2", tags=("other",),
                                description="sales figures here"))
    names = [a.asset_id for a in catalog.search("sales")]
    assert names == ["a1", "a2", "a3"]


def test_search_filters_are_anded():
    catalog = Catalog()
    catalog.register(make_asset("a1", "orders", owner="team-a",
                                classification=Classification.PUBLIC))
    catalog.register(make_asset("a2", "orders-archive", owner="team-b",
                                classification=Classification.PUBLIC))
    assert [a.asset_id for a in catalog.search("orders", owner="team-a")] == ["a1"]
    assert catalog.search("orders", classification=Classification.RESTRICTED) == []
    assert [a.asset_id for a in catalog.search(tags=["sales"])] == ["a1", "a2"]


def test_search_is_deterministic_on_ties():
    catalog = Catalog()
    catalog.register(make_asset("b-id", "zeta"))
    catalog.register(make_asset("a-id", "alpha"))
    # Empty query: name-sorted, regardless of insertion order.
    assert [a.asset_id for a in catalog.search()] == ["a-id", "b-id"]


def test_schema_versioning_increments():
    asset = make_asset()
    v1 = asset.add_schema_version([SchemaField("id", "string", nullable=False)])
    v2 = asset.add_schema_version([SchemaField("id", "string", nullable=False),
                                   SchemaField("total", "decimal")])
    assert (v1.version, v2.version) == (1, 2)
    assert asset.current_schema() is v2
    assert asset.current_schema().field_names() == ["id", "total"]


def test_staleness_report_flags_and_orders():
    now = datetime.utcnow()
    catalog = Catalog()
    catalog.register(make_asset("fresh", "fresh", last_updated=now,
                                staleness_threshold_days=7, quality_score=0.9))
    catalog.register(make_asset("stale", "stale",
                                last_updated=now - timedelta(days=30),
                                staleness_threshold_days=7, quality_score=0.5))
    catalog.register(make_asset("never", "never", last_updated=None,
                                staleness_threshold_days=7))
    rows = catalog.staleness_report(at=now)
    assert [r["asset_id"] for r in rows] == ["never", "stale", "fresh"]
    assert [r["stale"] for r in rows] == [True, True, False]
