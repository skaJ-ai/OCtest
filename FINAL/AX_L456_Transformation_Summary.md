# HR L4~L6 전환 요약 (AS-IS → TO-BE)

## 1) AS-IS 기준 (realdata.ts)
- 기준 정의: 행위(Action) 중심 L6 activity
- L4 개수: **63**
- L5 개수: **246**
- L6(행) 개수: **539**

## 2) TO-BE 기준 (v8.x 최종)
- 기준 정의: 결과 상태(Status) 중심 L6 (목적어+완료/확정/발행/등록)
- L4 개수: **63**
- L5 개수: **225**
- L6(행) 개수: **976**

## 3) 변화 포인트
- L6를 시퀀스 기반으로 재설계하여 프로세스 마디를 명확화
- Cadence(상시/수시/연간)를 명칭에서 분리해 속성화
- 각 최종 L6에 Activity_ID를 부여하여 의존관계(pre_dependency) 추적 가능
- 비교 CSV에서 AS-IS 1건이 TO-BE 다건으로 분해된 경우 반복 표기하여 추적성 확보

## 4) 산출물
- 요약 문서: `REPORTS/AX_L456_Transformation_Summary.md`
- 행 단위 비교: `exports/hr_l6_comparison_report_for_team.csv`
