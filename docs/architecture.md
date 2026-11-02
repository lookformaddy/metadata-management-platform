# Architecture

## Components

```
                ┌──────────────┐
                │  CLI / demo  │
                └──────┬───────┘
                       │  (optional FastAPI adapter in service.py)
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Catalog │   │ Glossary │   │ Lineage  │   │ Access   │
   │         │   │          │   │ Graph    │   │ Manager  │
   └────┬────┘   └────┬─────┘   └──────────┘   └────┬─────┘
        │             │                              │
        └─────────────┴──────────┬───────────────────┘
                                 ▼
                          ┌────────────┐
                          │ AuditLog   │  hash-chained, append-only
                          │ (SHA-256)  │
                          └────────────┘
```

All components are plain Python objects over the standard library.
`Catalog`, `Glossary`, and `AccessManager` share one `AuditLog`
instance when constructed together (as `seed.build_platform()` does),
so a single verifiable trail covers glossary decisions and access
decisions alike.

## Data model

- **Asset** — identity (`asset_id`), human name, type
  (`table | dashboard | topic | ml_model`), owner, steward, tags,
  classification, description, ordered schema versions, freshness
  fields (`last_updated`, `staleness_threshold_days`), and an optional
  quality score in `[0, 1]`. Schema versions are append-only: adding a
  version never rewrites history.
- **GlossaryTerm** — name, definition, lifecycle status, proposer,
  decider, and linked asset ids. Links are validated against the
  catalog when one is attached, so terms cannot point at phantom assets.
- **ChangeProposal** — a proposed new value for one field of one
  target (term definition or asset description). Decisions are final;
  approval applies the value, rejection leaves the target untouched.
- **AccessRequest / Grant** — a request carries justification and a
  terminal status; approval mints a `Grant` with an expiry timestamp.
  Grants are checked with `is_active(at)`, so expiry is evaluated at
  read time rather than by a background sweeper.
- **AuditEntry** — `index, timestamp, actor, action, details, prev_hash,
  entry_hash`, where `entry_hash = SHA-256(canonical JSON of the
  entry)`. Verification recomputes the whole chain.

## Search ranking

Score tiers (additive, but weighted so tiers do not overlap for
single-field matches):

| Match | Points |
|---|---|
| Query equals the asset name | 200 |
| Query is a substring of the name | 100 |
| Query matches a tag | 10 |
| Query matches the description | 1 |

Results sort by score descending, then name, then asset id. Filters
(tags, owner, classification) are ANDed before ranking, so a filter can
only narrow, never reorder by itself.

## Lineage and impact

Edges point upstream → downstream. Impact analysis is a breadth-first
walk of the downstream adjacency, returning the transitive closure
sorted. Cycle prevention uses the same walk: adding `u → d` is refused
if `d` already reaches `u`. `detect_cycle()` (iterative DFS with a
grey/black coloring) exists for graphs assembled outside `add_link`,
e.g. bulk imports, where the invariant may not hold.

## Audit log: what it does and does not promise

The hash chain makes any edit to an existing entry detectable, because
every later entry's `prev_hash` and hash no longer recompute. It does
*not* prevent an actor with write access to the log object from
rewriting the entire chain from scratch — that requires an external,
append-only store (WORM storage, a ledger service, or a signed
transparency log), which is the correct production hardening and is
deliberately out of scope here.

## Extension points

1. **Persistence** — add a repository behind `Catalog`/`Glossary`
   (SQLite for local use, Postgres for production); the domain methods
   do not assume in-memory storage.
2. **Column-level lineage** — extend edges from asset ids to
   `(asset_id, field)` pairs; impact analysis then walks field edges
   with asset-level fallback.
3. **Policy enforcement** — connect classification + grants to the
   query layer so `RESTRICTED` assets are actually unreadable without
   an active grant, rather than merely labeled.
4. **Event-driven freshness** — replace `last_updated` polling with
   ingestion events that update freshness and quality scores on write.
5. **Full-text search** — swap the substring scorer for a tokenized
   index (e.g. SQLite FTS or an external search service) once the
   catalog outgrows substring matching, keeping the same filter API.
