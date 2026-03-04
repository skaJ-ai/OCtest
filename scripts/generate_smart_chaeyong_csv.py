import json
import csv
import re

# 기존 realdata.ts에서 [채용] 도메인의 L5 목록을 "정밀한 제미나이 추론 결과"로 하드코딩하여 완벽히 교체합니다.
# 단순 if-else 문이 아닌, HR 도메인 전문성에 기반한 철저한 1:N 쪼개기 및 상태 동사 적용

CHAEYONG_SMART_RESULTS = [
    # L5: 채용 계획 수립(경영계획) -> TO-BE 분할: 채용 수요 조사, 채용 TO 확정
    {"l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "전체 채용규모 산정", "l5_to_be": "채용 수요 조사", "l6_to_be": "전년도 직군별 채용 실적 리포트 취합", "strategy": "Digital Worker", "reason": "과거 데이터베이스의 기계적 수합 및 기초 통계 작성"},
    {"l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "팀별 채용규모 확인", "l5_to_be": "채용 수요 조사", "l6_to_be": "부서별 인력 수요 조사 양식 배포", "strategy": "Digital Worker", "reason": "각 부서장에게 수요 조사 템플릿 일괄 발송"},
    {"l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "팀별 채용규모 확인", "l5_to_be": "채용 수요 조사", "l6_to_be": "회신 데이터 기반 부서별 수요 취합", "strategy": "Digital Worker", "reason": "접수된 양식을 단일 시트로 병합하는 단순 작업"},
    {"l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "충원 필요성 검토", "l5_to_be": "채용 TO 확정", "l6_to_be": "부서별 충원 타당성 심사 결과 확정", "strategy": "HR", "reason": "현업 부서장과의 조율 및 재무적 관점의 정성적 판단"},
    {"l4": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "사업부 채용규모 확정", "l5_to_be": "채용 TO 확정", "l6_to_be": "최종 사업부 채용 TO 기안서 확정", "strategy": "HR", "reason": "경영진 최종 승인을 위한 전략적 문서 완성"},

    # L5: 직무기술서 작성 -> TO-BE: JD 개발
    {"l4": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청", "l5_to_be": "JD(Job Description) 개발", "l6_to_be": "포지션별 직무기술서 작성 요청 메일 발송", "strategy": "Digital Worker", "reason": "채용 대상 부서에 가이드 및 양식 일괄 발송"},
    {"l4": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청", "l5_to_be": "JD(Job Description) 개발", "l6_to_be": "회신된 직무기술서 내용 품질 검수 확정", "strategy": "HR", "reason": "현업이 작성한 기술서가 채용 시장에 적합한지 톤앤매너 검수"},
    {"l4": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청", "l5_to_be": "JD(Job Description) 개발", "l6_to_be": "최종 직무기술서 채용 시스템 등록", "strategy": "Digital Worker", "reason": "확정된 JD를 사내외 채용 플랫폼 데이터베이스에 업로드"},

    # L5: 인재 소싱 채널 선정 및 액팅 -> TO-BE 분할: 소싱 전략 기획, 소싱 실행, 인재 DB 관리
    {"l4": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "발굴 기준 확정", "l5_to_be": "다이렉트 소싱 전략 수립", "l6_to_be": "타겟 포지션 핵심 역량 키워드 확정", "strategy": "HR", "reason": "어떤 역량을 가진 인재를 찾을지 페르소나 정의"},
    {"l4": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "소싱 채널 선정", "l5_to_be": "다이렉트 소싱 전략 수립", "l6_to_be": "이용 소싱 채널(플랫폼/헤드헌터) 목록 확정", "strategy": "HR", "reason": "포지션 난이도와 예산을 고려한 외부 채널 선정"},
    {"l4": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 발굴", "l5_to_be": "소싱 실행(Outbound)", "l6_to_be": "키워드 매칭 대상자 이력서 풀 추출", "strategy": "Digital Worker", "reason": "정해진 키워드를 기반으로 링크드인 등에서 후보자 프로필 자동 스크래핑"},
    {"l4": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 발굴", "l5_to_be": "소싱 실행(Outbound)", "l6_to_be": "스카웃 제안 콜드메일 발송", "strategy": "Digital Worker", "reason": "후보자 풀 대상 템플릿 기반 대량 메시지 발송"},
    {"l4": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 풀 구축", "l5_to_be": "인재 DB 관리", "l6_to_be": "관심 표명 후보자 이력서 채용DB 등록", "strategy": "Digital Worker", "reason": "회신온 후보자들의 이력서를 사내 ATS에 자동 적재"},

    # L5: 서류심사 -> TO-BE 분할: 서류 접수/필터링, 서류 평가
    {"l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행", "l5_to_be": "지원서 접수 및 필터링", "l6_to_be": "블라인드 위반/필수 요건 미달자 필터링 명단 확정", "strategy": "Digital Worker", "reason": "최소 학력, 금지어(블라인드) 포함 여부 등 시스템 자동 필터링"},
    {"l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행", "l5_to_be": "서류 평가 운영", "l6_to_be": "HR 서류 평가 점수표 확정", "strategy": "HR", "reason": "HR 관점에서의 정성적 역량 및 로열티 1차 평가"},
    {"l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "현업 서류 검토 진행", "l5_to_be": "서류 평가 운영", "l6_to_be": "현업 면접관 서류 검토 요청 알림 발송", "strategy": "Digital Worker", "reason": "해당 부서 면접관에게 시스템 알림 및 리마인더 자동 발송"},
    {"l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "현업 서류 검토 진행", "l5_to_be": "서류 평가 운영", "l6_to_be": "최종 서류 전형 합격자 명단 확정", "strategy": "HR", "reason": "HR과 현업의 점수를 취합하여 최종 서류 합격 커트라인 및 명단 확정"},
    {"l4": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "서류 검토 결과안내", "l5_to_be": "서류 평가 운영", "l6_to_be": "서류 전형 결과(합/불) 안내 메일 발송", "strategy": "Digital Worker", "reason": "합불 명단을 바탕으로 템플릿 메일 일괄 전송"},

    # L5: 자격 검증(GSAT, 코딩 테스트 등) -> TO-BE: 인적성/코딩테스트 운영
    {"l4": "선발전형", "l5_as_is": "자격 검증(GSAT, 코딩 테스트 등)", "l6_as_is": "검정 대상자 선정", "l5_to_be": "온/오프라인 테스트 운영", "l6_to_be": "테스트 응시 대상자 명단 취합", "strategy": "Digital Worker", "reason": "서류 합격자 명단을 기반으로 응시 대상자 DB 자동 이관"},
    {"l4": "선발전형", "l5_as_is": "자격 검증(GSAT, 코딩 테스트 등)", "l6_as_is": "검정 일정/장소 확정", "l5_to_be": "온/오프라인 테스트 운영", "l6_to_be": "테스트 일시 및 방식(온/오프) 기안서 확정", "strategy": "HR", "reason": "응시자 규모를 고려한 예산 및 진행 방식 기획/결정"},
    {"l4": "선발전형", "l5_as_is": "자격 검증(GSAT, 코딩 테스트 등)", "l6_as_is": "검정 운영 위원 선발/교육", "l5_to_be": "온/오프라인 테스트 운영", "l6_to_be": "감독관 배정 명단 확정", "strategy": "HR", "reason": "사내 감독관 차출 인원 조율 및 확정"},
    {"l4": "선발전형", "l5_as_is": "자격 검증(GSAT, 코딩 테스트 등)", "l6_as_is": "검정 준비", "l5_to_be": "온/오프라인 테스트 운영", "l6_to_be": "수험표 및 수험 가이드라인 메일 배포", "strategy": "Digital Worker", "reason": "응시자 대상 시스템 일괄 메일 배포"},
    {"l4": "선발전형", "l5_as_is": "자격 검증(GSAT, 코딩 테스트 등)", "l6_as_is": "검정 운영", "l5_to_be": "온/오프라인 테스트 운영", "l6_to_be": "오프라인 고사장 물리적 세팅 패키지", "strategy": "SSC", "reason": "시험장 책상 배치, 노트북 설치, 안내문 부착 등 완전한 물리적 작업"},
    {"l4": "선발전형", "l5_as_is": "자격 검증(GSAT, 코딩 테스트 등)", "l6_as_is": "검정 후속처리", "l5_to_be": "온/오프라인 테스트 운영", "l6_to_be": "테스트 결과 점수표 시스템 저장", "strategy": "Digital Worker", "reason": "외주 업체/시스템에서 산출된 점수 데이터베이스 API 연동 및 저장"},

    # L5: 면접 -> TO-BE 분할: 면접 기획/안내, 면접 실행
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접위원 선발/교육", "l5_to_be": "면접 위원 구성 및 교육", "l6_to_be": "직무별 면접 위원 배정 명단 확정", "strategy": "HR", "reason": "포지션 전문성을 고려한 면접관 선발 및 조율"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접위원 선발/교육", "l5_to_be": "면접 위원 구성 및 교육", "l6_to_be": "면접관 평가 가이드북 사내 배포", "strategy": "Digital Worker", "reason": "확정된 면접관 대상 메뉴얼 자동 메일링"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접일정 조율", "l5_to_be": "면접 일정 관리", "l6_to_be": "후보자 및 면접관 참석 가능 일정 취합", "strategy": "Digital Worker", "reason": "일정 조율 툴(Calendly 등)을 통한 빈 시간대 자동 파악"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접일정 조율", "l5_to_be": "면접 일정 관리", "l6_to_be": "최종 면접 타임테이블 확정", "strategy": "HR", "reason": "복잡한 예외상황(임원 일정 등)을 반영한 최종 일정 픽스"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접운영 준비", "l5_to_be": "면접 실행 및 운영", "l6_to_be": "면접 참석 안내 및 화상 링크 메일 발송", "strategy": "Digital Worker", "reason": "픽스된 일정에 맞춰 템플릿 메일 자동 발송"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접 운영", "l5_to_be": "면접 실행 및 운영", "l6_to_be": "오프라인 면접장 다과 및 명패 세팅 패키지", "strategy": "SSC", "reason": "대기실 안내, 음료 세팅 등 물리적 현장 지원 서비스 통이관"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접 후속처리", "l5_to_be": "면접 결과 취합", "l6_to_be": "면접관 개별 평가 점수 및 코멘트 취합", "strategy": "Digital Worker", "reason": "채용 시스템상에 입력된 평가 결과 엑셀 다운로드 및 취합"},
    {"l4": "선발전형", "l5_as_is": "면접", "l6_as_is": "면접 후속처리", "l5_to_be": "면접 결과 취합", "l6_to_be": "최종 면접 합격자 명단 확정", "strategy": "HR", "reason": "평가 의견이 엇갈릴 경우 랩업 미팅을 통한 정성적 최종 판정"},

    # L5: 채용 및 처우 승인 -> TO-BE: 처우 협상, 채용 품의
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "중복확인", "l5_to_be": "입사 전 사전 검증", "l6_to_be": "타 계열사 중복지원 이력 조회 결과 확정", "strategy": "Digital Worker", "reason": "데이터베이스 내 주민번호/이메일 기반 중복값 기계적 조회"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "후보자 종합 검증", "l5_to_be": "입사 전 사전 검증", "l6_to_be": "레퍼런스 체크 및 평판조회 보고서 확정", "strategy": "HR", "reason": "외부 업체 또는 자체 연락을 통한 심층 인성/역량 검증 보고서 작성"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "처우 협의/승인", "l5_to_be": "오퍼 및 처우 협상", "l6_to_be": "내부 기준 기반 1차 처우(연봉) 제안 테이블 확정", "strategy": "HR", "reason": "사내 페이밴드 및 후보자 경력을 고려한 전략적 연봉 산정"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "처우 협의/승인", "l5_to_be": "오퍼 및 처우 협상", "l6_to_be": "최종 처우 합의안 기안서 확정", "strategy": "HR", "reason": "후보자와의 줄다리기 협상(핑퐁) 후 도출된 최종 금액 컨펌"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "오퍼 확보", "l5_to_be": "오퍼 및 처우 협상", "l6_to_be": "처우 안내(Offer Letter) 메일 발송", "strategy": "Digital Worker", "reason": "확정된 처우 내역을 공식 템플릿에 담아 발송"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "오퍼 확보", "l5_to_be": "오퍼 및 처우 협상", "l6_to_be": "후보자 Offer 수락 서명본 저장", "strategy": "Digital Worker", "reason": "전자서명 시스템(DocuSign 등)을 통한 완료본 자동 적재"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "건강검진", "l5_to_be": "입사 전 사전 검증", "l6_to_be": "채용 건강검진 적격 여부 결과 등록", "strategy": "Digital Worker", "reason": "검진 센터에서 송부받은 합/불/재검 데이터를 시스템에 단순 이관"},
    {"l4": "선발전형", "l5_as_is": "채용 및 처우 승인", "l6_as_is": "채용 품의 진행", "l5_to_be": "채용 품의", "l6_to_be": "최종 채용 확정 품의서 완료", "strategy": "HR", "reason": "대표이사 등 임원진 대상 최종 채용 기안 문서 작성 및 결재 상신"},
]

def generate_smart_csv():
    headers = [
        "[AS-IS] L3", "[AS-IS] L4", "[AS-IS] L5", "[AS-IS] L6", 
        "[TO-BE] L3", "[TO-BE] L4", "[TO-BE] L5", "[TO-BE] L6", 
        "추천 주체", "전략 사유"
    ]
    
    with open('FINAL/hr_cleansing_smart_result_chaeyong.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in CHAEYONG_SMART_RESULTS:
            writer.writerow({
                "[AS-IS] L3": "채용",
                "[AS-IS] L4": row["l4"],
                "[AS-IS] L5": row["l5_as_is"],
                "[AS-IS] L6": row["l6_as_is"],
                "[TO-BE] L3": "채용",
                "[TO-BE] L4": row["l4"],
                "[TO-BE] L5": row["l5_to_be"],
                "[TO-BE] L6": row["l6_to_be"],
                "추천 주체": row["strategy"],
                "전략 사유": row["reason"]
            })
            
    print("스마트 분해 CSV 생성 완료: FINAL/hr_cleansing_smart_result_chaeyong.csv")

if __name__ == "__main__":
    generate_smart_csv()
