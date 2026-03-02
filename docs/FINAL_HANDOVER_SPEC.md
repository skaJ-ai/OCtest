# FINAL HANDOVER SPEC

작성일: 2026-03-01  
대상 브랜치: `feature/api-extraction`

## 1) 추출 엔진 아키텍처

## 1-1. 계층 구조
- 기준 KB: `docs/hr_l6_apqc_master_library_v2.json`
- 계층: `L3 -> L4 -> L5 -> L6`
- 이벤트 단위 스키마 핵심 필드:
  - `event_id`
  - `event_type` (`normal`, `planned`, `rework`, `suspended`, `canceled`, `resolved`)
  - `l5_activity_name`
  - `l6_activity_name`
  - `mapping_status` (`matched_l6`, `matched_l5`, `unclassified` 등)
  - `timestamp`, `actor`, `confidence_score`, `evidence_span`

## 1-2. 처리 로직 요약
1. 비정형 텍스트 입력 (`/api/events/extract`)
2. Context Splitter로 복합 문장 분할
3. 이벤트별 `event_type` 추론(보류/반려/해결 포함)
4. L6 매핑 (taxonomy + labor anchors + contextual inheritance)
5. L6->L5 상속 매핑
6. case_id 기준 이벤트 적재(메모리 스토어)
7. Trace 집계/변이 분석/시각화 생성

---

## 2) 핵심 자산 리스트

### 2-1. 마스터 데이터
- `docs/hr_l6_apqc_master_library_v2.json`
  - 전사 L3~L5 full coverage
  - 총 370개 L6
  - 필드: `l6_id, l6_name, input, output, digital_trace, automation_potential, legacy_l6_match, improvement_note`

### 2-2. 서비스 모듈
- `app/services/taxonomy_service.py`
  - L5/L6 매핑, 유사도 계산, 앵커 기반 강제 매핑
  - 노사 전용 앵커(`LABOR_ER_ANCHORS`) 포함
- `app/services/trace_service.py`
  - case_id 이벤트 정렬/집계
  - `lead_time_sec`, `transition_times`, `variant_analysis` 계산
- `app/services/viz_service.py`
  - Mermaid 생성
  - Bottleneck/Variant/Exception 스타일 및 Legend 자동 삽입

### 2-3. API 엔드포인트
- `POST /api/events/extract`
- `GET /api/events/trace/{case_id}`
- `GET /api/viz/process-map?case_id=...`

---

## 3) 리얼 데이터 매핑 가이드 (Spaghetti L6 -> 표준 L6)

## 3-1. legacy_l6_match 활용 전략
- 현업 원문 L6 명칭/별칭을 `legacy_l6_match`로 축적
- 신규 표현 유입 시:
  1) 우선 legacy alias exact match
  2) 미스매치 시 anchor 사전 검사
  3) 마지막으로 유사도 기반 후보 제시 + human review

## 3-2. 추천 자동화 플로우
1. 스파게티 L6 문자열 수집
2. `legacy_l6_match` dict 자동 생성/업데이트
3. 배치 매핑 리포트 생성(매핑률, 미매핑 Top N)
4. 미매핑 항목만 수동 승인

---

## 4) 복구 성공률(Trace Recovery Rate) 회귀 테스트 가이드

## 4-1. 기준 지표
- 채용 3단계 시나리오 기준 목표: `>= 0.99`
- 회귀 실행:
```bash
python tests/synthetic_eval_loop.py --base-url http://127.0.0.1:8000 --run-recruitment-scenarios --scenario-sets 100
```

## 4-2. 실패 시 우선 점검
1. `trace_too_short` / `trace_transition_missing`
2. `hierarchy_mismatch`
3. `wrong_l5_mapping`
4. `invalid_isolation_reason`

## 4-3. 보호 규칙
- 예외 이벤트(`rework/suspended`)도 반드시 L6 귀속
- `unclassified_count` 급증 시 배포 차단
- Hard cases를 daily 요약으로 운영 리뷰

---

## 5) 운영 전환 체크리스트
- [x] systemd `process-coaching-test.service` 상시 가동
- [x] systemd daily summary timer (09:00 KST)
- [x] hard case 로그 경로 확인
- [x] v2 마스터 라이브러리 반영

---

## 6) 삼성 고유 명사 앵커 사전 (Sandbox Guideline)
파싱 로직에서 아래 키워드는 일반명사로 버리지 말고 우선 앵커로 처리한다.

- `S-calling` / `에스콜링`: 사내 전화(031 회선) 모바일 연동 서비스
- `두발로`: 사업장 공용 자전거 시스템
- `STEP`: Samsung Talent Exchange Program(법인 간 인력 교환)
- `My Pulse` / `마이펄스`: 조직문화 상시 서베이
- `SCI`: 조직문화 진단 프레임워크
- `Change Agent` / `CA`: 조직문화 변화리더 운영 체계
- `VP(상무)`: 임원 직급 이벤트(승격/보임) 앵커
- `사내 화물 운영`: 내부 물류/수발 프로세스
- `상주협력사`: 사업장 상주 협력사 인력/출입/안전 관리 도메인

권장 적용 순서:
1) 고유명사 exact match
2) 앵커 사전 유사어 매칭
3) legacy_l6_match 동의어 매칭
4) 의미 유사도 후보 + human review

## 7) 클로드코드 이식 시작점
- 1순위: `taxonomy_service.py` + `hr_l6_apqc_master_library_v2.1_custom.json`
- 2순위: `trace_service.py` (리드타임/변이 계산)
- 3순위: `viz_service.py` (리더 보고용 Mermaid)
- 4순위: 메인 프로젝트 스키마와 `event_type`/`mapping_status` 정합
