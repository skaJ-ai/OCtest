import json
import csv
import re
import traceback

# realdata.ts의 내용을 파싱하기 위해 간단한 정규식을 사용합니다 (실제로는 ast 또는 js2py 등을 쓰는 것이 좋으나 빠른 처리를 위해)
# 사용자 프롬프트에 제공된 realdata.ts 원본 문자열의 일부를 하드코딩하여 사용하겠습니다. (채용 도메인 중 일부)

# 우리가 처리할 타겟 L5 목록 (채용 관련)
TARGET_L5 = [
    {
        "l3": "채용", "l4": "채용 후속조치", "l5": "입사 및 온보딩",
        "l6_activities": [
            "입사 전 O/T 진행", "입사절차 안내(입사자)", "입사발령(Workday)", 
            "입사 전 준비", "입문교육 진행", "멘토링/면담 진행", "비용 지급/관리"
        ]
    },
    {
        "l3": "인력운영", "l4": "휴복직", "l5": "휴직",
        "l6_activities": [
            "휴직 신청", "휴직 면담", "휴직 적정성 및 일정, 서류 검토",
            "휴직원 작성 및 신청", "휴직 행정사항 안내", "휴직 연장 신청"
        ]
    }
]

# 위에서 정의했던 시스템 프롬프트 내용
SYSTEM_PROMPT = """
당신은 글로벌 최고 수준의 HR 프로세스 엔지니어이자 조직 설계 전문가(Organization Design Expert)입니다.
당신의 임무는 제공된 HR 담당자의 기존 단위 업무(L5)와 과거 작업 단계(L6)를 확인하고, 
이것을 다음 작업자나 AI에게 인수인계(Handoff) 가능한 '독립된 실물 결과물(L6)' 단위로 재설계하는 것입니다.

이 과정에서 Zero-based Redesign(ZBR) 철학을 적용하여, 과거의 불필요한 관행은 제거(Eliminate)하고, 
단순 반복 업무는 Digital Worker에게 이관(DW)하며, 물리적 작업이 수반되는 L5는 통으로 SSC로 넘깁니다. 
고부가가치 업무는 HR이 집중하게 합니다.

### [원칙 1] L6 명칭 표준화 원칙 (A+B 형태)
L6 명칭은 반드시 `[구체적 명사(A)] + [표준 상태 동사(B)]`의 형태여야 합니다.

**A. 구체적 명사 (실물 중심)**
- ❌ 금지어: 데이터, 내역, 원천 데이터, 오류 데이터, 정합성, 초안, 수정본, 시스템 로그
- ✅ 권장어: 지원자 명단, 대상자 풀, 기안서, 수급 계획서, 평가표, 선발 기준, 안내 메일, 합격 통보 메시지 등 실물/결과물

**B. 표준 상태 동사 (마일스톤 중심)**
- ❌ 금지어: 진행, 수집, 점검, 보정
- ✅ 허용 동사 풀:
  - `확정`: 내부 의사결정 완료 및 버전 고정 (예: 선발 기준 확정)
  - `완료`: 기안서, 문서 등의 작성 완료 (예: 기안서 승인 완료)
  - `발송` / `발행` / `배포`: 외부/타조직 안내 (예: 안내 메일 발송, 공고문 발행)
  - `등록` / `저장`: 시스템 적재 (예: 신규 입사자 정보 등록)

### [원칙 2] 클렌징 전략 (Execution Strategy) 판정 기준 (To-Be 추천 주체)
각 L6마다 아래 4가지 중 하나의 실행 주체를 반드시 할당하세요.
1. **HR**: 대면 협상, 예외적/정성적 의사결정, 전략 기획, 기준 수립이 필요한 고부가가치 업무.
2. **Digital Worker**: [우선적으로 최대한 할당할 것] 규칙 기반 데이터 대조/필터링, 대량 발송, 표준화 챗봇 응대.
3. **SSC**: [극도로 보수적 할당, '통이관' 원칙] 파편적 단위 이관 지양. AI가 불가능한 물리적 작업(포장, 배송)이나 대량 육안 대조가 필요한 '해당 L5(단위 업무) 전체 흐름'을 묶어서 넘길 때만 사용.
4. **Eliminate**: 불필요한 중간 보고, 중복 취합, 관행적 업무. 과감히 없앱니다.

---

### 입력 데이터 형식
- Domain(L3): 채용
- Process(L4): 채용 후속조치
- Activity(L5): 입사 및 온보딩
- 기존 L6 목록: ["입사 전 O/T 진행", "입사절차 안내(입사자)", "입사발령(Workday)", "입사 전 준비", "입문교육 진행", "멘토링/면담 진행", "비용 지급/관리"]

### 출력 포맷 (반드시 JSON Array 형태만 출력할 것)
[
  {
    "TO_BE_L6": "신규 입사자 명단 추출 완료",
    "Strategy": "Digital Worker",
    "Reason": "정해진 조건에 따라 시스템에서 대상자 명단을 추출하는 단순 반복 작업이므로 Digital Worker가 수행."
  },
  ...
]
"""

# 시간 관계상, 실제 API를 태우기 전에 하드코딩된 '모범 답안' 로직으로 LLM의 출력을 흉내내어 CSV를 만들어보겠습니다.
# (OpenAI API 키 세팅 문제와 응답 지연을 방지하고 즉각적인 결과물을 보기 위함)

MOCK_LLM_RESPONSES = {
    "입사 및 온보딩": [
        {"TO_BE_L6": "입사 대상자 명단 확정", "Strategy": "HR", "Reason": "입사 대상자에 대한 최종 예외사항 점검 및 명단 확정은 HR의 판단 필요."},
        {"TO_BE_L6": "온보딩 안내 메일 발송", "Strategy": "Digital Worker", "Reason": "대상자 명단을 기반으로 한 단순 반복적 메일 발송 업무."},
        {"TO_BE_L6": "입사자 정보 ERP 등록", "Strategy": "Digital Worker", "Reason": "입사자 정보를 시스템에 업로드하는 규칙 기반 작업."},
        {"TO_BE_L6": "웰컴키트 실물 포장 및 발송", "Strategy": "SSC", "Reason": "물리적 포장 및 택배 발송이 포함된 업무 패키지."},
        {"TO_BE_L6": "온보딩 교육 커리큘럼 확정", "Strategy": "HR", "Reason": "교육 내용과 방향성을 설정하는 기획 업무."},
        {"TO_BE_L6": "중간 점검 현황표 작성", "Strategy": "Eliminate", "Reason": "시스템상 대시보드로 실시간 확인 가능하므로 별도 수기 작성 제거."}
    ],
    "휴직": [
        {"TO_BE_L6": "휴직 요건 및 잔여일수 안내 발송", "Strategy": "Digital Worker", "Reason": "단순 규정 안내 및 잔여일수 조회는 챗봇/DW가 담당 가능."},
        {"TO_BE_L6": "휴직 신청서 접수 완료", "Strategy": "Digital Worker", "Reason": "시스템을 통한 자동 접수 및 분류."},
        {"TO_BE_L6": "휴직 예외사항 면담 결과 확정", "Strategy": "HR", "Reason": "규정을 벗어난 특이 케이스에 대한 정성적 판단 및 면담 진행."},
        {"TO_BE_L6": "휴직 증빙 서류 육안 검증 완료", "Strategy": "SSC", "Reason": "진단서 등 육안으로 진위여부를 확인해야 하는 서류 대조 업무 패키지."},
        {"TO_BE_L6": "휴직 발령 ERP 등록", "Strategy": "Digital Worker", "Reason": "검증 완료된 데이터에 대한 기계적인 시스템 입력."}
    ]
}

def generate_csv():
    output_rows = []
    headers = [
        "[AS-IS] L3", "[AS-IS] L4", "[AS-IS] L5", "[AS-IS] L6", 
        "[TO-BE] L3", "[TO-BE] L4", "[TO-BE] L5", "[TO-BE] L6", 
        "추천 주체", "전략 사유"
    ]
    
    for task in TARGET_L5:
        l3 = task['l3']
        l4 = task['l4']
        l5 = task['l5']
        as_is_l6_list = task['l6_activities']
        
        # MOCK 데이터 가져오기
        to_be_list = MOCK_LLM_RESPONSES.get(l5, [])
        
        # row 매핑 (보통 AS-IS와 TO-BE 개수가 다름)
        # 비교를 위해 가장 긴 리스트 기준으로 row를 만듦
        max_len = max(len(as_is_l6_list), len(to_be_list))
        
        for i in range(max_len):
            as_is_l6 = as_is_l6_list[i] if i < len(as_is_l6_list) else ""
            
            if i < len(to_be_list):
                to_be_l6 = to_be_list[i]['TO_BE_L6']
                strategy = to_be_list[i]['Strategy']
                reason = to_be_list[i]['Reason']
            else:
                to_be_l6 = ""
                strategy = ""
                reason = ""
                
            row = {
                "[AS-IS] L3": l3,
                "[AS-IS] L4": l4,
                "[AS-IS] L5": l5,
                "[AS-IS] L6": as_is_l6,
                "[TO-BE] L3": l3,
                "[TO-BE] L4": l4,
                "[TO-BE] L5": l5,
                "[TO-BE] L6": to_be_l6,
                "추천 주체": strategy,
                "전략 사유": reason
            }
            output_rows.append(row)
            
    with open('FINAL/hr_cleansing_sample_v1.0.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)
        
    print("CSV 생성 완료: FINAL/hr_cleansing_sample_v1.0.csv")

if __name__ == "__main__":
    generate_csv()
