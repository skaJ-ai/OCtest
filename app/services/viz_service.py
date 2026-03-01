"""Visualization service for process map + Mermaid generation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_mermaid(process_map: dict[str, Any], trace: dict[str, Any]) -> str:
    nodes = process_map.get("nodes", [])
    edges = process_map.get("edges", [])
    transitions = trace.get("transition_times", [])
    variants = trace.get("variant_analysis", [])

    # anomaly event ids
    anomaly_event_ids = {
        str(v.get("event_id"))
        for v in variants
        if bool(v.get("anomaly_flag"))
    }

    # transition bottleneck threshold
    times = [float(t.get("transition_time_sec", 0.0)) for t in transitions if t.get("transition_time_sec") is not None]
    avg_time = (sum(times) / len(times)) if times else 0.0
    critical_threshold = avg_time * 1.5 if avg_time > 0 else 0.0

    trans_by_edge: dict[tuple[str, str], float] = {}
    node_by_event: dict[str, str] = {}
    for n in nodes:
        ev_id = str((n.get("meta") or {}).get("event_id", ""))
        node_by_event[ev_id] = str(n.get("id"))

    for t in transitions:
        fe = str(t.get("from_event_id", ""))
        te = str(t.get("to_event_id", ""))
        if fe in node_by_event and te in node_by_event:
            trans_by_edge[(node_by_event[fe], node_by_event[te])] = float(t.get("transition_time_sec", 0.0))

    # group by l5 as cluster(subgraph)
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        l5 = str((n.get("meta") or {}).get("l5", "Unclassified")) or "Unclassified"
        clusters[l5].append(n)

    lines: list[str] = ["flowchart LR"]

    # declare nodes in subgraphs
    for i, (l5, members) in enumerate(clusters.items(), start=1):
        lines.append(f"  subgraph CL{i}[{l5}]")
        for n in members:
            node_id = n.get("id")
            label = n.get("label", "Unknown")
            safe_label = str(label).replace('"', "'")
            lines.append(f"    {node_id}[\"{safe_label}\"]")
        lines.append("  end")

    # edges + critical detection
    critical_nodes: set[str] = set()
    critical_edges: set[str] = set()

    for e in edges:
        s = str(e.get("source"))
        t = str(e.get("target"))
        eid = str(e.get("id"))
        lines.append(f"  {s} --> {t}")

        edge_t = trans_by_edge.get((s, t), 0.0)
        if edge_t >= critical_threshold and critical_threshold > 0:
            critical_edges.add(eid)
            critical_nodes.add(s)
            critical_nodes.add(t)

    # anomaly nodes as critical
    for n in nodes:
        ev_id = str((n.get("meta") or {}).get("event_id", ""))
        if ev_id in anomaly_event_ids:
            critical_nodes.add(str(n.get("id")))

    # style declarations
    for nid in sorted(critical_nodes):
        lines.append(f"  style {nid} fill:#ffdddd,stroke:#ff0000,stroke-width:2px")

    # cannot style edge directly in all Mermaid renderers; add class hint via linkStyle index fallback
    # approximate: mark all critical edges with thicker red link style by index
    if critical_edges:
        for idx, e in enumerate(edges):
            if str(e.get("id")) in critical_edges:
                lines.append(f"  linkStyle {idx} stroke:#ff0000,stroke-width:2px,color:#ff0000")

    return "\n".join(lines)
