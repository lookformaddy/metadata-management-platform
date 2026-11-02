import pytest

from metadata_platform.access import AccessManager
from metadata_platform.audit import AuditLog
from metadata_platform.catalog import Catalog
from metadata_platform.glossary import Glossary
from metadata_platform.lineage import CycleError, LineageGraph
from metadata_platform.models import (
    Asset,
    AssetType,
    Classification,
    ProposalStatus,
)


def _catalog_with_asset():
    catalog = Catalog()
    catalog.register(Asset(asset_id="tbl-orders", name="orders",
                           asset_type=AssetType.TABLE, owner="team-a",
                           steward="steward-a"))
    return catalog


def test_glossary_term_approval_workflow():
    glossary = Glossary()
    term = glossary.propose_term("t1", "Revenue", "Income.", proposer="ana")
    assert term.status == ProposalStatus.PROPOSED
    glossary.decide_term("t1", approver="priya", approve=True)
    assert glossary.get_term("t1").status == ProposalStatus.APPROVED
    with pytest.raises(ValueError):
        glossary.decide_term("t1", approver="priya", approve=False)
    assert glossary.audit.verify()


def test_glossary_rejection_and_change_proposal_applies_only_on_approval():
    catalog = _catalog_with_asset()
    glossary = Glossary(catalog=catalog)
    glossary.propose_term("t1", "Revenue", "Old definition.", proposer="ana")
    glossary.decide_term("t1", approver="priya", approve=False, reason="vague")
    assert glossary.get_term("t1").status == ProposalStatus.REJECTED

    rejected = glossary.propose_change("glossary_term", "t1", "definition",
                                       "New definition.", proposer="ana")
    glossary.decide_change(rejected.proposal_id, decided_by="priya",
                           approve=False)
    assert glossary.get_term("t1").definition == "Old definition."

    approved = glossary.propose_change("asset", "tbl-orders", "description",
                                       "Updated description.", proposer="ana")
    glossary.decide_change(approved.proposal_id, decided_by="priya",
                           approve=True)
    assert catalog.require("tbl-orders").description == "Updated description."
    assert glossary.audit.verify()


def test_glossary_link_requires_known_asset():
    catalog = _catalog_with_asset()
    glossary = Glossary(catalog=catalog)
    glossary.propose_term("t1", "Revenue", "Income.", proposer="ana")
    with pytest.raises(KeyError):
        glossary.link_asset("t1", "tbl-missing", actor="ana")
    glossary.link_asset("t1", "tbl-orders", actor="ana")
    assert glossary.get_term("t1").linked_asset_ids == ["tbl-orders"]


def test_lineage_impact_and_cycle_detection():
    graph = LineageGraph()
    graph.add_link("a", "b")
    graph.add_link("b", "c")
    graph.add_link("a", "d")
    assert graph.impact_analysis("a") == ["b", "c", "d"]
    assert graph.impact_analysis("c") == []
    assert graph.transitive_upstream("c") == {"a", "b"}
    assert graph.detect_cycle() is None
    with pytest.raises(CycleError):
        graph.add_link("c", "a")
    with pytest.raises(CycleError):
        graph.add_link("b", "b")


def test_access_request_approve_deny_and_expiry():
    catalog = _catalog_with_asset()
    audit = AuditLog()
    access = AccessManager(catalog=catalog, audit=audit)
    req = access.request_access("tbl-orders", "jordan", "analysis")
    grant = access.approve(req.request_id, decided_by="priya", grant_days=7)
    assert grant.is_active()
    assert access.active_grants()[0].grant_id == grant.grant_id

    denied = access.request_access("tbl-orders", "casey", "curiosity")
    with pytest.raises(ValueError):
        access.deny(denied.request_id, decided_by="priya", reason="  ")
    access.deny(denied.request_id, decided_by="priya", reason="insufficient need")
    assert denied.status.value == "denied"
    with pytest.raises(ValueError):
        access.approve(denied.request_id, decided_by="priya")
    assert audit.verify()


def test_audit_chain_detects_tampering():
    audit = AuditLog()
    audit.append("ana", "access_requested", "acc-0001")
    audit.append("priya", "access_approved", "acc-0001")
    assert audit.verify()
    # Entries are frozen dataclasses, so tampering means replacing one entry.
    tampered = audit.entries()
    import dataclasses
    audit._entries[0] = dataclasses.replace(tampered[0], details="forged")
    assert not audit.verify()
