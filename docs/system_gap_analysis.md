# HR 비정형 데이터 기반 프로세스 마이닝 갭 분석 및 AX 아키텍처 개선안

작성일: 2026-02-28
대상 저장소: process-coaching

## 1) 분석 범위
- 기준 마스터 데이터: `docs/hr_domain_knowledge.json`
- 코드 분석 범위: `backend/*`, `frontend/src/*`
- 목표: L5 단위업무 중 비정형 데이터 처리 항목의 디지털 발자국(event log) 변환 지원 여부 진단

---

## 2) 비정형 데이터 처리 우선 L5 식별

### A. 노사 > 사건사고 관리
- 면담기록/요약
- 유사사례 및 판례 확인
- 징계항목 제안

### B. 노사 > ER
- 직장내괴롭힘
- 마음건강
- 동행파악

### C. 임원조직 > 인력운영
- 임원 피드백 면담

### D. 해외인사 > M&A
- (실사)결과 분석
- (실사)시사점 도출
- (PMI)BP 분석

### E. 채용 > 선발전형
- 면접
- 자격 검증(문서/증빙 검토 기반)

위 항목은 텍스트 문서, 면담 메모, 사례 검색 결과, 판단 근거 등 비정형 입력이 핵심이므로
직접적인 프로세스 마이닝용 이벤트 스키마 변환이 필요합니다.

---

## 3) 현재 시스템 진단 (코드 근거)

## 3-1. 현재 강점
1. **L3-L4-L5 컨텍스트 주입 기능 존재**
   - `backend/l345_reference.py`의 `L345_TREE`, `get_l345_context()`
   - `backend/app.py`에서 `/api/chat`, `/api/review`, `/api/pdd-insights`에 L345 블록 주입
2. **플로우 노드/엣지 중심의 코칭 구조 구현**
   - `backend/schemas.py`의 `FlowNode`, `FlowEdge`
   - `backend/flow_services.py`의 `describe_flow()`, `mock_review()`
3. **LLM/Rules/Mock 체인으로 사용자 코칭 기능 제공**
   - `backend/chat_orchestrator.py`

## 3-2. 핵심 갭

### Gap-1) 비정형 데이터 수집/정규화 파이프라인 부재
- 텍스트 문서(면담록, 판례요약, 징계 검토서)를 입력받아 구조화하는 ETL/NLP 모듈이 없음.
- 현재 로직은 **캔버스 노드/라벨 문자열**을 기준으로 코칭만 수행.

### Gap-2) 프로세스 마이닝 이벤트 로그 스키마 부재
- `case_id`, `activity`, `timestamp`, `resource`, `l3/l4/l5`, `confidence` 같은 표준 이벤트 필드 정의가 없음.
- XES/CSV/Parquet 등 마이닝 엔진 연계 포맷 내보내기 기능 없음.

### Gap-3) 증거 추적(Traceability) 부재
- 어떤 문장/문서 조각이 어떤 이벤트로 변환되었는지 provenance(근거 링크) 저장 구조 없음.
- 징계/노무처럼 설명 가능성과 감사 추적이 중요한 영역에서 리스크 큼.

### Gap-4) 도메인 지식의 이원화
- 기존 `backend/l345_reference.py` 내 하드코딩 트리와 신규 `docs/hr_domain_knowledge.json` 간 싱글소스 미정립.
- 향후 기준 불일치 가능.

### Gap-5) AX 관점의 모듈 분리 미흡
- 현재 백엔드는 코칭 API 중심 단일 계층 구조.
- 수집/추출/판정/검증/로그 적재/분석 API가 기능별로 분리되지 않음.

---

## 4) 결론: 비정형 이벤트의 디지털 발자국 변환 로직 존재 여부

**판정: 현재 저장소에는 ‘비정형 HR 이벤트 → 프로세스 마이닝 디지털 발자국’으로 변환하는 전용 로직이 사실상 없습니다.**

- 존재하는 것은 L345 참조 기반 코칭/추천 로직이며,
- 비정형 텍스트를 이벤트 로그로 정규화하는 파이프라인은 미구현 상태입니다.

---

## 5) AX 중심 모듈형 아키텍처 개선안

## 5-1. 목표 아키텍처 (모듈 분리)

1. **Domain-KB 모듈**
   - 책임: L3-L4-L5 마스터 데이터 관리
   - 소스: `docs/hr_domain_knowledge.json` 단일 소스화
   - 기능: 버전관리, 유효성 검증, 키워드 매핑 사전

2. **Evidence Ingestion 모듈**
   - 입력: 면담록, 판례요약, 징계 검토 메모, 이메일/문서 텍스트
   - 기능: 문서 수집, 전처리(PII 마스킹), 문단/문장 분할

3. **Event Extraction 모듈 (AI/NLP)**
   - 기능: 텍스트에서 이벤트 후보 추출
   - 출력(예):
     - case_id
     - activity_raw
     - actor/resource
     - occurred_at / inferred_time
     - evidence_span
     - confidence

4. **L5 Mapping & Canonicalization 모듈**
   - 기능: 추출 이벤트를 L3/L4/L5와 정합 매핑
   - 규칙: exact/semantic 매칭 + 임계치 기반 재검토 큐

5. **Process-Mining Event Store 모듈**
   - 기능: 이벤트 로그 적재/조회
   - 포맷: CSV/XES/Parquet export 지원
   - 테이블 분리: raw_event / normalized_event / mapping_audit

6. **Quality & Governance 모듈**
   - 기능: 신뢰도 임계치, human-in-the-loop 승인, 감사 추적
   - 핵심: 이벤트별 근거 문장, 모델 버전, 규칙 버전 저장

7. **Insight API 모듈**
   - 기능: 병목/재작업/리드타임/변형(variant) 분석
   - 현재 `pdd-insights`와 연계해 실제 이벤트 기반 인사이트로 고도화

## 5-2. 제안 API 초안
- `POST /api/evidence/ingest`
- `POST /api/events/extract`
- `POST /api/events/map-l5`
- `POST /api/events/validate`
- `GET /api/events/export?format=xes|csv|parquet`
- `GET /api/mining/insights?case_id=...`

## 5-3. 권장 데이터 스키마(요약)
```json
{
  "event_id": "uuid",
  "case_id": "string",
  "activity": "string",
  "l3": "string",
  "l4": "string",
  "l5": "string",
  "resource": "string",
  "timestamp": "ISO-8601",
  "source_type": "interview_note|precedent|discipline_review|email|doc",
  "evidence": {
    "doc_id": "string",
    "span": "string"
  },
  "confidence": 0.0,
  "mapping_method": "rule|embedding|llm",
  "approved": false
}
```

## 5-4. 단계별 실행 로드맵
- **Phase 1 (2주)**: Domain-KB 싱글소스화 + 이벤트 스키마/스토어 구축
- **Phase 2 (3주)**: 비정형 텍스트 추출기 + L5 매핑기 + 검증 UI
- **Phase 3 (2주)**: XES/CSV export + mining insight API 연결
- **Phase 4 (지속)**: 정밀도 개선(도메인 사전, 판례/징계 특화 프롬프트, 휴먼 피드백 루프)

---

## 6) 즉시 권장 조치
1. `backend/l345_reference.py`의 하드코딩을 `docs/hr_domain_knowledge.json` 로더로 교체
2. 비정형 고위험 L5(면담기록/요약, 판례 확인, 징계항목 제안)부터 이벤트 추출 MVP 착수
3. `pdd-insights`를 노드 라벨 기반 규칙에서 이벤트로그 기반 분석으로 전환
4. 감사 추적(provenance) 필드를 모든 추출 이벤트에 의무화
