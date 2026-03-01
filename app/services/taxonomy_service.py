"""Taxonomy guardrail service.

- hr_domain_knowledge.json 기반 L5 taxonomy 로드
- 도메인 유의어 치환
- Levenshtein distance 기반 유사도 계산
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

KB_PATH = Path(__file__).resolve().parents[2] / "docs" / "hr_domain_knowledge.json"

# 도메인 유의어/표현 정규화 사전 (1차)
SYNONYM_MAP = {
    "면담기록": "면담기록/요약",
    "면담 요약": "면담기록/요약",
    "판례 확인": "유사사례 및 판례 확인",
    "판례검색": "유사사례 및 판례 확인",
    "징계 제안": "징계항목 제안",
    "징계안 제안": "징계항목 제안",
    "퇴직 미지급금": "퇴직자 미지급금 지급",
    "연차 수당": "연차수당",
    "온보딩": "입사 및 온보딩",
    "jd 작성": "직무기술서 작성",
    "job description": "직무기술서 작성",
}


def _norm(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    return t


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + cost,
            ))
        prev = cur
    return prev[-1]


def _similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    dist = _levenshtein(na, nb)
    max_len = max(len(na), len(nb))
    return max(0.0, 1.0 - (dist / max_len))


@lru_cache(maxsize=1)
def load_l5_taxonomy() -> list[str]:
    raw = json.loads(KB_PATH.read_text(encoding="utf-8"))
    l5_list: list[str] = []
    for l3 in raw.get("l3_domains", []):
        for l4 in l3.get("l4", []):
            l5_list.extend([x for x in l4.get("l5", []) if isinstance(x, str) and x.strip()])
    uniq = sorted(set(l5_list))
    if not uniq:
        raise ValueError("taxonomy load failed: empty L5")
    return uniq


def normalize_activity(activity_raw: str) -> str:
    t = (activity_raw or "").strip()
    if not t:
        return ""
    low = t.lower()
    for k, v in SYNONYM_MAP.items():
        if k in low:
            return v
    return t


def map_to_l5(activity_raw: str, top_k: int = 3) -> dict[str, Any]:
    taxonomy = load_l5_taxonomy()
    activity = normalize_activity(activity_raw)

    # exact / contains
    n = _norm(activity)
    for l5 in taxonomy:
        ln = _norm(l5)
        if n == ln:
            return {
                "l5_activity_name": l5,
                "taxonomy_status": "matched",
                "taxonomy_candidates": [{"l5": l5, "score": 1.0}],
            }
        if ln and (ln in n or n in ln):
            return {
                "l5_activity_name": l5,
                "taxonomy_status": "matched",
                "taxonomy_candidates": [{"l5": l5, "score": 0.92}],
            }

    # levenshtein nearest
    scored = [(l5, _similarity(activity, l5)) for l5 in taxonomy]
    scored.sort(key=lambda x: x[1], reverse=True)
    candidates = [{"l5": k, "score": round(v, 4)} for k, v in scored[:max(1, top_k)]]

    if not candidates:
        return {
            "l5_activity_name": "Unclassified",
            "taxonomy_status": "unclassified",
            "taxonomy_candidates": [],
        }

    top = candidates[0]
    if top["score"] >= 0.75:
        status = "matched"
        l5_name = top["l5"]
    elif top["score"] >= 0.45:
        status = "suggested"
        l5_name = top["l5"]
    else:
        status = "unclassified"
        l5_name = "Unclassified"

    return {
        "l5_activity_name": l5_name,
        "taxonomy_status": status,
        "taxonomy_candidates": candidates,
    }
