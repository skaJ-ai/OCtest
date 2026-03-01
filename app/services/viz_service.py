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
    exception_nodes: set[str] = set()
    for i, (l5, members) in enumerate(clusters.items(), start=1):
        lines.append(f"  subgraph CL{i}[{l5}]")
        for n in members:
            node_id = n.get("id")
            label = n.get("label", "Unknown")
            safe_label = str(label).replace('"', "'")
            e_type = str((n.get("meta") or {}).get("event_type", "normal"))
            if e_type in ("rework", "suspended"):
                lines.append(f"    {node_id}{{\"{safe_label}\"}}")
                exception_nodes.add(str(node_id))
            else:
                lines.append(f"    {node_id}[\"{safe_label}\"]")
        lines.append("  end")

    # edges + critical detection
    critical_nodes: set[str] = set()
    critical_edges: set[str] = set()

    anomaly_type_by_event = {str(v.get("event_id")): str(v.get("anomaly_type", "")) for v in variants}
    edge_style_index: dict[int, str] = {}

    for idx, e in enumerate(edges):
        s = str(e.get("source"))
        t = str(e.get("target"))
        eid = str(e.get("id"))
        # label with transition time (red text)
        tt = trans_by_edge.get((s, t), 0.0)
        if tt > 0:
            lines.append(f"  {s} -- \"{int(tt)}s\" --> {t}")
        else:
            lines.append(f"  {s} --> {t}")

        edge_t = trans_by_edge.get((s, t), 0.0)
        if edge_t >= critical_threshold and critical_threshold > 0:
            critical_edges.add(eid)
            critical_nodes.add(s)
            critical_nodes.add(t)
            edge_style_index[idx] = "critical"

        # anomaly edge type color (using target event)
        target_event = ""
        for ev_id, nid in node_by_event.items():
            if nid == t:
                target_event = ev_id
                break
        at = anomaly_type_by_event.get(target_event, "")
        if at == "step_skipping":
            edge_style_index[idx] = "skip"
        elif at == "order_inversion":
            edge_style_index[idx] = "inversion"

    # feedback loop: rework/suspended -> later resolved on same L6
    node_meta = {str(n.get('id')): (n.get('meta') or {}) for n in nodes}
    feedback_edges: list[tuple[str, str]] = []
    for i in range(len(nodes)):
        ni = str(nodes[i].get('id'))
        mi = node_meta.get(ni, {})
        if str(mi.get('event_type')) not in ('rework', 'suspended'):
            continue
        for j in range(i + 1, len(nodes)):
            nj = str(nodes[j].get('id'))
            mj = node_meta.get(nj, {})
            if str(mj.get('event_type')) == 'resolved' and str(mj.get('l6')) == str(mi.get('l6')):
                feedback_edges.append((ni, nj))
                break

    for k, (a, b) in enumerate(feedback_edges, start=1):
        lines.append(f"  {a} -. feedback .-> {b}")

    # anomaly nodes as critical
    for n in nodes:
        ev_id = str((n.get("meta") or {}).get("event_id", ""))
        if ev_id in anomaly_event_ids:
            critical_nodes.add(str(n.get("id")))

    # style declarations
    for nid in sorted(critical_nodes):
        lines.append(f"  style {nid} fill:#ffdddd,stroke:#ff0000,stroke-width:2px")
    for nid in sorted(exception_nodes):
        lines.append(f"  style {nid} fill:#fff5f5,stroke:#ff0000,stroke-width:2px,stroke-dasharray: 5 5")

    for idx, style in edge_style_index.items():
        if style == "critical":
            width = 4 if avg_time > 0 and any(trans_by_edge.get((str(e.get('source')), str(e.get('target'))),0) >= avg_time*2 for i,e in enumerate(edges) if i==idx) else 2
            lines.append(f"  linkStyle {idx} stroke:#ff0000,stroke-width:{width}px,color:#ff0000")
        elif style == "skip":
            lines.append(f"  linkStyle {idx} stroke:#ff9900,stroke-width:2px,stroke-dasharray:5 5,color:#ff9900")
        elif style == "inversion":
            lines.append(f"  linkStyle {idx} stroke:#8000ff,stroke-width:2px,color:#8000ff")

    # legend (variant semantics)
    lines.append("  subgraph LEGEND[Legend]")
    lines.append("    lg1[빨간색 실선: 평균 대비 지연(Bottleneck) 구간]")
    lines.append("    lg2[주황색 점선: Step Skipping 발생 구간]")
    lines.append("    lg3[보라색 화살표: 역순(Order Inversion) 발생 구간]")
    lines.append("    lg4[정상 이벤트: 실선 사각 노드]")
    lines.append("    lg5[예외 이벤트(rework/suspended): 빨간 점선 마름모 노드]")
    lines.append("  end")
    lines.append("  style lg1 fill:#ffe5e5,stroke:#ff0000,stroke-width:2px")
    lines.append("  style lg2 fill:#fff1e0,stroke:#ff9900,stroke-width:2px,stroke-dasharray: 5 5")
    lines.append("  style lg3 fill:#f1e5ff,stroke:#8000ff,stroke-width:2px")
    lines.append("  style lg4 fill:#e8f5ff,stroke:#2d6cdf,stroke-width:2px")
    lines.append("  style lg5 fill:#fff5f5,stroke:#ff0000,stroke-width:2px,stroke-dasharray: 5 5")

    return "\n".join(lines)
