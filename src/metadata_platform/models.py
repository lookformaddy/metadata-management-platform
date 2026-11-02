"""Core domain models for the metadata management platform.

All models are plain, typed dataclasses over the standard library. Nothing
here depends on a web framework or a database, so the catalog, glossary,
lineage, and access logic can be embedded in another service or tested in
isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AssetType(str, Enum):
    TABLE = "table"
    DASHBOARD = "dashboard"
    TOPIC = "topic"
    ML_MODEL = "ml_model"


class Classification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class SchemaField:
    """One column/field of an asset schema version."""

    name: str
    type: str
    nullable: bool = True
    description: str = ""


@dataclass
class SchemaVersion:
    version: int
    fields: tuple[SchemaField, ...]
    change_note: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]


@dataclass
class Asset:
    """A registered data asset: table, dashboard, topic, or ML model."""

    asset_id: str
    name: str
    asset_type: AssetType
    owner: str
    steward: str
    tags: tuple[str, ...] = ()
    classification: Classification = Classification.INTERNAL
    description: str = ""
    schema_versions: list[SchemaVersion] = field(default_factory=list)
    last_updated: datetime | None = None
    staleness_threshold_days: int = 7
    quality_score: float | None = None  # 0.0 - 1.0, None = not yet scored
    created_at: datetime = field(default_factory=datetime.utcnow)

    def current_schema(self) -> SchemaVersion | None:
        return self.schema_versions[-1] if self.schema_versions else None

    def add_schema_version(
        self, fields: list[SchemaField], change_note: str = ""
    ) -> SchemaVersion:
        next_version = (self.schema_versions[-1].version + 1) if self.schema_versions else 1
        version = SchemaVersion(
            version=next_version, fields=tuple(fields), change_note=change_note
        )
        self.schema_versions.append(version)
        return version

    def days_since_update(self, at: datetime | None = None) -> float | None:
        if self.last_updated is None:
            return None
        ref = at or datetime.utcnow()
        return (ref - self.last_updated).total_seconds() / 86400.0

    def is_stale(self, at: datetime | None = None) -> bool:
        days = self.days_since_update(at)
        if days is None:
            return True  # never updated counts as stale
        return days > self.staleness_threshold_days


@dataclass
class GlossaryTerm:
    term_id: str
    name: str
    definition: str
    status: ProposalStatus = ProposalStatus.PROPOSED
    proposer: str = ""
    approver: str = ""
    decision_reason: str = ""
    linked_asset_ids: list[str] = field(default_factory=list)


@dataclass
class ChangeProposal:
    """A proposed change to a glossary term definition or an asset description.

    Only ``proposed`` proposals can be decided, and a decision is final:
    approving applies the new value, rejecting leaves the target untouched.
    """

    proposal_id: str
    target_kind: str  # "glossary_term" or "asset"
    target_id: str
    field_name: str
    new_value: str
    proposer: str
    status: ProposalStatus = ProposalStatus.PROPOSED
    decided_by: str = ""
    decision_reason: str = ""


@dataclass
class AccessRequest:
    request_id: str
    asset_id: str
    requester: str
    justification: str
    status: AccessStatus = AccessStatus.REQUESTED
    decided_by: str = ""
    decision_reason: str = ""
    grant_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Grant:
    grant_id: str
    request_id: str
    asset_id: str
    grantee: str
    granted_by: str
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    revoked: bool = False

    def is_active(self, at: datetime | None = None) -> bool:
        if self.revoked:
            return False
        if self.expires_at is None:
            return True
        return (at or datetime.utcnow()) < self.expires_at


def expiry_after(days: int, at: datetime | None = None) -> datetime:
    return (at or datetime.utcnow()) + timedelta(days=days)
