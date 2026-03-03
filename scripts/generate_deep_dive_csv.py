import csv

# 완전히 쪼개진 TO-BE 데이터를 표현하기 위한 MOCK 데이터
# 기존 1개의 L5가 여러 개의 TO-BE L5로 쪼개지고, 기존 1개의 L6가 여러 개의 TO-BE L6로 잘게 분해됨을 보여줍니다.

DEEP_DIVE_MOCK_DATA = [
    # AS-IS: 입사 전 O/T 진행 -> TO-BE 4개 단위로 쪼개짐
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 O/T 진행",
        "to_be_l5": "입사 전 O/T 운영", "to_be_l6": "입사 대상자 명단 확정",
        "strategy": "HR", "reason": "최종 합격자 중 입사 포기자 등을 반영한 최종 명단 확정 의사결정"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 O/T 진행",
        "to_be_l5": "입사 전 O/T 운영", "to_be_l6": "O/T 일정 및 방식 확정",
        "strategy": "HR", "reason": "대상자 규모에 따른 장소/온라인 여부 등 기획/의사결정"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 O/T 진행",
        "to_be_l5": "입사 전 O/T 운영", "to_be_l6": "O/T 참석 안내 메일 발송",
        "strategy": "Digital Worker", "reason": "명단과 일정 템플릿에 따른 대량/반복 메일 발송"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 O/T 진행",
        "to_be_l5": "입사 전 O/T 운영", "to_be_l6": "O/T 출석 결과 취합",
        "strategy": "Digital Worker", "reason": "시스템/Zoom 등을 통한 기계적인 출석 로그 다운로드 및 취합"
    },

    # AS-IS: 입사절차 안내(입사자) -> TO-BE 3개 단위로 쪼개짐
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사절차 안내(입사자)",
        "to_be_l5": "입사 구비서류 안내 및 수합", "to_be_l6": "입사 구비서류 목록 확정",
        "strategy": "HR", "reason": "경력/신입/직군별 필요한 구비서류 기준 설정"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사절차 안내(입사자)",
        "to_be_l5": "입사 구비서류 안내 및 수합", "to_be_l6": "입사 안내 패키지 발송",
        "strategy": "Digital Worker", "reason": "표준화된 서류 양식 및 작성 가이드 일괄 메일/카톡 발송"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사절차 안내(입사자)",
        "to_be_l5": "입사 구비서류 안내 및 수합", "to_be_l6": "입사 증빙서류 육안 대조 완료",
        "strategy": "SSC", "reason": "주민등록등본, 학위증명서 등 실물/이미지 서류의 육안 진위여부 패키지 대조"
    },

    # AS-IS: 입사 전 준비 -> TO-BE L5(기기 및 계정 지급) 분리 및 쪼개짐
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 준비",
        "to_be_l5": "IT기기 및 계정 지급", "to_be_l6": "사번 및 그룹웨어 계정 생성",
        "strategy": "Digital Worker", "reason": "HR 마스터 데이터 기반의 자동화된 IT 계정 프로비저닝"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 준비",
        "to_be_l5": "IT기기 및 계정 지급", "to_be_l6": "지급용 IT기기 세팅 완료",
        "strategy": "SSC", "reason": "노트북 포맷, 보안프로그램 설치 등 물리적인 IT기기 세팅"
    },
    {
        "as_is_l5": "입사 및 온보딩", "as_is_l6": "입사 전 준비",
        "to_be_l5": "웰컴키트 지급", "to_be_l6": "웰컴키트 실물 포장 및 택배 발송",
        "strategy": "SSC", "reason": "단순 물류/포장 작업이므로 해당 L5 전체를 통으로 SSC 이관"
    }
]

def generate_deep_dive_csv():
    headers = [
        "[AS-IS] L5", "[AS-IS] L6", 
        "[TO-BE] L5", "[TO-BE] L6", 
        "추천 주체", "전략 사유"
    ]
    
    with open('FINAL/hr_cleansing_deep_dive_sample.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in DEEP_DIVE_MOCK_DATA:
            writer.writerow({
                "[AS-IS] L5": row["as_is_l5"],
                "[AS-IS] L6": row["as_is_l6"],
                "[TO-BE] L5": row["to_be_l5"],
                "[TO-BE] L6": row["to_be_l6"],
                "추천 주체": row["strategy"],
                "전략 사유": row["reason"]
            })
            
    print("심화 분해 CSV 생성 완료: FINAL/hr_cleansing_deep_dive_sample.csv")

if __name__ == "__main__":
    generate_deep_dive_csv()
