"""Lineage-lite: upstream/downstream links, impact analysis, cycle detection.

The graph is deliberately direction-aware: an edge upstream -> downstream
means "downstream is derived from upstream". Impact analysis answers
"what breaks if this asset changes?" as the transitive downstream set.
"""

from __future__ import annotations

from collections import deque


class CycleError(ValueError):
    pass


class LineageGraph:
    def __init__(self) -> None:
        self._downstream: dict[str, set[str]] = {}
        self._upstream: dict[str, set[str]] = {}

    def add_link(self, upstream: str, downstream: str) -> None:
        """Add an edge, refusing anything that would create a cycle."""
        if upstream == downstream:
            raise CycleError(f"self-loop is a cycle: {upstream}")
        # Adding upstream -> downstream creates a cycle iff downstream can
        # already reach upstream.
        if upstream in self.transitive_downstream(downstream):
            raise CycleError(
                f"link {upstream} -> {downstream} would create a cycle"
            )
        self._downstream.setdefault(upstream, set()).add(downstream)
        self._upstream.setdefault(downstream, set()).add(upstream)
        self._downstream.setdefault(downstream, set())
        self._upstream.setdefault(upstream, set())

    def downstream(self, asset_id: str) -> set[str]:
        return set(self._downstream.get(asset_id, set()))

    def upstream(self, asset_id: str) -> set[str]:
        return set(self._upstream.get(asset_id, set()))

    def transitive_downstream(self, asset_id: str) -> set[str]:
        return self._walk(asset_id, self._downstream)

    def transitive_upstream(self, asset_id: str) -> set[str]:
        return self._walk(asset_id, self._upstream)

    @staticmethod
    def _walk(start: str, adjacency: dict[str, set[str]]) -> set[str]:
        seen: set[str] = set()
        queue: deque[str] = deque(adjacency.get(start, set()))
        while queue:
            node = queue.popleft()
            if node in seen or node == start:
                continue
            seen.add(node)
            queue.extend(adjacency.get(node, set()))
        return seen

    def impact_analysis(self, asset_id: str) -> list[str]:
        """Sorted transitive downstream set: everything affected by a change."""
        return sorted(self.transitive_downstream(asset_id))

    def detect_cycle(self) -> list[str] | None:
        """Return one cycle path if the graph has one, else None.

        add_link() prevents cycles, so this normally returns None; it exists
        to verify graphs built by other means (imports, bulk loads).
        """
        WHITE, GREY, BLACK = 0, 1, 2
        color: dict[str, int] = {}
        stack: list[str] = []

        def visit(node: str) -> list[str] | None:
            color[node] = GREY
            stack.append(node)
            for nxt in sorted(self._downstream.get(node, set())):
                if color.get(nxt, WHITE) == GREY:
                    idx = stack.index(nxt)
                    return stack[idx:] + [nxt]
                if color.get(nxt, WHITE) == WHITE:
                    found = visit(nxt)
                    if found:
                        return found
            stack.pop()
            color[node] = BLACK
            return None

        for node in sorted(self._downstream):
            if color.get(node, WHITE) == WHITE:
                found = visit(node)
                if found:
                    return found
        return None
