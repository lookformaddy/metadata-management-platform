"""Append-only, hash-chained audit log.

Each entry commits to the previous entry's hash, so deleting or altering a
middle entry breaks verification of every entry after it. This is a
tamper-evidence mechanism, not tamper-proofing: it detects edits, it does
not prevent them (that would need an external, append-only store).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class AuditEntry:
    index: int
    timestamp: str
    actor: str
    action: str
    details: str
    prev_hash: str
    entry_hash: str


def _hash_entry(
    index: int, timestamp: str, actor: str, action: str, details: str, prev_hash: str
) -> str:
    payload = json.dumps(
        {
            "index": index,
            "timestamp": timestamp,
            "actor": actor,
            "action": action,
            "details": details,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLog:
    """In-memory append-only log. Entries are immutable once appended."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def append(self, actor: str, action: str, details: str = "") -> AuditEntry:
        prev_hash = self._entries[-1].entry_hash if self._entries else "0" * 64
        timestamp = datetime.utcnow().isoformat()
        index = len(self._entries)
        entry = AuditEntry(
            index=index,
            timestamp=timestamp,
            actor=actor,
            action=action,
            details=details,
            prev_hash=prev_hash,
            entry_hash=_hash_entry(
                index, timestamp, actor, action, details, prev_hash
            ),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def verify(self) -> bool:
        """Return True only if the whole chain recomputes cleanly."""
        prev_hash = "0" * 64
        for i, entry in enumerate(self._entries):
            if entry.index != i or entry.prev_hash != prev_hash:
                return False
            expected = _hash_entry(
                entry.index,
                entry.timestamp,
                entry.actor,
                entry.action,
                entry.details,
                entry.prev_hash,
            )
            if entry.entry_hash != expected:
                return False
            prev_hash = entry.entry_hash
        return True
