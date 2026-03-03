import csv

# LLM이 'SYSTEM_PROMPT_DEEP_CLEANSING'을 받고 실시간으로 쪼갰다고 가정(Mocking)한 최종 결과물 리스트입니다.
# realdata.ts의 "채용" 도메인 일부와 "인력운영" 도메인 일부를 대상으로 극한 쪼개기를 수행한 결과입니다.

AI_GENERATED_MOCK_RESULTS = [
    # ----------------------------------------------------
    # 도메인: 채용 > L4: 채용계획
    # ----------------------------------------------------
    # AS-IS L5: 채용 계획 수립(경영계획) -> TO-BE L5: 채용 계획 기획
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "전체 채용규모 산정",
     "l4_to_be": "채용계획", "l5_to_be": "채용 계획 기획", "l6_to_be": "전년도 채용 데이터 취합", "strategy": "Digital Worker", "reason": "과거 데이터베이스의 기계적 수합"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "전체 채용규모 산정",
     "l4_to_be": "채용계획", "l5_to_be": "채용 계획 기획", "l6_to_be": "전사 채용 규모 가이드라인 확정", "strategy": "HR", "reason": "경영진 및 재무팀 조율을 통한 고부가가치 의사결정"},
    
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "팀별 채용규모 확인",
     "l4_to_be": "채용계획", "l5_to_be": "부서별 수요 조사", "l6_to_be": "채용 수요 조사 양식 배포", "strategy": "Digital Worker", "reason": "템플릿 기반의 대량/반복 안내 메일 발송"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "팀별 채용규모 확인",
     "l4_to_be": "채용계획", "l5_to_be": "부서별 수요 조사", "l6_to_be": "팀별 수요 취합 결과서 작성", "strategy": "Digital Worker", "reason": "회신된 양식의 기계적 취합 및 목록화"},
    
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "충원 필요성 검토",
     "l4_to_be": "채용계획", "l5_to_be": "채용 규모 확정", "l6_to_be": "부서별 충원 타당성 검토 결과 확정", "strategy": "HR", "reason": "정성적 판단 및 부서장 면담을 통한 최종 조율"},
    
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "사업부 채용규모 확정",
     "l4_to_be": "채용계획", "l5_to_be": "채용 규모 확정", "l6_to_be": "최종 사업부 채용규모 기안서 완료", "strategy": "HR", "reason": "경영진 최종 승인을 위한 문서 작성"},

    # AS-IS L5: 직무기술서 작성 -> TO-BE L5: 직무기술서 관리
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청",
     "l4_to_be": "채용계획", "l5_to_be": "직무기술서 관리", "l6_to_be": "직무기술서 작성 요청 메일 발송", "strategy": "Digital Worker", "reason": "부서별 담당자에게 작성 요청을 일괄 발송"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청",
     "l4_to_be": "채용계획", "l5_to_be": "직무기술서 관리", "l6_to_be": "직무기술서 취합 및 내용 검수 확정", "strategy": "HR", "reason": "현업이 작성한 내용의 적절성(JD 품질) 검수"},

    # ----------------------------------------------------
    # 도메인: 채용 > L4: 인재발굴
    # ----------------------------------------------------
    # AS-IS L5: 인재 소싱 채널 선정 및 액팅
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "발굴 기준 확정",
     "l4_to_be": "인재발굴", "l5_to_be": "소싱 전략 수립", "l6_to_be": "포지션별 발굴 기준 확정", "strategy": "HR", "reason": "어떤 역량을 가진 인재를 찾을지 타겟팅하는 기획 업무"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "소싱 채널 선정",
     "l4_to_be": "인재발굴", "l5_to_be": "소싱 전략 수립", "l6_to_be": "소싱 채널(플랫폼/헤드헌터) 리스트 확정", "strategy": "HR", "reason": "비용 대비 효과를 고려한 외부 채널 선정"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 발굴",
     "l4_to_be": "인재발굴", "l5_to_be": "외부 소싱 실행", "l6_to_be": "채용 플랫폼 내 키워드 기반 후보자 추출 완료", "strategy": "Digital Worker", "reason": "정해진 키워드(JD)를 기반으로 링크드인 등에서 후보자 프로필 자동 수집"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 발굴",
     "l4_to_be": "인재발굴", "l5_to_be": "외부 소싱 실행", "l6_to_be": "콜드메일/인메일 일괄 발송", "strategy": "Digital Worker", "reason": "후보자군에 대한 기계적이고 반복적인 컨택 메시지 발송"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 풀 구축",
     "l4_to_be": "인재발굴", "l5_to_be": "인재 Pool 관리", "l6_to_be": "관심 표명 후보자 DB 등록", "strategy": "Digital Worker", "reason": "회신온 후보자들의 이력서를 채용 시스템에 자동 적재"},

    # ----------------------------------------------------
    # 도메인: 채용 > L4: 선발전형
    # ----------------------------------------------------
    # AS-IS L5: 서류심사 -> TO-BE L5: 서류 접수 및 검토
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "서류 접수 및 검토", "l6_to_be": "필수 요건(블라인드 등) 미달자 필터링", "strategy": "Digital Worker", "reason": "기본 요건 미달자를 시스템 필터링으로 자동 탈락 처리"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "서류 접수 및 검토", "l6_to_be": "HR 서류 평가 점수 확정", "strategy": "HR", "reason": "후보자의 이력과 자기소개서에 대한 HR 관점의 정성적 검토"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "현업 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "현업 평가", "l6_to_be": "서류 검토 요청 시스템 알림 발송", "strategy": "Digital Worker", "reason": "현업 면접관에게 시스템에서 자동 알림 및 리마인더 발송"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "서류 검토 결과안내",
     "l4_to_be": "선발전형", "l5_to_be": "현업 평가", "l6_to_be": "서류 합불 결과 안내 메일 발송", "strategy": "Digital Worker", "reason": "확정된 합불 명단을 기반으로 템플릿 메일 일괄 발송"},

    # ----------------------------------------------------
    # 도메인: 인력운영 > L4: 인력이동
    # ----------------------------------------------------
    # AS-IS L5: 사내 Job Posting -> 너무 거대함, 다수 L5로 분리
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부문(부서별) J/P 부서 수요 취합",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 공고", "l6_to_be": "J/P 수요 조사 양식 배포", "strategy": "Digital Worker", "reason": "수요 취합을 위한 일괄 시스템/메일 요청"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "J/P 운영 타당성 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 공고", "l6_to_be": "오픈 대상 J/P 포지션 확정", "strategy": "HR", "reason": "타 부서 전배를 오픈할 만큼 중요한 포지션인지 타당성 심사"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "Post 확정 후 J/P 실시",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 공고", "l6_to_be": "사내 게시판 J/P 공고문 등록", "strategy": "Digital Worker", "reason": "작성된 공고문의 시스템 업로드"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "지원자 지원 자격 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "근속연수/고과 등 자격 미달자 필터링", "strategy": "Digital Worker", "reason": "사내 전배 규정(최소 근속 등)에 따른 자동 필터링"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "면접평가 결과 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "면접 합격자 명단 확정", "strategy": "HR", "reason": "면접 결과를 바탕으로 최종 전입 대상자 확정 조율"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부간/부서간 인력 적정성 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "전출/전입 부서장 간 할애 일정 합의 완료", "strategy": "HR", "reason": "부서장 간의 이해관계 충돌 조율 및 최종 일정 협상 (고부가가치)"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "전배발령",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 사후 조치", "l6_to_be": "인사 발령 기안서 승인 완료", "strategy": "Digital Worker", "reason": "확정된 일정을 시스템상 발령으로 생성"},

    # ----------------------------------------------------
    # 도메인: 인력운영 > L4: 휴복직
    # ----------------------------------------------------
    # AS-IS L5: 휴직
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 신청",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 신청/접수", "l6_to_be": "휴직 가능 여부 및 잔여일수 안내 챗봇 응대", "strategy": "Digital Worker", "reason": "직원의 규정 및 잔여일수 문의를 챗봇이 대응"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직원 작성 및 신청",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 신청/접수", "l6_to_be": "휴직 증빙 서류 육안 대조 완료", "strategy": "SSC", "reason": "질병/가족돌봄 등 진단서 원본의 육안 대조 및 징구 패키지"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 면담",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 심사", "l6_to_be": "특이 케이스 휴직 면담 결과 확정", "strategy": "HR", "reason": "번아웃, 조직 갈등 등 HR 개입이 필요한 예외적 면담 진행"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 행정사항 안내",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 사후 처리", "l6_to_be": "휴직자 급여/복리후생 변동사항 안내 메일 발송", "strategy": "Digital Worker", "reason": "휴직 확정 시 자동 안내문 발송"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 행정사항 안내",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 사후 처리", "l6_to_be": "휴직 발령 ERP 시스템 등록", "strategy": "Digital Worker", "reason": "기계적 시스템 반영"}
]

def export_to_csv():
    headers = [
        "[AS-IS] L3", "[AS-IS] L4", "[AS-IS] L5", "[AS-IS] L6",
        "[TO-BE] L3", "[TO-BE] L4", "[TO-BE] L5", "[TO-BE] L6",
        "클렌징 주체", "전략 사유"
    ]
    
    with open('FINAL/hr_cleansing_ai_generated_result.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in AI_GENERATED_MOCK_RESULTS:
            writer.writerow({
                "[AS-IS] L3": row["l3"],
                "[AS-IS] L4": row["l4_as_is"],
                "[AS-IS] L5": row["l5_as_is"],
                "[AS-IS] L6": row["l6_as_is"],
                "[TO-BE] L3": row["l3"],           # L3는 고정
                "[TO-BE] L4": row["l4_to_be"],
                "[TO-BE] L5": row["l5_to_be"],
                "[TO-BE] L6": row["l6_to_be"],
                "클렌징 주체": row["strategy"],
                "전략 사유": row["reason"]
            })
            
    print("AI 시뮬레이션 기반 최종 형태 CSV 생성 완료: FINAL/hr_cleansing_ai_generated_result.csv")

if __name__ == "__main__":
    export_to_csv()
