"""Asset registry, ranked search, and freshness/quality reporting."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from .models import Asset, Classification


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _match_score(asset: Asset, query: str) -> int:
    """Deterministic ranking: name match > tag match > description match.

    Scores are additive so an asset matching in several places ranks above
    one matching in one, while the tier weights keep the priority order
    strict for single-field matches (name 100, tag 10, description 1).
    """
    q = _normalize(query)
    if not q:
        return 0
    score = 0
    name = _normalize(asset.name)
    if q == name:
        score += 200
    elif q in name:
        score += 100
    if any(q in _normalize(tag) for tag in asset.tags):
        score += 10
    if q in _normalize(asset.description):
        score += 1
    return score


class Catalog:
    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def register(self, asset: Asset) -> Asset:
        if asset.asset_id in self._assets:
            raise ValueError(f"asset already registered: {asset.asset_id}")
        self._assets[asset.asset_id] = asset
        return asset

    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def require(self, asset_id: str) -> Asset:
        asset = self.get(asset_id)
        if asset is None:
            raise KeyError(f"unknown asset: {asset_id}")
        return asset

    def all(self) -> list[Asset]:
        return sorted(self._assets.values(), key=lambda a: a.name)

    def search(
        self,
        query: str = "",
        tags: list[str] | None = None,
        owner: str | None = None,
        classification: Classification | None = None,
    ) -> list[Asset]:
        """Filter (AND across filters), then rank by match score.

        An empty query with no filters returns every asset, name-sorted.
        Ties in score break deterministically by name, then asset id.
        """
        wanted_tags = {_normalize(t) for t in (tags or [])}
        results: list[tuple[int, Asset]] = []
        for asset in self._assets.values():
            if owner is not None and asset.owner != owner:
                continue
            if classification is not None and asset.classification != classification:
                continue
            if wanted_tags and not wanted_tags.issubset(
                {_normalize(t) for t in asset.tags}
            ):
                continue
            score = _match_score(asset, query)
            if query and score == 0:
                continue
            results.append((score, asset))
        results.sort(key=lambda pair: (-pair[0], pair[1].name, pair[1].asset_id))
        return [asset for _, asset in results]

    def staleness_report(self, at: datetime | None = None) -> list[dict]:
        """One row per asset, stalest first; None days sorts as most stale."""
        ref = at or datetime.utcnow()
        rows = []
        for asset in self._assets.values():
            days = asset.days_since_update(ref)
            rows.append(
                {
                    "asset_id": asset.asset_id,
                    "name": asset.name,
                    "days_since_update": days,
                    "staleness_threshold_days": asset.staleness_threshold_days,
                    "stale": asset.is_stale(ref),
                    "quality_score": asset.quality_score,
                }
            )
        # Rows with days=None come first (never updated = most stale).
        rows.sort(
            key=lambda r: (
                0 if r["days_since_update"] is None else 1,
                -(r["days_since_update"] or 0),
                r["name"],
            )
        )
        return rows

    def to_dict(self, asset: Asset) -> dict:
        data = asdict(asset)
        data["asset_type"] = asset.asset_type.value
        data["classification"] = asset.classification.value
        return data
