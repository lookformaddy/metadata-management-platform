"""Business glossary with an audited approval workflow.

Terms start as proposals. A steward approves or rejects them; a term's
definition (and an asset's description) can only change through a
ChangeProposal that is approved, and every decision is written to the
audit log. Direct mutation of an approved definition outside this path
is deliberately not offered by this module.
"""

from __future__ import annotations

from .audit import AuditLog
from .catalog import Catalog
from .models import ChangeProposal, GlossaryTerm, ProposalStatus


class Glossary:
    def __init__(self, catalog: Catalog | None = None, audit: AuditLog | None = None):
        self.catalog = catalog
        self.audit = audit or AuditLog()
        self._terms: dict[str, GlossaryTerm] = {}
        self._proposals: dict[str, ChangeProposal] = {}
        self._next_proposal = 1

    # -- terms ---------------------------------------------------------
    def propose_term(
        self, term_id: str, name: str, definition: str, proposer: str
    ) -> GlossaryTerm:
        if term_id in self._terms:
            raise ValueError(f"term already exists: {term_id}")
        term = GlossaryTerm(
            term_id=term_id,
            name=name,
            definition=definition,
            status=ProposalStatus.PROPOSED,
            proposer=proposer,
        )
        self._terms[term_id] = term
        self.audit.append(proposer, "glossary_term_proposed", term_id)
        return term

    def decide_term(
        self,
        term_id: str,
        approver: str,
        approve: bool,
        reason: str = "",
    ) -> GlossaryTerm:
        term = self._terms.get(term_id)
        if term is None:
            raise KeyError(f"unknown term: {term_id}")
        if term.status != ProposalStatus.PROPOSED:
            raise ValueError(f"term {term_id} already decided: {term.status.value}")
        term.status = ProposalStatus.APPROVED if approve else ProposalStatus.REJECTED
        term.approver = approver
        term.decision_reason = reason
        self.audit.append(
            approver,
            "glossary_term_approved" if approve else "glossary_term_rejected",
            term_id,
        )
        return term

    def link_asset(self, term_id: str, asset_id: str, actor: str) -> GlossaryTerm:
        term = self._terms.get(term_id)
        if term is None:
            raise KeyError(f"unknown term: {term_id}")
        if self.catalog is not None:
            self.catalog.require(asset_id)  # refuse dangling links
        if asset_id not in term.linked_asset_ids:
            term.linked_asset_ids.append(asset_id)
            self.audit.append(actor, "glossary_term_linked", f"{term_id}->{asset_id}")
        return term

    def get_term(self, term_id: str) -> GlossaryTerm | None:
        return self._terms.get(term_id)

    def approved_terms(self) -> list[GlossaryTerm]:
        return sorted(
            (t for t in self._terms.values() if t.status == ProposalStatus.APPROVED),
            key=lambda t: t.name,
        )

    # -- change proposals ----------------------------------------------
    def propose_change(
        self,
        target_kind: str,
        target_id: str,
        field_name: str,
        new_value: str,
        proposer: str,
    ) -> ChangeProposal:
        if target_kind not in ("glossary_term", "asset"):
            raise ValueError(f"unsupported target kind: {target_kind}")
        if target_kind == "glossary_term" and target_id not in self._terms:
            raise KeyError(f"unknown term: {target_id}")
        if target_kind == "asset" and self.catalog is not None:
            self.catalog.require(target_id)
        proposal_id = f"chg-{self._next_proposal:04d}"
        self._next_proposal += 1
        proposal = ChangeProposal(
            proposal_id=proposal_id,
            target_kind=target_kind,
            target_id=target_id,
            field_name=field_name,
            new_value=new_value,
            proposer=proposer,
        )
        self._proposals[proposal_id] = proposal
        self.audit.append(proposer, "change_proposed", proposal_id)
        return proposal

    def decide_change(
        self, proposal_id: str, decided_by: str, approve: bool, reason: str = ""
    ) -> ChangeProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"unknown proposal: {proposal_id}")
        if proposal.status != ProposalStatus.PROPOSED:
            raise ValueError(
                f"proposal {proposal_id} already decided: {proposal.status.value}"
            )
        proposal.status = ProposalStatus.APPROVED if approve else ProposalStatus.REJECTED
        proposal.decided_by = decided_by
        proposal.decision_reason = reason
        if approve:
            self._apply(proposal)
        self.audit.append(
            decided_by,
            "change_approved" if approve else "change_rejected",
            proposal_id,
        )
        return proposal

    def _apply(self, proposal: ChangeProposal) -> None:
        if proposal.target_kind == "glossary_term":
            if proposal.field_name != "definition":
                raise ValueError(f"cannot change term field: {proposal.field_name}")
            self._terms[proposal.target_id].definition = proposal.new_value
        elif proposal.target_kind == "asset":
            if self.catalog is None:
                raise ValueError("no catalog attached; cannot apply asset change")
            if proposal.field_name != "description":
                raise ValueError(f"cannot change asset field: {proposal.field_name}")
            self.catalog.require(proposal.target_id).description = proposal.new_value
