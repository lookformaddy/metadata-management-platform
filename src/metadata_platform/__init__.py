"""Metadata management platform: catalog, glossary, lineage, access control."""

from .access import AccessManager
from .audit import AuditLog
from .catalog import Catalog
from .glossary import Glossary
from .lineage import CycleError, LineageGraph
from .models import (
    AccessRequest,
    AccessStatus,
    Asset,
    AssetType,
    ChangeProposal,
    Classification,
    GlossaryTerm,
    Grant,
    ProposalStatus,
    SchemaField,
    SchemaVersion,
)

__all__ = [
    "AccessManager",
    "AccessRequest",
    "AccessStatus",
    "Asset",
    "AssetType",
    "AuditLog",
    "Catalog",
    "ChangeProposal",
    "Classification",
    "CycleError",
    "Glossary",
    "GlossaryTerm",
    "Grant",
    "LineageGraph",
    "ProposalStatus",
    "SchemaField",
    "SchemaVersion",
]

__version__ = "0.1.0"
