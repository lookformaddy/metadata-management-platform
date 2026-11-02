"""Optional FastAPI service layer over the stdlib core.

FastAPI is deliberately an optional dependency: the catalog, glossary,
lineage, and access logic all work without it. ``create_app`` raises a
clear RuntimeError when FastAPI is not installed, and the service test
skips in that case.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
except ImportError:  # pragma: no cover - exercised by the skip in tests
    FastAPI = None  # type: ignore[assignment,misc]
    HTTPException = None  # type: ignore[assignment,misc]


def create_app(catalog: Any, glossary: Any, lineage: Any, access: Any) -> Any:
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Install it (pip install -r requirements.txt) "
            "to run the service layer."
        )
    app = FastAPI(title="Metadata Management Platform")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/assets")
    def list_assets() -> list[dict]:
        return [catalog.to_dict(a) for a in catalog.all()]

    @app.get("/assets/{asset_id}")
    def get_asset(asset_id: str) -> dict:
        asset = catalog.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="unknown asset")
        return catalog.to_dict(asset)

    @app.get("/search")
    def search(
        q: str = "",
        owner: str | None = None,
        tag: str | None = None,
    ) -> list[dict]:
        tags = [tag] if tag else None
        return [catalog.to_dict(a) for a in catalog.search(q, tags=tags, owner=owner)]

    @app.get("/lineage/{asset_id}/impact")
    def impact(asset_id: str) -> dict:
        return {"asset_id": asset_id, "downstream": lineage.impact_analysis(asset_id)}

    @app.post("/access-requests")
    def create_access_request(body: dict) -> dict:
        request = access.request_access(
            body["asset_id"], body["requester"], body.get("justification", "")
        )
        return {
            "request_id": request.request_id,
            "asset_id": request.asset_id,
            "status": request.status.value,
        }

    return app
