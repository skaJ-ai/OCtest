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
_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
L6_LIB_PATH = _DOCS_DIR / "hr_l6_apqc_master_library.json"
if not L6_LIB_PATH.exists():
    L6_LIB_PATH = _DOCS_DIR / "hr_l6_apqc_library.json"

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


@lru_cache(maxsize=1)
def load_l6_library() -> list[dict[str, Any]]:
    if not L6_LIB_PATH.exists():
        return []
    raw = json.loads(L6_LIB_PATH.read_text(encoding="utf-8"))
    lib = raw.get("library", [])
    return [x for x in lib if isinstance(x, dict)]


def get_l5_for_l6_id(l6_id: str) -> str:
    if not l6_id:
        return "Unclassified"
    for row in load_l6_library():
        if row.get("l6_id") == l6_id:
            return str(row.get("l5") or "Unclassified")
    return "Unclassified"


def get_l5_for_l6_name(l6_name: str) -> str:
    key = (l6_name or "").strip()
    if not key:
        return "Unclassified"
    for row in load_l6_library():
        if str(row.get("l6_name", "")).strip() == key:
            return str(row.get("l5") or "Unclassified")
    return "Unclassified"


def get_l6_id_for_name(l6_name: str) -> str:
    key = (l6_name or "").strip()
    if not key:
        return ""
    for row in load_l6_library():
        if str(row.get("l6_name", "")).strip() == key:
            return str(row.get("l6_id") or "")
    return ""


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
                "mapping_status": "matched_l5",
                "taxonomy_candidates": [{"l5": l5, "score": 1.0}],
            }
        if ln and (ln in n or n in ln):
            return {
                "l5_activity_name": l5,
                "mapping_status": "matched_l5",
                "taxonomy_candidates": [{"l5": l5, "score": 0.92}],
            }

    # levenshtein nearest
    scored = [(l5, _similarity(activity, l5)) for l5 in taxonomy]
    scored.sort(key=lambda x: x[1], reverse=True)
    candidates = [{"l5": k, "score": round(v, 4)} for k, v in scored[:max(1, top_k)]]

    if not candidates:
        return {
            "l5_activity_name": "Unclassified",
            "mapping_status": "unclassified",
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
        "mapping_status": "matched_l5" if status == "matched" else ("suggested_l5" if status == "suggested" else "unclassified"),
        "taxonomy_candidates": candidates,
    }


def map_to_l6_by_output(text: str, top_k: int = 3) -> dict[str, Any]:
    """텍스트 내 결과물(output) 키워드를 기반으로 L6 매핑 + reasoning 반환."""
    src = (text or "").strip()
    lib = load_l6_library()
    if not src or not lib:
        return {
            "l6_name": "Unclassified",
            "mapping_status": "unclassified",
            "candidates": [],
            "matched_l6_id": "",
            "isolation_pass_reason": "입력 텍스트 또는 L6 라이브러리가 없어 고립 테스트를 수행할 수 없습니다.",
            "confidence_breakdown": {"keyword_score": 0.0, "similarity_score": 0.0, "bonus_score": 0.0, "final_score": 0.0},
        }

    output_tokens = ["신청", "신청서", "등록", "등록번호", "완료", "발송", "처리 이력", "이력", "승인"]

    def keyword_score(src_text: str, output_text: str) -> float:
        score = 0.0
        for t in output_tokens:
            if t in src_text and t in output_text:
                score += 0.2
        return min(score, 0.8)

    scored: list[tuple[dict[str, Any], float, float, float, float]] = []
    for row in lib:
        output = str(row.get("output", ""))
        l6_name = str(row.get("l6_name", ""))
        sim_out = _similarity(src, output)
        sim_l6 = _similarity(src, l6_name)
        sim = max(sim_out, sim_l6)
        kscore = keyword_score(src, output)
        bonus = 0.0
        if ("강사" in src) and ("강사" in output or "강사" in l6_name):
            bonus += 0.25
        final = min(sim + kscore + bonus, 1.0)
        scored.append((row, final, sim, kscore, bonus))

    scored.sort(key=lambda x: x[1], reverse=True)
    cand = [
        {
            "l6_id": r.get("l6_id"),
            "l6_name": r.get("l6_name"),
            "l5": r.get("l5"),
            "output": r.get("output"),
            "score": round(final, 4),
            "similarity_score": round(sim, 4),
            "keyword_score": round(ks, 4),
            "bonus_score": round(bonus, 4),
        }
        for r, final, sim, ks, bonus in scored[:max(1, top_k)]
    ]

    if not cand:
        return {
            "l6_name": "Unclassified",
            "mapping_status": "unclassified",
            "candidates": [],
            "matched_l6_id": "",
            "isolation_pass_reason": "매핑 후보가 없어 고립 테스트 통과 근거를 생성할 수 없습니다.",
            "confidence_breakdown": {"keyword_score": 0.0, "similarity_score": 0.0, "bonus_score": 0.0, "final_score": 0.0},
        }

    top = cand[0]
    if top["score"] >= 0.72:
        status = "matched"
        name = top["l6_name"]
    elif top["score"] >= 0.45:
        status = "suggested"
        name = top["l6_name"]
    else:
        status = "unclassified"
        name = "Unclassified"

    matched_output = top.get("output", "")
    token_hit = next((t for t in output_tokens if t in src and t in matched_output), None)
    if status in ("matched", "suggested"):
        if token_hit:
            reason = f"텍스트 내 '{token_hit}' 표현이 L6 산출물 '{matched_output}'과 직접 연결되어 독립 산출물이 확인됩니다."
        else:
            reason = f"텍스트가 L6 산출물 '{matched_output}'과 유사하게 일치하여 독립 결과물 생성 가능성이 확인됩니다."
    else:
        reason = "텍스트에서 독립 산출물을 특정할 수 있는 근거가 부족하여 고립 테스트를 통과하지 못했습니다."

    return {
        "l6_name": name,
        "mapping_status": "matched_l6" if status == "matched" else ("suggested_l6" if status == "suggested" else "unclassified"),
        "candidates": cand,
        "matched_l6_id": top.get("l6_id", "") if status != "unclassified" else "",
        "isolation_pass_reason": reason,
        "confidence_breakdown": {
            "keyword_score": top.get("keyword_score", 0.0),
            "similarity_score": top.get("similarity_score", 0.0),
            "bonus_score": top.get("bonus_score", 0.0),
            "final_score": top.get("score", 0.0),
        },
    }
