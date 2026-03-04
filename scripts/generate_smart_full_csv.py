import csv

# 이 리스트에 전체 도메인의 "스마트 분해 결과"가 모두 담깁니다.
# LLM(제미나이)의 전문성을 바탕으로 L5의 스톱워치 단위 쪼개기, L6의 A+B(명사+고도화된 상태동사) 규칙을 전면 적용한 데이터입니다.

ALL_SMART_RESULTS = [
    # ==========================================
    # 1. 도메인: 채용 (기존 완성본 + 보완)
    # ==========================================
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "전체 채용규모 산정",
     "l4_to_be": "채용계획", "l5_to_be": "채용 수요 조사", "l6_to_be": "전년도 직군별 채용 실적 리포트 추출", "strategy": "Digital Worker", "reason": "과거 데이터베이스의 기계적 수합 및 기초 통계 생성"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "팀별 채용규모 확인",
     "l4_to_be": "채용계획", "l5_to_be": "채용 수요 조사", "l6_to_be": "부서별 인력 수요 조사 양식 발송", "strategy": "Digital Worker", "reason": "각 부서장에게 수요 조사 템플릿 일괄 메일/메시지 송신"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "팀별 채용규모 확인",
     "l4_to_be": "채용계획", "l5_to_be": "채용 수요 조사", "l6_to_be": "회신 데이터 기반 부서별 수요 취합", "strategy": "Digital Worker", "reason": "접수된 양식을 단일 시트로 병합하는 단순 작업"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "충원 필요성 검토",
     "l4_to_be": "채용계획", "l5_to_be": "채용 TO 확정", "l6_to_be": "부서별 충원 타당성 심사 결과 확정", "strategy": "HR", "reason": "현업 부서장과의 조율 및 재무적 관점의 정성적 판단"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "채용 계획 수립(경영계획)", "l6_as_is": "사업부 채용규모 확정",
     "l4_to_be": "채용계획", "l5_to_be": "채용 TO 확정", "l6_to_be": "최종 사업부 채용 TO 기안서 확정", "strategy": "HR", "reason": "경영진 최종 승인을 위한 전략적 문서 완성 및 결재"},

    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청",
     "l4_to_be": "채용계획", "l5_to_be": "JD(Job Description) 개발", "l6_to_be": "포지션별 직무기술서 작성 가이드 발송", "strategy": "Digital Worker", "reason": "채용 대상 부서에 가이드 및 양식 일괄 발송"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청",
     "l4_to_be": "채용계획", "l5_to_be": "JD(Job Description) 개발", "l6_to_be": "회신된 직무기술서 내용 품질 확정", "strategy": "HR", "reason": "현업이 작성한 기술서가 채용 시장에 적합한지 톤앤매너 검수"},
    {"l3": "채용", "l4_as_is": "채용계획", "l5_as_is": "직무기술서 작성", "l6_as_is": "직무기술서 작성 요청",
     "l4_to_be": "채용계획", "l5_to_be": "JD(Job Description) 개발", "l6_to_be": "최종 직무기술서 채용 플랫폼 등록", "strategy": "Digital Worker", "reason": "확정된 JD를 사내외 채용 플랫폼 데이터베이스에 시스템 업로드"},

    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "발굴 기준 확정",
     "l4_to_be": "인재발굴", "l5_to_be": "다이렉트 소싱 전략 수립", "l6_to_be": "타겟 포지션 핵심 역량 키워드 확정", "strategy": "HR", "reason": "어떤 역량을 가진 인재를 찾을지 페르소나 정의"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "소싱 채널 선정",
     "l4_to_be": "인재발굴", "l5_to_be": "다이렉트 소싱 전략 수립", "l6_to_be": "이용 소싱 채널(플랫폼/헤드헌터) 목록 확정", "strategy": "HR", "reason": "포지션 난이도와 예산을 고려한 외부 채널 선정"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 발굴",
     "l4_to_be": "인재발굴", "l5_to_be": "소싱 실행(Outbound)", "l6_to_be": "키워드 매칭 대상자 이력서 풀 추출", "strategy": "Digital Worker", "reason": "정해진 키워드를 기반으로 링크드인 등에서 후보자 프로필 자동 스크래핑"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 발굴",
     "l4_to_be": "인재발굴", "l5_to_be": "소싱 실행(Outbound)", "l6_to_be": "스카웃 제안 콜드메일 발송", "strategy": "Digital Worker", "reason": "후보자 풀 대상 템플릿 기반 대량 메시지 송신"},
    {"l3": "채용", "l4_as_is": "인재발굴", "l5_as_is": "인재 소싱 채널 선정 및 액팅", "l6_as_is": "후보자 풀 구축",
     "l4_to_be": "인재발굴", "l5_to_be": "인재 DB 관리", "l6_to_be": "관심 표명 후보자 이력서 사내DB 등록", "strategy": "Digital Worker", "reason": "회신온 후보자들의 이력서를 사내 ATS에 자동 적재"},

    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "지원서 접수 및 필터링", "l6_to_be": "필수 요건(학위/블라인드 등) 미달자 필터링 추출", "strategy": "Digital Worker", "reason": "규칙 기반의 하드 스킬 미달자 시스템 자동 필터링"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "HR 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "서류 평가 운영", "l6_to_be": "HR 서류 평가 점수표 확정", "strategy": "HR", "reason": "HR 관점에서의 정성적 역량 및 로열티 1차 평가"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "현업 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "서류 평가 운영", "l6_to_be": "현업 면접관 서류 검토 요청 시스템 알림 발송", "strategy": "Digital Worker", "reason": "해당 부서 면접관에게 시스템 알림 및 리마인더 자동 송신"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "현업 서류 검토 진행",
     "l4_to_be": "선발전형", "l5_to_be": "서류 평가 운영", "l6_to_be": "최종 서류 전형 합격자 명단 확정", "strategy": "HR", "reason": "HR과 현업의 점수를 종합 판단하여 최종 서류 합격 커트라인 픽스"},
    {"l3": "채용", "l4_as_is": "선발전형", "l5_as_is": "서류심사", "l6_as_is": "서류 검토 결과안내",
     "l4_to_be": "선발전형", "l5_to_be": "서류 평가 운영", "l6_to_be": "서류 전형 결과(합/불) 안내 메일 발송", "strategy": "Digital Worker", "reason": "합불 명단을 바탕으로 템플릿 메일 일괄 전송"},

    # ==========================================
    # 2. 도메인: 인력운영 (이번 심층 분해의 핵심 타겟)
    # ==========================================
    # L5: 사내 Job Posting (비대했던 것을 기획/선발/사후로 쪼갬)
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부문(부서별) J/P 부서 수요 취합",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 수요조사", "l6_to_be": "J/P(Job Posting) 수요 조사 양식 발송", "strategy": "Digital Worker", "reason": "전사 부서장 대상 템플릿 안내 시스템 발송"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부문(부서별) J/P 부서 수요 취합",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 수요조사", "l6_to_be": "J/P 접수 포지션 리스트 취합", "strategy": "Digital Worker", "reason": "회신된 접수 내역의 기계적 엑셀 취합"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "J/P 운영 타당성 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 수요조사", "l6_to_be": "최종 J/P 오픈 대상 포지션 확정", "strategy": "HR", "reason": "전사 인력 운영 관점에서 타 부서 할애를 감수할 핵심 포지션인지 타당성 심사"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "Post 확정 후 J/P 실시",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 기획 및 수요조사", "l6_to_be": "사내 게시판 J/P 공식 공고문 배포", "strategy": "Digital Worker", "reason": "작성된 공고문을 사내 인트라넷에 시스템 업로드"},
    
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "지원자 지원 자격 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "사내 전배 규정(근속연수/고과) 미달자 필터링 추출", "strategy": "Digital Worker", "reason": "ERP 데이터 연동을 통한 지원 자격 시스템 1차 필터링"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "지원서 평가",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "현업 J/P 서류 평가 결과표 취합", "strategy": "Digital Worker", "reason": "현업 부서장의 검토 결과 시스템 등록분 취합"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "지원서 평가결과 검토 후 면접 대상자 확정",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "J/P 면접 대상자 명단 확정", "strategy": "HR", "reason": "최종 면접에 올릴 대상자 규모 HR 컨펌"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "면접 진행 및 평가",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "J/P 화상 면접 링크 및 일정 안내 발송", "strategy": "Digital Worker", "reason": "대상자에게 시스템 자동 알림 발송"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "면접평가 결과 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 선발 운영", "l6_to_be": "J/P 최종 전입 합격자 명단 확정", "strategy": "HR", "reason": "면접 결과를 바탕으로 전입 부서장과 조율 후 합격자 확정"},
    
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "사업부간/부서간 인력 적정성 검토",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 사후 조치", "l6_to_be": "전출/전입 부서장 간 실이동 일정 합의안 확정", "strategy": "HR", "reason": "부서장 간의 이해관계 충돌(언제 빼줄 것인가) 조율 및 최종 일정 협상"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "서류/면접 합불 통보",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 사후 조치", "l6_to_be": "J/P 전형 최종 결과(합/불) 메일 발송", "strategy": "Digital Worker", "reason": "전체 결과 시스템 일괄 발송"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "사내 Job Posting", "l6_as_is": "전배발령",
     "l4_to_be": "인력이동", "l5_to_be": "J/P 사후 조치", "l6_to_be": "J/P 합격자 인사 발령 ERP 등록", "strategy": "Digital Worker", "reason": "확정된 실이동 일정에 맞춰 발령 데이터 시스템 적재"},

    # L5: 개별 전배
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "개별 전배", "l6_as_is": "충원 요청",
     "l4_to_be": "인력이동", "l5_to_be": "부서간 개별 전배", "l6_to_be": "현업 부서 전배 충원 요청서 접수", "strategy": "Digital Worker", "reason": "시스템상 요청 결재 라인 접수 로그"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "개별 전배", "l6_as_is": "충원 타당성 검토",
     "l4_to_be": "인력이동", "l5_to_be": "부서간 개별 전배", "l6_to_be": "개별 전배 타당성 및 조직 영향도 검토안 확정", "strategy": "HR", "reason": "정말 꼭 필요한 전배인지 인력 효율화 관점의 심층 분석"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "개별 전배", "l6_as_is": "적합 인력 서칭 및 Pool 구축",
     "l4_to_be": "인력이동", "l5_to_be": "부서간 개별 전배", "l6_to_be": "조건 부합 타겟 인력 리스트 추출", "strategy": "Digital Worker", "reason": "HR DB에서 특정 스킬/연차 보유자 조건 검색 및 엑셀 다운로드"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "개별 전배", "l6_as_is": "타겟 인력 할애 요청 / 할애 여부 검토",
     "l4_to_be": "인력이동", "l5_to_be": "부서간 개별 전배", "l6_to_be": "전출 부서장 대상 할애 동의 결과 확정", "strategy": "HR", "reason": "차출 대상 부서장과의 면담 및 협의를 통한 동의 도출"},
    {"l3": "인력운영", "l4_as_is": "인력이동", "l5_as_is": "개별 전배", "l6_as_is": "전배 발령",
     "l4_to_be": "인력이동", "l5_to_be": "부서간 개별 전배", "l6_to_be": "개별 전배 인사 발령 ERP 등록", "strategy": "Digital Worker", "reason": "확정된 전배 내역 시스템 반영"},

    # L5: 휴직
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 신청",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 신청 접수 및 1차 심사", "l6_to_be": "휴직 규정 및 잔여일수 안내 챗봇 발송", "strategy": "Digital Worker", "reason": "직원의 규정 및 잔여일수 단순 문의를 챗봇이 대응"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직원 작성 및 신청",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 신청 접수 및 1차 심사", "l6_to_be": "휴직원 및 증빙 서류 시스템 접수", "strategy": "Digital Worker", "reason": "시스템을 통한 제출서류 자동 분류 및 접수"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 적정성 및 일정, 서류 검토",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 신청 접수 및 1차 심사", "l6_to_be": "휴직 진단서/가족관계증명서 원본 육안 대조", "strategy": "SSC", "reason": "위변조 방지를 위한 법적 서류의 육안 진위여부 대조 패키지 이관"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 면담",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 예외 심사", "l6_to_be": "특이/반려 케이스 면담 결과 확정", "strategy": "HR", "reason": "번아웃, 조직 갈등 등 HR 개입이 필요한 정성적 면담 진행"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 행정사항 안내",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 사후 처리", "l6_to_be": "휴직자 대상 급여/보험 변동사항 안내 메일 발송", "strategy": "Digital Worker", "reason": "휴직 확정 시 템플릿에 따른 안내문 발송"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "휴직", "l6_as_is": "휴직 발령",
     "l4_to_be": "휴복직", "l5_to_be": "휴직 사후 처리", "l6_to_be": "휴직 발령 상태 ERP 등록", "strategy": "Digital Worker", "reason": "기계적 시스템 상태 변경 적용"},

    # L5: 복직
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "복직", "l6_as_is": "복직 안내(한달전, 일주일전)",
     "l4_to_be": "휴복직", "l5_to_be": "복직 지원 관리", "l6_to_be": "복직 예정일 도래 안내 및 의사확인 메일 발송", "strategy": "Digital Worker", "reason": "복직 1달 전 트리거에 의한 시스템 자동 발송"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "복직", "l6_as_is": "복직원 작성 및 신청",
     "l4_to_be": "휴복직", "l5_to_be": "복직 지원 관리", "l6_to_be": "복직원 시스템 접수", "strategy": "Digital Worker", "reason": "전자결재 시스템 수발신"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "복직", "l6_as_is": "출근 및 행정사항 처리",
     "l4_to_be": "휴복직", "l5_to_be": "복직 지원 관리", "l6_to_be": "복직자 부서 배치 및 좌석 확정", "strategy": "HR", "reason": "기존 부서 T/O 또는 직무 변경을 고려한 인력 재배치 판단"},
    {"l3": "인력운영", "l4_as_is": "휴복직", "l5_as_is": "복직", "l6_as_is": "휴직 발령 수정",
     "l4_to_be": "휴복직", "l5_to_be": "복직 지원 관리", "l6_to_be": "복직 발령 상태 ERP 등록", "strategy": "Digital Worker", "reason": "시스템 상태 원복 적재"},
     
    # ==========================================
    # 3. 도메인: 제도 (일부 예시)
    # ==========================================
    # L5: 피어리뷰 가이드 수립/배포
    {"l3": "제도", "l4_as_is": "피어리뷰", "l5_as_is": "가이드 수립/배포 및 시스템 준비", "l6_as_is": "피어리뷰 연간 운영가이드 수립",
     "l4_to_be": "업적/피어평가 기획", "l5_to_be": "피어리뷰 운영 기획", "l6_to_be": "당해년도 피어리뷰 평가 지표 및 문항표 확정", "strategy": "HR", "reason": "조직 방향성에 맞는 다면평가 지표 설계 기획"},
    {"l3": "제도", "l4_as_is": "피어리뷰", "l5_as_is": "가이드 수립/배포 및 시스템 준비", "l6_as_is": "임직원 가이드 작성/배포",
     "l4_to_be": "업적/피어평가 기획", "l5_to_be": "피어리뷰 운영 기획", "l6_to_be": "평가자 가이드라인 메뉴얼 사내 배포", "strategy": "Digital Worker", "reason": "확정된 메뉴얼을 인트라넷 게시 및 일괄 메일 전송"},
    {"l3": "제도", "l4_as_is": "피어리뷰", "l5_as_is": "가이드 수립/배포 및 시스템 준비", "l6_as_is": "피어리뷰 시스템 셋팅",
     "l4_to_be": "업적/피어평가 기획", "l5_to_be": "평가 시스템 세팅", "l6_to_be": "평가 기간 및 대상자 그룹웨어 설정 등록", "strategy": "Digital Worker", "reason": "단순 어드민 설정값 입력 작업"}
]

def generate_full_smart_csv():
    headers = [
        "[AS-IS] L3", "[AS-IS] L4", "[AS-IS] L5", "[AS-IS] L6", 
        "[TO-BE] L3", "[TO-BE] L4", "[TO-BE] L5", "[TO-BE] L6", 
        "추천 주체", "전략 사유"
    ]
    
    with open('FINAL/hr_cleansing_smart_full_v2.0.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in ALL_SMART_RESULTS:
            writer.writerow({
                "[AS-IS] L3": row["l3"],
                "[AS-IS] L4": row["l4_as_is"],
                "[AS-IS] L5": row["l5_as_is"],
                "[AS-IS] L6": row["l6_as_is"],
                "[TO-BE] L3": row["l3"],
                "[TO-BE] L4": row["l4_to_be"],
                "[TO-BE] L5": row["l5_to_be"],
                "[TO-BE] L6": row["l6_to_be"],
                "추천 주체": row["strategy"],
                "전략 사유": row["reason"]
            })
            
    print("단일 통합 스마트 분해 CSV 생성 완료: FINAL/hr_cleansing_smart_full_v2.0.csv")

if __name__ == "__main__":
    generate_full_smart_csv()
