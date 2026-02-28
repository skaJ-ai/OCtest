"""L345 HR 프로세스 참조 데이터 로더

단일 소스: docs/hr_domain_knowledge.json
- L3 → L4 → [L5] 트리를 로드하여 프롬프트 컨텍스트에 주입
- 기존 API(find_l3_for_l4/get_l345_context) 호환 유지
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
KB_PATH = PROJECT_ROOT / "docs" / "hr_domain_knowledge.json"


def _normalize_korean(raw: str) -> str:
    """'채용(Recruiting)' → '채용', 앞뒤 공백 제거"""
    text = (raw or "").strip()
    if not text:
        return ""
    m = re.match(r"^([^(（]+)", text)
    return (m.group(1).strip() if m else text).strip()


def _load_l345_tree() -> dict[str, dict[str, list[str]]]:
    if not KB_PATH.exists():
        raise FileNotFoundError(f"L345 KB 파일이 없습니다: {KB_PATH}")

    with KB_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    domains = raw.get("l3_domains")
    if not isinstance(domains, list):
        raise ValueError("hr_domain_knowledge.json 형식 오류: l3_domains가 배열이 아님")

    tree: dict[str, dict[str, list[str]]] = {}
    for d in domains:
        l3 = (d.get("l3") or "").strip()
        if not l3:
            continue

        l4_obj: dict[str, list[str]] = {}
        for l4 in d.get("l4", []):
            l4_name = (l4.get("name") or "").strip()
            if not l4_name:
                continue
            l5_list = [str(x).strip() for x in (l4.get("l5") or []) if str(x).strip()]
            l4_obj[l4_name] = l5_list

        if l4_obj:
            tree[l3] = l4_obj

    if not tree:
        raise ValueError("hr_domain_knowledge.json 형식 오류: 유효한 L3/L4/L5 데이터가 없음")

    return tree


L345_TREE: dict[str, dict[str, list[str]]] = _load_l345_tree()


# ── L4→L3 역방향 인덱스 (first-wins) ──
_L4_TO_L3: dict[str, str] = {}
for _l3, _l4_dict in L345_TREE.items():
    for _l4 in _l4_dict:
        if _l4 not in _L4_TO_L3:
            _L4_TO_L3[_l4] = _l3


def find_l3_for_l4(l4_raw: str) -> Optional[tuple[str, str]]:
    """L4 문자열에서 해당 (L3, 정규화된 L4명) 반환. 실패 시 None."""
    normalized = _normalize_korean(l4_raw)
    if not normalized:
        return None

    # 1) L4 정확 매칭
    if normalized in _L4_TO_L3:
        return (_L4_TO_L3[normalized], normalized)

    # 2) L3 이름 정확·접두사 매칭
    for l3_name in L345_TREE:
        if normalized == l3_name or normalized.startswith(l3_name):
            return (l3_name, "")

    # 3) L4 부분 매칭 (긴 키 우선)
    candidates = [
        (len(l4_key), l4_key, l3_name)
        for l4_key, l3_name in _L4_TO_L3.items()
        if l4_key in normalized or normalized in l4_key
    ]
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        _, best_key, best_l3 = candidates[0]
        return (best_l3, best_key)

    # 4) L3 느슨 매칭
    for l3_name in L345_TREE:
        if l3_name in normalized or normalized in l3_name:
            return (l3_name, "")

    return None


def _find_l5_in_tree(l5_raw: str, l3_name: str) -> Optional[tuple[str, str]]:
    """L3 블록 내에서 L5가 어느 L4에 속하는지 찾기. (L4명, L5명) 반환."""
    normalized = _normalize_korean(l5_raw)
    if not normalized or l3_name not in L345_TREE:
        return None

    for l4_key, l5_list in L345_TREE[l3_name].items():
        for l5 in l5_list:
            if normalized == l5 or normalized in l5 or l5 in normalized:
                return (l4_key, l5)

    return None


def get_l345_context(l4_raw: str, l5_raw: str = "", process_name: str = "") -> str:
    """사용자의 L4/L5에 맞는 L3 블록을 프롬프트 삽입용 문자열로 반환."""
    result = find_l3_for_l4(l4_raw)
    if not result:
        return ""

    l3_name, matched_l4 = result
    l3_block = L345_TREE[l3_name]

    current_l4 = matched_l4
    current_l5 = ""
    if l5_raw:
        l5_result = _find_l5_in_tree(l5_raw, l3_name)
        if l5_result:
            current_l4, current_l5 = l5_result

    current_desc_parts = []
    if current_l4:
        current_desc_parts.append(current_l4)
    if current_l5:
        current_desc_parts.append(current_l5)
    if process_name:
        pn = _normalize_korean(process_name)
        if pn and pn not in " ".join(current_desc_parts):
            current_desc_parts.append(pn)

    current_desc = " > ".join(current_desc_parts) if current_desc_parts else "미상"

    lines = [
        f"[HR 프로세스 참조: {l3_name}]",
        f"현재 작업: {current_desc}",
        "",
        f"{l3_name}의 전체 구조:",
    ]

    for l4_key, l5_list in l3_block.items():
        l5_formatted = [f"{l5} ← 현재" if l5 == current_l5 else l5 for l5 in l5_list]
        marker = " ←" if l4_key == current_l4 and not current_l5 else ""
        lines.append(f"  {l4_key}{marker}: {', '.join(l5_formatted)}")

    lines.append("")
    lines.append("이 구조를 참고하여 누락 단계, 전후 흐름, 분기점을 제안하세요.")

    return "\n".join(lines)
