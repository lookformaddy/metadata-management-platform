"""Command-line interface for the metadata platform.

Usage examples (run from the project root):

    PYTHONPATH=src python -m metadata_platform.cli search sales
    python -m metadata_platform.cli staleness
    python -m metadata_platform.cli impact tbl-orders
"""

from __future__ import annotations

import argparse
import json
import sys

from .seed import build_platform


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metadata-platform")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="ranked asset search")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--owner")
    search.add_argument("--tag", action="append", dest="tags")
    sub.add_parser("staleness", help="freshness and quality report")
    impact = sub.add_parser("impact", help="transitive downstream impact")
    impact.add_argument("asset_id")
    sub.add_parser("list", help="list all assets")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog, _glossary, lineage, _access, _audit = build_platform()
    if args.command == "search":
        results = catalog.search(args.query, tags=args.tags, owner=args.owner)
        for asset in results:
            print(f"{asset.asset_id}  {asset.name}  [{asset.classification.value}]")
    elif args.command == "staleness":
        print(json.dumps(catalog.staleness_report(), indent=2, default=str))
    elif args.command == "impact":
        for asset_id in lineage.impact_analysis(args.asset_id):
            print(asset_id)
    elif args.command == "list":
        for asset in catalog.all():
            print(f"{asset.asset_id}  {asset.name}  {asset.asset_type.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
