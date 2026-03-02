#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import defaultdict, deque
from pathlib import Path

SRC = Path("docs/hr_l6_apqc_master_library_v2.1_custom.json")


def build_graph(library: list[dict]):
    ids = {x.get("l6_id") for x in library if x.get("l6_id")}
    adj = defaultdict(list)
    indeg = defaultdict(int)

    for item in library:
        cur = item.get("l6_id")
        for nxt in item.get("successors", []) or []:
            if nxt in ids and cur in ids:
                adj[cur].append(nxt)
                indeg[nxt] += 1
                indeg[cur] += 0
        for prev in item.get("predecessors", []) or []:
            if prev in ids and cur in ids:
                adj[prev].append(cur)
                indeg[cur] += 1
                indeg[prev] += 0
    return ids, adj, indeg


def has_cycle(ids, adj, indeg):
    q = deque([n for n in ids if indeg.get(n, 0) == 0])
    seen = 0
    indeg2 = dict(indeg)
    while q:
        n = q.popleft()
        seen += 1
        for m in adj.get(n, []):
            indeg2[m] = indeg2.get(m, 0) - 1
            if indeg2[m] == 0:
                q.append(m)
    return seen != len(ids)


def orphan_check(library: list[dict]):
    by_group = defaultdict(list)
    for item in library:
        by_group[(item.get("l3"), item.get("l4"), item.get("l5"))].append(item)

    orphans = []
    for grp, items in by_group.items():
        idset = {x.get("l6_id") for x in items}
        # a node is orphan if it has no incoming+outgoing within group and group has >1 nodes
        if len(items) <= 1:
            continue
        for x in items:
            preds = [p for p in (x.get("predecessors") or []) if p in idset]
            succs = [s for s in (x.get("successors") or []) if s in idset]
            if not preds and not succs:
                orphans.append(x.get("l6_id"))
    return orphans


def main() -> int:
    obj = json.loads(SRC.read_text(encoding="utf-8"))
    library = obj.get("library", [])

    ids, adj, indeg = build_graph(library)
    cyc = has_cycle(ids, adj, indeg)
    orphans = orphan_check(library)

    print(json.dumps({
        "total_l6": len(library),
        "has_cycle": cyc,
        "orphan_count": len(orphans),
        "orphans": orphans[:30]
    }, ensure_ascii=False, indent=2))

    return 1 if cyc else 0


if __name__ == "__main__":
    raise SystemExit(main())
