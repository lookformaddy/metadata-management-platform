"""Access-request workflow with expiring grants and an audited trail.

Flow: request -> approve (creates a time-boxed grant) or deny (with a
reason). Every transition is appended to the shared hash-chained audit
log, so the history of who asked for what, who decided, and why is
verifiable after the fact.
"""

from __future__ import annotations

from datetime import datetime

from .audit import AuditLog
from .catalog import Catalog
from .models import AccessRequest, AccessStatus, Grant, expiry_after


class AccessManager:
    def __init__(self, catalog: Catalog | None = None, audit: AuditLog | None = None):
        self.catalog = catalog
        self.audit = audit or AuditLog()
        self._requests: dict[str, AccessRequest] = {}
        self._grants: dict[str, Grant] = {}
        self._next_request = 1
        self._next_grant = 1

    def request_access(
        self, asset_id: str, requester: str, justification: str
    ) -> AccessRequest:
        if self.catalog is not None:
            self.catalog.require(asset_id)
        request_id = f"acc-{self._next_request:04d}"
        self._next_request += 1
        request = AccessRequest(
            request_id=request_id,
            asset_id=asset_id,
            requester=requester,
            justification=justification,
        )
        self._requests[request_id] = request
        self.audit.append(requester, "access_requested", request_id)
        return request

    def approve(
        self,
        request_id: str,
        decided_by: str,
        grant_days: int = 30,
        reason: str = "",
    ) -> Grant:
        request = self._require_open(request_id)
        grant_id = f"grant-{self._next_grant:04d}"
        self._next_grant += 1
        grant = Grant(
            grant_id=grant_id,
            request_id=request_id,
            asset_id=request.asset_id,
            grantee=request.requester,
            granted_by=decided_by,
            expires_at=expiry_after(grant_days),
        )
        self._grants[grant_id] = grant
        request.status = AccessStatus.APPROVED
        request.decided_by = decided_by
        request.decision_reason = reason
        request.grant_id = grant_id
        self.audit.append(decided_by, "access_approved", request_id)
        return grant

    def deny(self, request_id: str, decided_by: str, reason: str) -> AccessRequest:
        if not reason.strip():
            raise ValueError("denial requires a reason")
        request = self._require_open(request_id)
        request.status = AccessStatus.DENIED
        request.decided_by = decided_by
        request.decision_reason = reason
        self.audit.append(decided_by, "access_denied", request_id)
        return request

    def revoke(self, grant_id: str, revoked_by: str) -> Grant:
        grant = self._grants.get(grant_id)
        if grant is None:
            raise KeyError(f"unknown grant: {grant_id}")
        grant.revoked = True
        self.audit.append(revoked_by, "access_revoked", grant_id)
        return grant

    def active_grants(self, at: datetime | None = None) -> list[Grant]:
        return sorted(
            (g for g in self._grants.values() if g.is_active(at)),
            key=lambda g: g.grant_id,
        )

    def get_request(self, request_id: str) -> AccessRequest | None:
        return self._requests.get(request_id)

    def _require_open(self, request_id: str) -> AccessRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"unknown access request: {request_id}")
        if request.status != AccessStatus.REQUESTED:
            raise ValueError(
                f"request {request_id} already decided: {request.status.value}"
            )
        return request
