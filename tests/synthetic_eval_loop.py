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


async def generate_noisy_text_with_llm(target_l5: str) -> str:
    """LLM 생성 시도. 실패하면 빈 문자열 반환."""
    try:
        from backend.llm_service import call_llm  # type: ignore

        prompt = f"""
당신은 HR 로그 생성기입니다.
목표 L5 활동: {target_l5}

아래 조건으로 한국어 비정형 텍스트를 3~5문장 생성하세요.
- 대화체/보고서체 혼합
- 노이즈 포함(오타, 중복표현, 주어 생략 일부)
- 상대 시간 표현 포함(어제, 오늘 오전, 방금 등)
- 목표 L5와 관련 행위가 반드시 1회 이상 나타나야 함

JSON으로만 응답:
{{"raw_text":"..."}}
""".strip()
        result = await call_llm("텍스트 생성기", prompt, allow_text_fallback=True)
        if isinstance(result, dict):
            txt = result.get("raw_text") or result.get("speech") or result.get("message") or ""
            return str(txt).strip()
        return ""
    except Exception:
        return ""


def fallback_noisy_text(target_l5: str) -> str:
    templates = [
        f"어제 오후에 {target_l5} 관련해서 급히 메모 남깁니다. 담당자A가 먼저 확인했고, 세부는 아직 누락됐어요. 오늘 오전 다시 정리 예정.",
        f"방금 팀장 통화했고 {target_l5} 건은 처리 방향만 공유됐습니다. 정확한 시각은 어제쯤으로 보이고, 기록이 중간에 끊겼어요.",
        f"회의록 일부: {target_l5} 진행 필요 의견 있음. 담당이 누군지 애매하고, 오늘 아침에 추가 확인하기로 했습니다.",
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
    for ev in events:
        l5 = ev.get("l5_activity_name", "")
        conf = float(ev.get("confidence_score", 0.0))
        span = str(ev.get("evidence_span", ""))

        if target_l5 == l5:
            matched = True
        if conf < confidence_threshold:
            reasons.append("low_confidence")
        if not span or span not in raw_text:
            reasons.append("invalid_evidence_span")

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--duration-hours", type=float, default=24.0, help="0이면 무기한")
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--max-iterations", type=int, default=0, help="0이면 제한 없음")
    parser.add_argument("--threshold", type=float, default=0.75)
    args = parser.parse_args()

    run_loop(
        base_url=args.base_url,
        duration_hours=args.duration_hours,
        interval_sec=args.interval_sec,
        max_iterations=args.max_iterations,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
