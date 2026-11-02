"""End-to-end demo: seeds synthetic assets and exercises every subsystem.

Run:  python demo.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from metadata_platform.seed import build_platform  # noqa: E402


def main() -> None:
    catalog, glossary, lineage, access, audit = build_platform()

    print("== Ranked search: 'sales' ==")
    for asset in catalog.search("sales"):
        print(f"  {asset.asset_id}  {asset.name}  tags={list(asset.tags)}")

    print("\n== Glossary approval ==")
    term = glossary.propose_term(
        "term-revenue", "Revenue",
        "Recognized income from completed orders.", proposer="ana-garcia",
    )
    glossary.link_asset(term.term_id, "tbl-orders", actor="ana-garcia")
    glossary.decide_term(term.term_id, approver="priya-sharma", approve=True)
    print(f"  term '{term.name}' status: {term.status.value}, "
          f"linked: {term.linked_asset_ids}")

    proposal = glossary.propose_change(
        "asset", "dash-revenue", "description",
        "Weekly revenue overview for regional managers (v2 wording).",
        proposer="ana-garcia",
    )
    glossary.decide_change(proposal.proposal_id, decided_by="priya-sharma",
                           approve=True)
    print(f"  change {proposal.proposal_id}: {proposal.status.value}; "
          f"new description: {catalog.require('dash-revenue').description!r}")

    print("\n== Impact analysis: change tbl-orders ==")
    print(f"  downstream: {lineage.impact_analysis('tbl-orders')}")

    print("\n== Access request ==")
    request = access.request_access(
        "tbl-customers", "jordan-lee", "Need sample rows for a retention analysis."
    )
    grant = access.approve(request.request_id, decided_by="priya-sharma",
                           grant_days=14)
    print(f"  request {request.request_id}: {request.status.value}; "
          f"grant {grant.grant_id} active={grant.is_active()}, "
          f"expires={grant.expires_at.date()}")

    print("\n== Staleness report ==")
    for row in catalog.staleness_report():
        print(f"  {row['asset_id']}: stale={row['stale']}, "
              f"days={row['days_since_update']}, quality={row['quality_score']}")

    print(f"\n== Audit log: {len(audit.entries())} entries, "
          f"chain valid: {audit.verify()} ==")


if __name__ == "__main__":
    main()
