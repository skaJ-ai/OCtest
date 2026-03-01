"""PoC: /api/events/extract

비정형 텍스트 로그를 정형 이벤트 데이터로 변환하는 MVP 컨트롤러 초안.
- Taxonomy Guardrail: docs/hr_domain_knowledge.json 기반 L5 강제 매핑
- Low-confidence/HITL 플래그 지원
- reference_datetime 기반 상대시간 해석 지원
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.llm_service import call_llm  # type: ignore
except Exception:  # pragma: no cover
    call_llm = None

from app.services.taxonomy_service import get_l5_for_l6_id, map_to_l5, map_to_l6_by_output
from app.services.trace_service import append_case_events, build_process_map, build_trace, get_case_events
from app.services.viz_service import build_mermaid


router = APIRouter(prefix="/api/events", tags=["events"])

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


class L6Context(BaseModel):
    matched_l6_id: str = ""
    isolation_pass_reason: str = ""
    l6_candidates: list[dict[str, Any]] = Field(default_factory=list)
    confidence_breakdown: dict[str, float] = Field(default_factory=dict)


class ExtractedEvent(BaseModel):
    event_id: str
    l5_activity_name: str
    l6_activity_name: str = "Unclassified"
    mapping_status: str = "unclassified"
    l6_context: L6Context = Field(default_factory=L6Context)
    timestamp: str
    actor: str
    confidence_score: float
    evidence_span: str
    taxonomy_candidates: list[L5Candidate] = Field(default_factory=list)
    human_review_required: bool


class ExtractResponse(BaseModel):
    case_id: str
    source_type: str
    reference_datetime: str
    events: list[ExtractedEvent]
    summary: dict[str, int]


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


async def _call_llm_extract(prompt: str) -> list[dict[str, Any]]:
    """LLM 호출 포인트.

    기대 응답 형식(JSON 배열):
    [
      {
        "activity_raw": "...",
        "timestamp": "ISO-8601",
        "actor": "...",
        "confidence_score": 0.0,
        "evidence_span": "..."
      }
    ]
    """
    if call_llm is None:
        return []

    system_prompt = "당신은 HR 이벤트 추출기입니다. JSON 배열만 출력하세요."
    result = await call_llm(system_prompt, prompt, allow_text_fallback=True, max_tokens=1200, temperature=0.1)
    if not isinstance(result, dict):
        return []

    # call_llm이 이미 JSON 파싱된 dict를 줄 수 있으므로 다중 형식 처리
    for key in ("events", "data", "result"):
        if isinstance(result.get(key), list):
            return [x for x in result[key] if isinstance(x, dict)]

    # text fallback 형태면 speech/message에 JSON 배열이 들어있을 수 있음
    text = str(result.get("speech") or result.get("message") or "").strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            arr = json.loads(text)
            return [x for x in arr if isinstance(x, dict)]
        except Exception:
            return []

    return []


def _fallback_extract(raw_text: str, ref_dt: datetime) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    lines = [x.strip() for x in re.split(r"[\n\.]+", raw_text) if x.strip()]

    # 1차: 키워드 기반
    for i, line in enumerate(lines[:20], start=1):
        if not re.search(r"면담|요약|판례|징계|검토|확인|제안|지급|정산|관리|운영|작성|선발|승인|교육|조사|분석", line):
            continue
        ts = _resolve_relative_time(line, ref_dt)
        actor_match = re.search(r"([A-Za-z가-힣0-9_]+)\s*(?:가|이|는|은)", line)
        actor = actor_match.group(1) if actor_match else "Unknown"
        events.append(
            {
                "activity_raw": line[:100],
                "timestamp": ts,
                "actor": actor,
                "confidence_score": 0.62 if ts else 0.52,
                "evidence_span": line[:220],
                "event_id": f"evt_{i:02d}",
            }
        )

    # 2차: 어떤 경우에도 최소 1개 이벤트 생성(422 방지)
    if not events and lines:
        base = lines[0]
        ts = _resolve_relative_time(base, ref_dt)
        actor_match = re.search(r"([A-Za-z가-힣0-9_]+)\s*(?:가|이|는|은)", base)
        actor = actor_match.group(1) if actor_match else "Unknown"
        events.append(
            {
                "activity_raw": base[:100],
                "timestamp": ts,
                "actor": actor,
                "confidence_score": 0.4,
                "evidence_span": base[:220],
                "event_id": "evt_01",
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

            taxonomy = map_to_l5(activity_raw, req.options.top_k_candidates)
            taxonomy_candidates = taxonomy.get("taxonomy_candidates", [])
            l5_name = taxonomy.get("l5_activity_name", "Unclassified")
            mapping_status = taxonomy.get("mapping_status", "unclassified")

            l6_map = map_to_l6_by_output(evidence_span or activity_raw, req.options.top_k_candidates)
            l6_mapping_status = l6_map.get("mapping_status", "unclassified")

            # L6 매핑 성공 시 부모 L5 상속 강제
            matched_l6_id = l6_map.get("matched_l6_id", "")
            if l6_mapping_status == "matched_l6" and matched_l6_id:
                parent_l5 = get_l5_for_l6_id(matched_l6_id)
                if parent_l5 and parent_l5 != "Unclassified":
                    l5_name = parent_l5
                    mapping_status = "matched_l6"

            if mapping_status == "unclassified":
                unc_count += 1

            # confidence_score는 가장 정밀한 하위 계층(L6 final_score)과 동기화
            top_tax_score = float(taxonomy_candidates[0]["score"]) if taxonomy_candidates else 0.0
            l6_final_score = float((l6_map.get("confidence_breakdown") or {}).get("final_score", 0.0))
            confidence = max(confidence, min(top_tax_score, 0.95), l6_final_score)

            review_needed = (
                confidence < req.options.low_confidence_threshold
                or mapping_status == "unclassified"
                or not timestamp
                or actor == "Unknown"
                or not evidence_span
            )
            if review_needed:
                low_count += 1

            out_events.append(
                ExtractedEvent(
                    event_id=event_id,
                    l5_activity_name=l5_name,
                    l6_activity_name=l6_map.get("l6_name", "Unclassified"),
                    mapping_status=mapping_status,
                    l6_context=L6Context(
                        matched_l6_id=l6_map.get("matched_l6_id", ""),
                        isolation_pass_reason=l6_map.get("isolation_pass_reason", ""),
                        l6_candidates=l6_map.get("candidates", [])[:3],
                        confidence_breakdown=l6_map.get("confidence_breakdown", {}),
                    ),
                    timestamp=timestamp or ref_dt_iso,
                    actor=actor,
                    confidence_score=round(confidence, 4),
                    evidence_span=evidence_span,
                    taxonomy_candidates=[L5Candidate(**c) for c in taxonomy_candidates],
                    human_review_required=review_needed,
                )
            )

        case_id = req.context.case_id or "CASE-UNKNOWN"

        # in-memory store for trace/viz aggregation
        append_case_events(case_id, [e.model_dump() for e in out_events])

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


@router.get("/trace/{case_id}")
async def get_case_trace(case_id: str):
    events = get_case_events(case_id)
    return build_trace(case_id, events)


@router.get("/viz/process-map")
async def get_process_map(case_id: str):
    events = get_case_events(case_id)
    if not events:
        raise HTTPException(status_code=404, detail="case_id not found")
    trace = build_trace(case_id, events)
    pmap = build_process_map(case_id, events)
    mermaid = build_mermaid(pmap, trace)
    return {
        **pmap,
        "trace_summary": {
            "lead_time_sec": trace.get("lead_time_sec", 0),
            "transition_times": trace.get("transition_times", []),
            "variant_analysis": trace.get("variant_analysis", []),
        },
        "mermaid": mermaid,
    }
