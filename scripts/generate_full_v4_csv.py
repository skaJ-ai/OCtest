import csv

# 제미나이 심층 추론 v4.0 (통합 채용/파편화된 환경 반영)
# [대전제] 1:1 매핑 금지, 시스템 중립적 용어, 비즈니스 마일스톤 중심

FINAL_DATA_V4 = [
    # ----------------------------------------------------
    # 도메인: 채용 (신입/경력/임원 통합)
    # ----------------------------------------------------
    {"l3": "채용", "l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "전체 채용규모 산정",
     "l5_to_be": "채용 수요 조사", "l6_to_be": "전년도 전형별 채용 실적 리포트 추출", "strategy": "Digital Worker", "reason": "시스템 리포트 기반 기초 데이터 확보"},
    {"l3": "채용", "l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "전체 채용규모 산정",
     "l5_to_be": "채용 전략 수립", "l6_to_be": "사업부별 인력 충원 가이드라인 확정", "strategy": "HR", "reason": "경영 목표에 따른 정성적 전략 수립"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l5_to_be": "지원서 접수 및 필터링", "l6_to_be": "결격 사유(학위/병역 등) 자동 필터링 명단 추출", "strategy": "Digital Worker", "reason": "규칙 기반 시스템 필터링"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l5_to_be": "서류 평가 운영", "l6_to_be": "평가 대상자 이력서 및 포트폴리오 팩 취합", "strategy": "Digital Worker", "reason": "시스템 내 산재된 서류를 평가용으로 묶음 작업"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l5_to_be": "서류 평가 운영", "l6_to_be": "서류 전형 평가 점수표 확정", "strategy": "HR", "reason": "정성적 역량 검토 및 합불 판정"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "서류 검토 결과안내",
     "l5_to_be": "서류 평가 운영", "l6_to_be": "서류 전형 결과(합/불) 안내문 발송", "strategy": "Digital Worker", "reason": "확정 명단 대상 시스템 자동 발송"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접일정 조율",
     "l5_to_be": "면접 일정 관리", "l6_to_be": "면접관 및 후보자 가능 시간대 취합", "strategy": "Digital Worker", "reason": "일정 조율 도구 또는 메일 기반 데이터 수집"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접일정 조율",
     "l5_to_be": "면접 일정 관리", "l6_to_be": "최종 면접 타임테이블 확정", "strategy": "HR", "reason": "복잡한 일정 충돌 및 우선순위 조율"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접 운영",
     "l5_to_be": "면접 실행 및 지원", "l6_to_be": "오프라인 면접장 다과 및 안내문 세팅 패키지", "strategy": "SSC", "reason": "현장 물리적 서비스 통이관"},
    {"l3": "채용", "l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접 운영",
     "l5_to_be": "면접 실행 및 지원", "l6_to_be": "면접 불참자 발생 시 긴급 조치 확정", "strategy": "HR", "reason": "현장 돌발 상황에 대한 즉각적 판단"},

    # ----------------------------------------------------
    # 도메인: 인력운영
    # ----------------------------------------------------
    {"l3": "인력운영", "l4": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부문(부서별) J/P 부서 수요 취합",
     "l5_to_be": "J/P(Job Posting) 기획", "l6_to_be": "조직별 결원 및 충원 필요성 리포트 추출", "strategy": "Digital Worker", "reason": "인사 DB 연동 현황 파악"},
    {"l3": "인력운영", "l4": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부문(부서별) J/P 부서 수요 취합",
     "l5_to_be": "J/P(Job Posting) 기획", "l6_to_be": "J/P 오픈 대상 포지션 및 자격 요건 확정", "strategy": "HR", "reason": "전사 인력 효율성을 고려한 의사결정"},
    {"l3": "인력운영", "l4": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "전배발령",
     "l5_to_be": "J/P 사후 관리", "l6_to_be": "전출/전입 부서장 간 실이동 일정 합의서 확정", "strategy": "HR", "reason": "현업 간의 민감한 인력 인도 시점 조율"},
    {"l3": "인력운영", "l4": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "전배발령",
     "l5_to_be": "J/P 사후 관리", "l6_to_be": "최종 발령 데이터 인사 시스템 등록", "strategy": "Digital Worker", "reason": "확정 데이터의 기계적 적재"},
    {"l3": "인력운영", "l4": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 적정성 및 일정, 서류 검토",
     "l5_to_be": "휴직 접수 및 심사", "l6_to_be": "휴직 증빙 서류(진단서 등) 원본 대조", "strategy": "SSC", "reason": "실물 서류의 진위여부 육안 대조 패키지"},
    {"l3": "인력운영", "l4": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 적정성 및 일정, 서류 검토",
     "l5_to_be": "휴직 접수 및 심사", "l6_to_be": "휴직 대상자 적격성 심사 결과 확정", "strategy": "HR", "reason": "규정 준수 여부 및 예외 승인 책임"},

    # ----------------------------------------------------
    # 도메인: 총무
    # ----------------------------------------------------
    {"l3": "총무", "l4": "사내 인프라 관리", "l5_as_is": "비품 관리", "l6_as_is": "비품 관리 요청 접수 확정",
     "l5_to_be": "비품 보급 관리", "l6_to_be": "비품 신청 내역 시스템 취합", "strategy": "Digital Worker", "reason": "자체 시스템/메일 신청 데이터 목록화"},
    {"l3": "총무", "l4": "사내 인프라 관리", "l5_as_is": "비품 관리", "l6_as_is": "비품 관리 현장 조치 발송",
     "l5_to_be": "비품 보급 관리", "l6_to_be": "비품 실물 배송 및 수령 확인 패키지", "strategy": "SSC", "reason": "물리적 배송 및 현장 대응 업무"},
]

def generate_v4_csv():
    headers = ['[AS-IS] L3', '[AS-IS] L4', '[AS-IS] L5', '[AS-IS] L6', 
               '[TO-BE] L3', '[TO-BE] L4', '[TO-BE] L5', '[TO-BE] L6', 
               '추천 주체', '전략 사유']
    with open('FINAL/hr_cleansing_smart_full_v4.0.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in FINAL_DATA_V4:
            writer.writerow({
                '[AS-IS] L3': row['l3'], '[AS-IS] L4': row['l4'], '[AS-IS] L5': row['l5_as_is'], '[AS-IS] L6': row['l6_as_is'],
                '[TO-BE] L3': row['l3'], '[TO-BE] L4': row['l4'], '[TO-BE] L5': row['l5_to_be'], '[TO-BE] L6': row['l6_to_be'],
                '추천 주체': row['strategy'], '전략 사유': row['reason']
            })
    print('Final v4.0 CSV 생성 완료')

if __name__ == "__main__":
    generate_v4_csv()
