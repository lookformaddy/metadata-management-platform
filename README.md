# Metadata Management Platform

An enterprise metadata catalog: one registry where data teams discover
assets, agree on what terms mean, see how fresh and trustworthy an asset
is, trace what depends on it, and request access — all with an auditable
trail. Built as clean-room, original code over synthetic data only.

## The enterprise problem

As a data estate grows, the same questions recur and nobody can answer
them reliably: *What tables and dashboards exist? Who owns them? Is this
data fresh enough to use? What breaks if I change this table? Who
approved that definition, and who got access to the restricted table?*

This project answers those questions with a small, composable core:

- **Metadata catalog** — registry for tables, dashboards, topics, and ML
  models, each with owner/steward, tags, classification
  (`PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED`), description, and
  schema/version history.
- **Ranked search** — keyword + tag + owner + classification filters,
  with deterministic ranking: name match > tag match > description
  match (ties break by name, then id, so results are stable).
- **Business glossary** — terms linked to assets, with an approval
  workflow for term and asset changes (`proposed → approved/rejected`),
  every decision written to the audit log.
- **Freshness & quality signals** — last-updated timestamps, per-asset
  staleness thresholds, quality scores, and a staleness report
  (never-updated assets sort as most stale).
- **Lineage-lite** — upstream/downstream links with transitive impact
  analysis ("what breaks if this changes?") and cycle detection;
  links that would create a cycle are refused.
- **Access requests** — request → approve/deny with a required denial
  reason, time-boxed grants, revocation, and an append-only,
  hash-chained audit log (chain verification detects tampering).

## Architecture overview

```
src/metadata_platform/
├── models.py    # Typed dataclasses: Asset, GlossaryTerm, ChangeProposal,
│                #   AccessRequest, Grant, SchemaVersion, enums
├── catalog.py   # Asset registry, ranked search, staleness report
├── glossary.py  # Glossary terms + audited change-approval workflow
├── lineage.py   # Lineage graph, impact analysis, cycle detection
├── access.py    # Access requests, expiring grants, revocation
├── audit.py     # Append-only hash-chained audit log
├── seed.py      # Synthetic demo data (invented names/schemas only)
├── service.py   # Optional FastAPI layer over the core (no FastAPI needed
│                #   for the core, CLI, or tests)
└── cli.py       # CLI: search / staleness / impact / list
demo.py          # Seeds synthetic assets and exercises every subsystem
```

The core is standard-library Python only, with no database and no
framework dependency, so it can be embedded in another service, wrapped
in a different API layer, or backed by persistent storage later without
rewriting the domain logic. The FastAPI layer is a thin adapter over
exactly the same objects the CLI and tests use.

See [docs/architecture.md](docs/architecture.md) for design decisions,
the ranking scheme, and the trade-offs.

## How to run

Requires Python 3.10+.

```bash
# Demo: seeds synthetic assets, runs search, glossary approval,
# impact analysis, an access request, and the staleness report.
python demo.py

# CLI (from the project root)
PYTHONPATH=src python -m metadata_platform.cli search sales
PYTHONPATH=src python -m metadata_platform.cli staleness
PYTHONPATH=src python -m metadata_platform.cli impact tbl-orders
PYTHONPATH=src python -m metadata_platform.cli list

# Tests (no install step needed; conftest puts src/ on sys.path)
pytest

# Optional service layer (installs FastAPI + Uvicorn)
pip install -r requirements.txt
# then build an app via create_app (see "Service note" below) and serve it
```

> **Service note:** `service.py` exposes `create_app(catalog, glossary,
> lineage, access)` rather than a module-level `app`, because the app
> is built over a seeded platform instance. To serve it, create a small
> entrypoint that builds the platform with `seed.build_platform()` and
> passes the pieces to `create_app`. The service test in
> `tests/test_service.py` shows the pattern and skips cleanly when
> FastAPI is not installed.

## Key design decisions and trade-offs

- **In-memory, stdlib core first.** Persistence is the easiest thing to
  add later and the hardest to get right early; keeping the core
  dependency-free makes the domain logic testable and portable, at the
  cost of no durability across restarts (a repository adapter is the
  natural next step, behind the same `Catalog`/`Glossary` interfaces).
- **Deterministic ranking over relevance tuning.** Match tiers are
  weighted so a name match always outranks a tag match, which always
  outranks a description match, with deterministic tie-breaking. This
  sacrifices BM25-style relevance for predictability — the right trade
  for a catalog where users must be able to explain why result A beat
  result B.
- **Approval workflow, not direct edits.** Approved definitions and
  descriptions change only through a decided `ChangeProposal`. This is
  deliberately stricter than a wiki-style edit: in a governed catalog,
  *who approved this wording, and when* matters as much as the wording.
- **Refuse cycles at write time.** Lineage links that would close a
  cycle are rejected instead of merely flagged, because a cyclic
  lineage graph makes impact analysis meaningless. `detect_cycle()`
  still exists to verify graphs built by bulk import.
- **Hash-chained audit log for tamper evidence, not tamper proof.**
  The chain detects edits to history; preventing them would require an
  external append-only store, which is out of scope for this core.
- **Classification is a label, not enforcement.** The catalog records
  `RESTRICTED` etc., and the access workflow gates grants, but this
  project does not enforce row/column-level access — that belongs in
  the query engine, not the catalog.

## What it demonstrates

Data-platform engineering judgment: a governed asset registry with
search ranking, a glossary approval workflow, freshness/quality
observability, lineage impact analysis, and audited access control —
the building blocks of a data mesh / data governance platform,
implemented as clean, typed, tested Python.

## CI

The GitHub Actions workflow lives at `docs/github-actions-ci.yml`. It is
not placed under `.github/workflows/` because the GitHub App used to
publish this repository lacks the Workflows permission. **To activate
CI, move it to `.github/workflows/ci.yml`** (one file move, no edits).

## License

MIT — see `LICENSE` if present in the repository root. All code is
original; all demo data is synthetic.
