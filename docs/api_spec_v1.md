# API Spec v1 — Event Extraction MVP

작성일: 2026-03-01  
버전: v1.0 (MVP)

## 1) Endpoint

- **Method**: `POST`
- **Path**: `/api/events/extract`
- **목적**: 비정형 텍스트 로그를 정형 이벤트 리스트로 변환

---

## 2) Request Schema

### Content-Type
`application/json`

### Body

```json
{
  "raw_text": "2026-02-28 14:20 면담 진행. A가 B에게 경고 조치 필요 의견 전달...",
  "source_type": "interview_note",
  "context": {
    "case_id": "ER-2026-00012",
    "l3_hint": "노사",
    "l4_hint": "사건사고 관리",
    "language": "ko-KR",
    "timezone": "Asia/Seoul"
  },
  "options": {
    "low_confidence_threshold": 0.75,
    "top_k_candidates": 3
  }
}
```

### Field Definition

- `raw_text` (string, required): 비정형 원문 텍스트
- `source_type` (string, required): 원천 데이터 유형
  - 예: `interview_note`, `er_log`, `discipline_review`, `email`, `doc`
- `context` (object, optional): 케이스/도메인 힌트
  - `case_id` (string, optional)
  - `l3_hint` (string, optional)
  - `l4_hint` (string, optional)
  - `language` (string, optional, default `ko-KR`)
  - `timezone` (string, optional, default `Asia/Seoul`)
- `options` (object, optional)
  - `low_confidence_threshold` (number, optional, default `0.75`)
  - `top_k_candidates` (integer, optional, default `3`)

---

## 3) Response Schema

```json
{
  "case_id": "ER-2026-00012",
  "source_type": "interview_note",
  "events": [
    {
      "event_id": "evt_01",
      "l5_activity_name": "면담기록/요약",
      "timestamp": "2026-02-28T14:20:00+09:00",
      "actor": "인사담당자A",
      "confidence_score": 0.86,
      "evidence_span": "2026-02-28 14:20 면담 진행",
      "taxonomy_status": "matched",
      "taxonomy_candidates": [
        { "l5": "면담기록/요약", "score": 0.91 },
        { "l5": "징계항목 제안", "score": 0.52 }
      ],
      "human_review_required": false
    }
  ],
  "summary": {
    "event_count": 1,
    "low_confidence_count": 0,
    "unclassified_count": 0
  }
}
```

### Event Required Fields (MVP 필수)
각 이벤트는 반드시 아래 필드를 포함해야 합니다.

- `l5_activity_name` (string)
- `timestamp` (string, ISO-8601 / 추론 가능)
- `actor` (string)
- `confidence_score` (number, 0.0~1.0)
- `evidence_span` (string, 원문 근거 구절)

### Taxonomy Guardrail 관련 필드

- `taxonomy_status` (enum):
  - `matched`: 기존 L5와 정합 매칭 성공
  - `suggested`: 정확 일치 없음, 유사 L5 제안
  - `unclassified`: 분류 불가
- `taxonomy_candidates` (array): L5 후보와 점수
- `human_review_required` (boolean): HITL 검토 필요 플래그

---

## 4) Error Response

### 400 Bad Request
```json
{
  "error": "INVALID_REQUEST",
  "message": "raw_text is required"
}
```

### 422 Unprocessable Entity
```json
{
  "error": "PARSING_FAILED",
  "message": "LLM parsing failed and fallback parser returned no events"
}
```

### 500 Internal Server Error
```json
{
  "error": "INTERNAL_ERROR",
  "message": "Unexpected server error"
}
```

---

## 5) Taxonomy Guardrail 설계

## 5-1. 목표
추출 이벤트를 반드시 `docs/hr_domain_knowledge.json`의 기존 L5 목록 중 하나로 매핑합니다.

## 5-2. 동작 단계
1. **Taxonomy 로드**: L3/L4/L5를 메모리로 로드
2. **LLM 추출**: 원문에서 이벤트 후보 생성 (`activity_raw`, `timestamp`, `actor`, `evidence_span`, `confidence`)
3. **정합 매핑**:
   - Exact match
   - 정규화 후 부분/토큰 유사 매칭
   - 필요 시 LLM 재판정(Few-shot) 또는 임베딩 유사도
4. **가드레일 판정**:
   - 임계치 이상: `matched`
   - 임계치 미만이나 후보 존재: `suggested`
   - 후보 부재: `unclassified`
5. **HITL 플래그**:
   - `confidence_score < threshold`
   - `taxonomy_status != matched`
   - `timestamp`/`actor` 누락

## 5-3. 예외 처리
- 새로운 미정의 활동 감지 시:
  1) top-k 유사 L5 제시 (`taxonomy_candidates`)
  2) `l5_activity_name = "Unclassified"`
  3) `human_review_required = true`

---

## 6) Evidence Span 품질 원칙

- `evidence_span`은 반드시 `raw_text`에서 **직접 발췌한 부분 문자열**이어야 함
- 요약 문장만 넣고 근거 원문이 없는 경우 invalid
- 권장 길이: 10~200자
- 한 이벤트당 최소 1개 증거 구절 필수
