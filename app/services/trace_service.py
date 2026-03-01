"""Process trace aggregation and variant analysis service."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

try:
    from app.services.taxonomy_service import load_l6_library
except Exception:  # pragma: no cover
    from taxonomy_service import load_l6_library  # type: ignore


_EVENT_STORE: dict[str, list[dict[str, Any]]] = defaultdict(list)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat((ts or "").replace("Z", "+00:00"))


def append_case_events(case_id: str, events: list[dict[str, Any]]) -> None:
    if not case_id:
        return
    _EVENT_STORE[case_id].extend(events)


def get_case_events(case_id: str) -> list[dict[str, Any]]:
    items = list(_EVENT_STORE.get(case_id, []))
    items.sort(key=lambda e: e.get("timestamp", ""))
    return items


def _standard_order_for_l5(l5_name: str) -> list[str]:
    lib = load_l6_library()
    return [str(x.get("l6_name")) for x in lib if str(x.get("l5")) == l5_name]


def build_trace(case_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "case_id": case_id,
            "events": [],
            "lead_time_sec": 0,
            "transition_times": [],
            "variant_analysis": [],
        }

    ordered = sorted(events, key=lambda e: e.get("timestamp", ""))

    # lead time
    try:
        start = _parse_ts(ordered[0].get("timestamp", ""))
        end = _parse_ts(ordered[-1].get("timestamp", ""))
        lead = max(0.0, (end - start).total_seconds())
    except Exception:
        lead = 0.0

    # transition times
    transitions: list[dict[str, Any]] = []
    for i in range(len(ordered) - 1):
        cur = ordered[i]
        nxt = ordered[i + 1]
        try:
            t = max(0.0, (_parse_ts(nxt.get("timestamp", "")) - _parse_ts(cur.get("timestamp", ""))).total_seconds())
        except Exception:
            t = 0.0
        transitions.append({
            "from_event_id": cur.get("event_id"),
            "to_event_id": nxt.get("event_id"),
            "from_l6": cur.get("l6_activity_name"),
            "to_l6": nxt.get("l6_activity_name"),
            "transition_time_sec": t,
        })

    # variant analysis (skip/loop/order inversion)
    variants: list[dict[str, Any]] = []
    std = _standard_order_for_l5(str(ordered[0].get("l5_activity_name", "")))
    std_idx = {name: i for i, name in enumerate(std)}

    visited: set[str] = set()
    last_idx = -1
    for i, ev in enumerate(ordered):
        l6 = str(ev.get("l6_activity_name", ""))
        reason = (ev.get("l6_context", {}) or {}).get("isolation_pass_reason", "")
        anomaly = False
        anomaly_reason = ""

        if l6 in visited:
            anomaly = True
            anomaly_reason = "loop_detected"
        visited.add(l6)

        if l6 in std_idx:
            idx = std_idx[l6]
            if idx < last_idx:
                anomaly = True
                anomaly_reason = "order_inversion"
            last_idx = max(last_idx, idx)
        else:
            anomaly = True
            anomaly_reason = "out_of_standard"

        # skip detection by gap
        if l6 in std_idx and i > 0:
            prev_l6 = str(ordered[i - 1].get("l6_activity_name", ""))
            if prev_l6 in std_idx and std_idx[l6] - std_idx[prev_l6] > 1:
                anomaly = True
                anomaly_reason = "step_skipping"

        variants.append({
            "event_id": ev.get("event_id"),
            "l6_activity_name": l6,
            "anomaly_flag": anomaly,
            "anomaly_type": anomaly_reason if anomaly else "",
            "analysis_reason": f"{anomaly_reason} | {reason}" if anomaly else reason,
        })

    return {
        "case_id": case_id,
        "events": ordered,
        "lead_time_sec": round(lead, 3),
        "transition_times": transitions,
        "variant_analysis": variants,
    }


def build_process_map(case_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda e: e.get("timestamp", ""))
    nodes = []
    edges = []
    for i, ev in enumerate(ordered):
        node_id = f"n{i+1}"
        nodes.append({
            "id": node_id,
            "label": ev.get("l6_activity_name") or ev.get("l5_activity_name") or "Unclassified",
            "meta": {
                "event_id": ev.get("event_id"),
                "case_id": case_id,
                "l5": ev.get("l5_activity_name"),
                "l6": ev.get("l6_activity_name"),
                "output": ((ev.get("l6_context") or {}).get("l6_candidates") or [{}])[0].get("output", ""),
                "evidence_span": ev.get("evidence_span", ""),
                "timestamp": ev.get("timestamp", ""),
                "mapping_status": ev.get("mapping_status", ""),
                "event_type": ev.get("event_type", "normal"),
            },
        })
        if i > 0:
            edges.append({
                "id": f"e{i}",
                "source": f"n{i}",
                "target": node_id,
                "label": "next",
            })

    return {
        "case_id": case_id,
        "nodes": nodes,
        "edges": edges,
        "render_hint": "mermaid|graphviz",
    }
