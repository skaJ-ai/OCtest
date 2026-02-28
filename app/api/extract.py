"""PoC: /api/events/extract

비정형 텍스트 로그를 정형 이벤트 데이터로 변환하는 MVP 컨트롤러 초안.
- Taxonomy Guardrail: docs/hr_domain_knowledge.json 기반 L5 강제 매핑
- Low-confidence/HITL 플래그 지원
- reference_datetime 기반 상대시간 해석 지원
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/events", tags=["events"])

KB_PATH = Path(__file__).resolve().parents[2] / "docs" / "hr_domain_knowledge.json"
DEFAULT_THRESHOLD = 0.75


class ExtractOptions(BaseModel):
    low_confidence_threshold: float = Field(default=DEFAULT_THRESHOLD, ge=0.0, le=1.0)
    top_k_candidates: int = Field(default=3, ge=1, le=10)


class ExtractContext(BaseModel):
    case_id: Optional[str] = None
    l3_hint: Optional[str] = None
    l4_hint: Optional[str] = None
    language: str = "ko-KR"
    timezone: str = "Asia/Seoul"


class ExtractRequest(BaseModel):
    raw_text: str
    source_type: str
    reference_datetime: Optional[str] = None  # ISO-8601
    context: ExtractContext = Field(default_factory=ExtractContext)
    options: ExtractOptions = Field(default_factory=ExtractOptions)


class L5Candidate(BaseModel):
    l5: str
    score: float


class ExtractedEvent(BaseModel):
    event_id: str
    l5_activity_name: str
    timestamp: str
    actor: str
    confidence_score: float
    evidence_span: str
    taxonomy_status: str
    taxonomy_candidates: list[L5Candidate] = Field(default_factory=list)
    human_review_required: bool


class ExtractResponse(BaseModel):
    case_id: str
    source_type: str
    reference_datetime: str
    events: list[ExtractedEvent]
    summary: dict[str, int]


@dataclass
class TaxonomyMatch:
    l5_activity_name: str
    taxonomy_status: str
    candidates: list[dict[str, Any]]


def _load_l5_taxonomy() -> list[str]:
    if not KB_PATH.exists():
        raise FileNotFoundError(f"taxonomy file not found: {KB_PATH}")

    raw = json.loads(KB_PATH.read_text(encoding="utf-8"))
    l5_list: list[str] = []
    for l3 in raw.get("l3_domains", []):
        for l4 in l3.get("l4", []):
            l5_list.extend([x for x in l4.get("l5", []) if isinstance(x, str) and x.strip()])

    if not l5_list:
        raise ValueError("taxonomy load failed: empty l5 list")

    return sorted(set(l5_list))


L5_TAXONOMY = _load_l5_taxonomy()


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def _token_overlap_score(a: str, b: str) -> float:
    aa = set(re.findall(r"[가-힣A-Za-z0-9]+", a))
    bb = set(re.findall(r"[가-힣A-Za-z0-9]+", b))
    if not aa or not bb:
        return 0.0
    inter = len(aa & bb)
    union = len(aa | bb)
    return inter / union if union else 0.0


def _guardrail_map_l5(activity_raw: str, top_k: int = 3) -> TaxonomyMatch:
    # 1) exact/contains
    n = _norm(activity_raw)
    for l5 in L5_TAXONOMY:
        ln = _norm(l5)
        if n == ln:
            return TaxonomyMatch(l5, "matched", [{"l5": l5, "score": 1.0}])
        if ln and (ln in n or n in ln):
            return TaxonomyMatch(l5, "matched", [{"l5": l5, "score": 0.9}])

    # 2) token overlap candidate
    scored: list[tuple[str, float]] = []
    for l5 in L5_TAXONOMY:
        s = _token_overlap_score(activity_raw, l5)
        if s > 0:
            scored.append((l5, s))

    scored.sort(key=lambda x: x[1], reverse=True)
    candidates = [{"l5": name, "score": round(score, 4)} for name, score in scored[:top_k]]

    if candidates:
        top_score = candidates[0]["score"]
        if top_score >= 0.7:
            return TaxonomyMatch(candidates[0]["l5"], "matched", candidates)
        return TaxonomyMatch(candidates[0]["l5"], "suggested", candidates)

    # 3) unclassified
    return TaxonomyMatch("Unclassified", "unclassified", [])


def _parse_ref_dt(reference_datetime: Optional[str]) -> datetime:
    if reference_datetime:
        try:
            return datetime.fromisoformat(reference_datetime.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="reference_datetime must be ISO-8601")
    return datetime.now().astimezone()


def _resolve_relative_time(text: str, ref_dt: datetime) -> str:
    t = (text or "").strip()
    if not t:
        return ""

    # absolute date-time patterns first
    p = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?", t)
    if p:
        y, m, d = int(p.group(1)), int(p.group(2)), int(p.group(3))
        hh = int(p.group(4) or 0)
        mm = int(p.group(5) or 0)
        return ref_dt.replace(year=y, month=m, day=d, hour=hh, minute=mm, second=0, microsecond=0).isoformat()

    # relative korean expressions
    base = ref_dt
    if "그저께" in t:
        base = base - timedelta(days=2)
    elif "어제" in t:
        base = base - timedelta(days=1)
    elif "오늘" in t:
        base = base
    elif "내일" in t:
        base = base + timedelta(days=1)

    hm = re.search(r"(오전|오후)?\s*(\d{1,2})[:시]\s*(\d{2})?", t)
    if hm:
        ap = hm.group(1)
        h = int(hm.group(2))
        minute = int(hm.group(3) or 0)
        if ap == "오후" and h < 12:
            h += 12
        if ap == "오전" and h == 12:
            h = 0
        base = base.replace(hour=h, minute=minute, second=0, microsecond=0)

    # If only relative day found, keep current clock from reference
    if any(k in t for k in ["그저께", "어제", "오늘", "내일"]) or hm:
        return base.isoformat()

    return ""


def _build_prompt(req: ExtractRequest, ref_dt_iso: str) -> str:
    return f"""
당신은 HR 비정형 로그를 이벤트로 파싱하는 엔진입니다.
반드시 JSON 배열만 반환하세요.

[목표]
원문에서 이벤트를 추출하고 각 이벤트에 아래 필드를 채우세요:
- activity_raw
- timestamp (ISO-8601 절대시간)
- actor
- confidence_score (0~1)
- evidence_span (원문에서 직접 발췌)

[중요: 시간 해석 규칙]
- reference_datetime={ref_dt_iso}
- 원문에 상대 시간 표현(예: 어제, 오늘 오전, 방금, 지난주)이 있으면 reference_datetime 기준으로 절대시간으로 변환하세요.
- timestamp를 비워두지 마세요. 추정이 불가하면 reference_datetime 시점을 사용하고 confidence를 낮추세요.

[입력]
source_type={req.source_type}
case_id={req.context.case_id or ''}
l3_hint={req.context.l3_hint or ''}
l4_hint={req.context.l4_hint or ''}

raw_text:
{req.raw_text}
""".strip()


async def _call_llm_extract(_prompt: str) -> list[dict[str, Any]]:
    """LLM 호출 포인트 (PoC). 실제 연동 시 교체."""
    return []


def _fallback_extract(raw_text: str, ref_dt: datetime) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    lines = [x.strip() for x in re.split(r"[\n\.]+", raw_text) if x.strip()]
    for i, line in enumerate(lines[:20], start=1):
        if not re.search(r"면담|요약|판례|징계|검토|확인|제안|지급|정산", line):
            continue
        ts = _resolve_relative_time(line, ref_dt)
        actor_match = re.search(r"([A-Za-z가-힣0-9_]+)\s*(?:가|이|는|은)", line)
        actor = actor_match.group(1) if actor_match else "Unknown"
        events.append(
            {
                "activity_raw": line[:80],
                "timestamp": ts,
                "actor": actor,
                "confidence_score": 0.55 if ts else 0.45,
                "evidence_span": line[:180],
                "event_id": f"evt_{i:02d}",
            }
        )
    return events


@router.post("/extract", response_model=ExtractResponse)
async def extract_events(req: ExtractRequest):
    if not req.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is required")
    if not req.source_type.strip():
        raise HTTPException(status_code=400, detail="source_type is required")

    ref_dt = _parse_ref_dt(req.reference_datetime)
    ref_dt_iso = ref_dt.isoformat()

    try:
        prompt = _build_prompt(req, ref_dt_iso)
        llm_events = await _call_llm_extract(prompt)
        events_raw = llm_events if llm_events else _fallback_extract(req.raw_text, ref_dt)

        if not events_raw:
            raise HTTPException(status_code=422, detail="no events extracted")

        out_events: list[ExtractedEvent] = []
        low_count = 0
        unc_count = 0

        for idx, ev in enumerate(events_raw, start=1):
            activity_raw = str(ev.get("activity_raw", "")).strip()
            timestamp = str(ev.get("timestamp", "")).strip() or ""
            actor = str(ev.get("actor", "Unknown")).strip() or "Unknown"
            confidence = float(ev.get("confidence_score", 0.0))
            evidence_span = str(ev.get("evidence_span", "")).strip()
            event_id = str(ev.get("event_id", f"evt_{idx:02d}"))

            # fallback: relative resolution if timestamp still missing
            if not timestamp:
                timestamp = _resolve_relative_time(evidence_span or activity_raw, ref_dt)

            taxonomy = _guardrail_map_l5(activity_raw, req.options.top_k_candidates)
            if taxonomy.taxonomy_status == "unclassified":
                unc_count += 1

            review_needed = (
                confidence < req.options.low_confidence_threshold
                or taxonomy.taxonomy_status != "matched"
                or not timestamp
                or actor == "Unknown"
                or not evidence_span
            )
            if review_needed:
                low_count += 1

            out_events.append(
                ExtractedEvent(
                    event_id=event_id,
                    l5_activity_name=taxonomy.l5_activity_name,
                    timestamp=timestamp or ref_dt_iso,
                    actor=actor,
                    confidence_score=round(confidence, 4),
                    evidence_span=evidence_span,
                    taxonomy_status=taxonomy.taxonomy_status,
                    taxonomy_candidates=[L5Candidate(**c) for c in taxonomy.candidates],
                    human_review_required=review_needed,
                )
            )

        case_id = req.context.case_id or "CASE-UNKNOWN"
        return ExtractResponse(
            case_id=case_id,
            source_type=req.source_type,
            reference_datetime=ref_dt_iso,
            events=out_events,
            summary={
                "event_count": len(out_events),
                "low_confidence_count": low_count,
                "unclassified_count": unc_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal_error: {e}")
