#!/usr/bin/env python3
"""24/7 Synthetic Stress Test Loop for /api/events/extract

Step A: hr_domain_knowledge.json에서 랜덤 L5 선택
Step B: LLM(또는 fallback 템플릿)로 노이즈 섞인 비정형 텍스트 생성
Step C: /api/events/extract 호출
Step D: 자동 검증
  (1) 선택 L5와 일치 여부
  (2) confidence_score 수준
  (3) evidence_span 원문 포함 여부

실패/저신뢰 케이스는 data/logs/hard_cases.jsonl에 저장.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "docs" / "hr_domain_knowledge.json"
HARD_CASES_PATH = ROOT / "data" / "logs" / "hard_cases.jsonl"
REPORT_PATH = ROOT / "data" / "logs" / "synthetic_report_latest.json"


def load_l5_pool() -> list[str]:
    raw = json.loads(KB_PATH.read_text(encoding="utf-8"))
    pool = []
    for l3 in raw.get("l3_domains", []):
        for l4 in l3.get("l4", []):
            pool.extend([x for x in l4.get("l5", []) if isinstance(x, str) and x.strip()])
    uniq = sorted(set(pool))
    if not uniq:
        raise RuntimeError("L5 pool is empty")
    return uniq


def _core_keyword(target_l5: str) -> str:
    # 핵심 키워드는 최소한 target_l5 문자열 자체를 포함
    return target_l5.strip()


async def generate_noisy_text_with_llm(target_l5: str) -> str:
    """LLM 생성 시도. 실패하면 빈 문자열 반환."""
    try:
        from backend.llm_service import call_llm  # type: ignore
        import asyncio

        core_kw = _core_keyword(target_l5)
        prompt = f"""
당신은 HR 로그 생성기입니다.
목표 L5 활동: {target_l5}
핵심 키워드: {core_kw}

아래 조건으로 한국어 비정형 텍스트를 생성하세요.
- 반드시 3~5단계의 연속 업무 시나리오(문장 3~5개)
- 현업 담당자가 급하게 남긴 메모처럼 지저분하고 모호하게 작성
- 악의적 노이즈 포함: 오탈자, 주어 생략, 지시어(이거/저거), 중간 취소/보류 표현
- 상대 시간 표현 포함(어제, 오늘 오전, 방금, 내일 다시)
- 핵심 키워드("{core_kw}")를 2회 이상 포함
- 복합 지시 포함(예: "정산서 결재는 올리지 마", "일단 보류")
- 문장 일부는 구어체/반말/축약형 허용

JSON으로만 응답:
{{"raw_text":"..."}}
""".strip()
        result = await asyncio.wait_for(
            call_llm("텍스트 생성기", prompt, allow_text_fallback=True, max_tokens=300, temperature=0.7),
            timeout=8.0,
        )
        if isinstance(result, dict):
            txt = result.get("raw_text") or result.get("speech") or result.get("message") or ""
            return str(txt).strip()
        return ""
    except Exception:
        return ""


def fallback_noisy_text(target_l5: str) -> str:
    kw = _core_keyword(target_l5)
    templates = [
        f"어제 면담에서 {kw} 얘기 나왔고 김과장이 위로금 불만 제기함. 일단 보류, 내일 다시 협의하기로. 정산서 결재는 올리지 마라고 전달됨.",
        f"{kw} 건 어제 처리하려다 중간에 멈춤;; 신청서는 넣었는데 승인 안 남. 담당자 바뀌어서 이력도 누락, 오늘 오전 다시 맞추는 중.",
        f"메모조각: {kw} 먼저 한다고 했는데 저쪽에서 반려. 등록번호는 생성됐다는 말 있음, 근데 공식 통지는 아직. 내일 재면담 예정.",
    ]
    return random.choice(templates)


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def evaluate_result(target_l5: str, raw_text: str, response: dict[str, Any], confidence_threshold: float) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    events = response.get("events") or []
    if not events:
        return False, ["no_events"]

    # pass condition: at least one matched event for target + evidence_span valid + confidence threshold
    matched = False
    output_tokens = ["신청", "신청서", "등록", "등록번호", "완료", "발송", "처리 이력", "이력", "승인"]

    for ev in events:
        l5 = ev.get("l5_activity_name", "")
        conf = float(ev.get("confidence_score", 0.0))
        span = str(ev.get("evidence_span", ""))
        l6_ctx = ev.get("l6_context", {}) if isinstance(ev.get("l6_context", {}), dict) else {}
        reason = str(l6_ctx.get("isolation_pass_reason", ""))
        mapping_status = str(ev.get("mapping_status", ""))

        # L6가 매핑되었는데 L5가 부모와 일치하지 않는 경우
        if mapping_status == "matched_l6":
            cands = l6_ctx.get("l6_candidates", []) if isinstance(l6_ctx.get("l6_candidates", []), list) else []
            parent_l5 = cands[0].get("l5") if cands else None
            if parent_l5 and l5 and parent_l5 != l5:
                reasons.append("hierarchy_mismatch")

        if target_l5 == l5:
            matched = True
        if conf < confidence_threshold:
            reasons.append("low_confidence")
        if not span or span not in raw_text:
            reasons.append("invalid_evidence_span")

        # isolation reasoning 논리성 점검
        claims_pass = any(k in reason for k in ["독립 산출물", "통과", "확인"])
        has_output_signal = any(tok in span for tok in output_tokens) or any(tok in raw_text for tok in output_tokens)
        if claims_pass and not has_output_signal:
            reasons.append("invalid_isolation_reason")

    if not matched:
        reasons.append("wrong_l5_mapping")

    return len(reasons) == 0, sorted(set(reasons))


def run_loop(base_url: str, duration_hours: float, interval_sec: float, max_iterations: int, threshold: float):
    l5_pool = load_l5_pool()
    start = time.time()
    deadline = start + duration_hours * 3600 if duration_hours > 0 else None

    total = 0
    passed = 0
    failure_counter = Counter()

    while True:
        if deadline and time.time() > deadline:
            break
        if max_iterations > 0 and total >= max_iterations:
            break

        total += 1
        target_l5 = random.choice(l5_pool)
        text = asyncio.run(generate_noisy_text_with_llm(target_l5))
        if not text:
            text = fallback_noisy_text(target_l5)

        ref_dt = datetime.now().astimezone().isoformat()
        payload = {
            "raw_text": text,
            "source_type": random.choice(["interview_note", "er_log", "discipline_review", "doc"]),
            "reference_datetime": ref_dt,
            "context": {"case_id": f"SYN-{total:06d}"},
            "options": {"low_confidence_threshold": threshold, "top_k_candidates": 3},
        }

        status_code = 0
        body: dict[str, Any] = {}
        try:
            r = requests.post(f"{base_url}/api/events/extract", json=payload, timeout=30)
            status_code = r.status_code
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
        except Exception as e:
            body = {"error": str(e)}

        ok = False
        reasons: list[str] = []
        if status_code == 200 and isinstance(body, dict):
            ok, reasons = evaluate_result(target_l5, text, body, threshold)

            # trace reconstruction validation (3+ steps)
            try:
                tr = requests.get(f"{base_url}/api/events/trace/{payload['context']['case_id']}", timeout=20)
                if tr.status_code == 200:
                    t = tr.json()
                    if len(t.get("events", [])) < 3:
                        reasons.append("trace_too_short")
                    if len(t.get("transition_times", [])) < 2:
                        reasons.append("trace_transition_missing")
                else:
                    reasons.append("trace_api_error")
            except Exception:
                reasons.append("trace_api_error")

            ok = len(reasons) == 0
        else:
            reasons = [f"api_error_{status_code}"]

        if ok:
            passed += 1
        else:
            for reason in reasons:
                failure_counter[reason] += 1

        # hard case archiving 조건
        low_conf_hit = False
        for ev in (body.get("events") if isinstance(body, dict) else []) or []:
            try:
                if float(ev.get("confidence_score", 0.0)) < 0.7:
                    low_conf_hit = True
                    break
            except Exception:
                pass

        if (not ok) or low_conf_hit:
            append_jsonl(
                HARD_CASES_PATH,
                {
                    "ts": datetime.now().astimezone().isoformat(),
                    "iteration": total,
                    "target_l5": target_l5,
                    "request": payload,
                    "response_status": status_code,
                    "response": body,
                    "reasons": reasons,
                },
            )

        if total % 10 == 0:
            acc = passed / total if total else 0.0
            print(f"[synthetic-loop] total={total} pass={passed} acc={acc:.3f} top_failures={failure_counter.most_common(5)}")

            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(
                json.dumps(
                    {
                        "total": total,
                        "passed": passed,
                        "accuracy": acc,
                        "top_failures": failure_counter.most_common(10),
                        "updated_at": datetime.now().astimezone().isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        time.sleep(max(0.1, interval_sec))

    acc = passed / total if total else 0.0
    summary = {
        "total": total,
        "passed": passed,
        "accuracy": acc,
        "top_failures": failure_counter.most_common(10),
        "hard_cases_path": str(HARD_CASES_PATH),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def run_recruitment_scenarios(base_url: str, sets: int = 100) -> dict[str, Any]:
    """채용 3단계 유기 시나리오(공고->서류심사->면접예약) 복구율 측정."""
    recovered = 0
    errors = Counter()

    for i in range(1, sets + 1):
        case_id = f"REC-SCEN-{i:04d}"
        ref = datetime.now().astimezone().isoformat()
        steps = [
            "어제 09:00 채용 공고를 등록하고 공고 게시를 완료했습니다.",
            "어제 10:00 지원서 서류심사 결과표를 확정했습니다.",
            "어제 11:00 면접 일정표를 작성하고 예약 완료 메일을 발송했습니다.",
        ]

        ok_all = True
        for txt in steps:
            payload = {
                "raw_text": txt,
                "source_type": "doc",
                "reference_datetime": ref,
                "context": {"case_id": case_id},
            }
            try:
                r = requests.post(f"{base_url}/api/events/extract", json=payload, timeout=30)
                if r.status_code != 200:
                    ok_all = False
                    errors[f"extract_{r.status_code}"] += 1
            except Exception:
                ok_all = False
                errors["extract_exception"] += 1

        try:
            tr = requests.get(f"{base_url}/api/events/trace/{case_id}", timeout=30)
            if tr.status_code != 200:
                ok_all = False
                errors[f"trace_{tr.status_code}"] += 1
            else:
                data = tr.json()
                if len(data.get("events", [])) < 3:
                    ok_all = False
                    errors["trace_short"] += 1
                if len(data.get("transition_times", [])) < 2:
                    ok_all = False
                    errors["transition_short"] += 1
        except Exception:
            ok_all = False
            errors["trace_exception"] += 1

        if ok_all:
            recovered += 1

    rate = recovered / sets if sets else 0.0
    result = {
        "scenario": "recruitment_3step",
        "sets": sets,
        "recovered": recovered,
        "trace_recovery_rate": rate,
        "errors": errors.most_common(10),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--duration-hours", type=float, default=24.0, help="0이면 무기한")
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--max-iterations", type=int, default=0, help="0이면 제한 없음")
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--run-recruitment-scenarios", action="store_true")
    parser.add_argument("--scenario-sets", type=int, default=100)
    args = parser.parse_args()

    if args.run_recruitment_scenarios:
        run_recruitment_scenarios(args.base_url, args.scenario_sets)
        return

    run_loop(
        base_url=args.base_url,
        duration_hours=args.duration_hours,
        interval_sec=args.interval_sec,
        max_iterations=args.max_iterations,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
