import json
import csv
import re

def advanced_smart_split(l3, l4, l5_as_is, l6_as_is):
    rows = []
    text = l6_as_is.replace('(', ' ').replace(')', ' ').strip()
    
    # ----------------------------------------------------
    # 1. 거대 L5 분해 (De-composition)
    # ----------------------------------------------------
    l5_to_be = l5_as_is
    if l5_as_is == "사내 Job Posting":
        if any(k in text for k in ["수요", "타당성", "공고", "Post"]): l5_to_be = "J/P 기획 및 수요조사"
        elif any(k in text for k in ["지원자", "평가", "면접"]): l5_to_be = "J/P 선발 전형 운영"
        else: l5_to_be = "J/P 사후 발령 관리"
    elif l5_as_is == "입사 및 온보딩":
        if any(k in text for k in ["O/T", "안내", "준비"]): l5_to_be = "입사 전 서류 및 O/T"
        elif any(k in text for k in ["발령"]): l5_to_be = "입사 발령 및 시스템 적재"
        else: l5_to_be = "입문 교육 및 현업 배치"
    elif l5_as_is == "휴직":
        if any(k in text for k in ["신청", "면담", "검토"]): l5_to_be = "휴직 신청 및 요건 검증"
        else: l5_to_be = "휴직 사후 행정 처리"
    elif l5_as_is == "면접":
        if any(k in text for k in ["위원", "조율", "준비"]): l5_to_be = "면접 기획 및 일정 세팅"
        else: l5_to_be = "면접 실행 및 평가 취합"
    elif l5_as_is == "서류심사":
        if "안내" in text: l5_to_be = "서류 전형 결과 발송"
        else: l5_to_be = "지원서 필터링 및 평가"
        
    # ----------------------------------------------------
    # 2. 3-Step 1:N 극한 분해 (Input -> Process -> Output)
    # ----------------------------------------------------
    # (A) 의사결정 / 선발 / 심사 / 평가 계열
    if any(k in text for k in ['선발', '심사', '평가', '검토', '확정', '승인', '결정']):
        # Input
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 심사 대상자 데이터베이스 추출", 'strategy': 'Digital Worker', 'reason': '시스템 내 후보군/대상자 조건 기반 자동 필터링 및 명단 추출'})
        # Process
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 타당성 검토 및 최종 결과안 확정", 'strategy': 'HR', 'reason': '대상자 요건 및 조직 정황을 고려한 정성적 판단 및 의사결정'})
        # Output
        if '안내' not in text:
            rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 확정 결과 시스템 반영 및 저장", 'strategy': 'Digital Worker', 'reason': 'HR이 확정한 최종 결과값을 인사 시스템에 기계적 업데이트'})

    # (B) 운영 / 행사 / 진행 / 준비 계열
    elif any(k in text for k in ['운영', '진행', '실시', '준비']):
        # Input
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 운영 일정 및 가용 자원 리스트 취합", 'strategy': 'Digital Worker', 'reason': '참석자 일정 및 장소 가용성 시스템 데이터 취합'})
        # Process 1 (Physical)
        if l3 == '총무' or any(k in text for k in ['물리', '시설', '장소', '다과', '세팅']):
            rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 오프라인 현장 세팅 및 물류 지원 패키지", 'strategy': 'SSC', 'reason': '행사장 세팅, 다과 준비 등 물리적 수작업 패키지 이관'})
        else:
            rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 최종 운영 시나리오 및 타임테이블 확정", 'strategy': 'HR', 'reason': '복합적 변수를 고려한 행사/운영 기획안 컨펌'})
        # Output
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 대상자 공식 안내문 및 리마인더 발송", 'strategy': 'Digital Worker', 'reason': '템플릿 기반 대량 알림 메일/메시지 자동 발송'})

    # (C) 시스템 반영 / 데이터 처리 / 등록 계열
    elif any(k in text for k in ['등록', '저장', '반영', '입력', '수정', '오류']):
        # Input
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 원천 증빙 서류 및 제출 데이터 취합", 'strategy': 'Digital Worker', 'reason': '여러 채널로 인입된 데이터 단일 포맷 병합'})
        # Process (Physical Check)
        if any(k in text for k in ['서류', '증명서', '진단서', '영수증']):
            rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 실물 증빙 서류 원본 육안 대조", 'strategy': 'SSC', 'reason': '위변조 확인을 위한 영수증/증명서 육안 패키지 검수'})
        else:
            rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 마스터 데이터 정합성 규칙 대조", 'strategy': 'Digital Worker', 'reason': 'Workday 등 시스템 로직에 의한 기계적 값 검증'})
        # Output
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 최종 데이터 Workday 시스템 등록", 'strategy': 'Digital Worker', 'reason': '검증 완료된 데이터의 시스템 Bulk 업로드'})

    # (D) 안내 / 배포 / 공지 계열
    elif any(k in text for k in ['안내', '공지', '메일', '배포', '홍보']):
        # Input
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 수신 대상자 그룹 명단 추출", 'strategy': 'Digital Worker', 'reason': '발송 타겟(조직/직급/전형별) 대상자 쿼리 및 목록화'})
        # Process
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 안내문 초안 톤앤매너 검수 및 확정", 'strategy': 'HR', 'reason': '민감한 이슈(인사발령/평가 등)의 대외 메시지 문구 최종 컨펌'})
        # Output
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 전사/타겟 채널 공식 메시지 발송", 'strategy': 'Digital Worker', 'reason': '이메일, 인트라넷, 카카오톡 등 매체별 일괄 시스템 전송'})

    # (E) 자료 작성 / 통계 / 기획 계열
    elif any(k in text for k in ['작성', '분석', '기록', '도출', '수립', '설계']):
        # Input
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 연도별/조직별 과거 이력 리포트 추출", 'strategy': 'Digital Worker', 'reason': '기안서 작성을 위한 Raw 데이터 시스템 다운로드'})
        # Process
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 분석 결과 기반 전략 기안서 확정", 'strategy': 'HR', 'reason': '통찰력이 요구되는 보고서 작성 및 임원진 결재 완료'})
    
    # (F) 그 외 애매한 항목들 (최소 2-Step 분해)
    else:
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 요건 확인용 기초 자료 취합", 'strategy': 'Digital Worker', 'reason': '산재된 데이터의 중앙 집중화'})
        rows.append({'l5_to_be': l5_to_be, 'l6': f"[{text}] 인사 기준 기반 최종 결과 확정", 'strategy': 'HR', 'reason': '인사규정 및 상황에 따른 최종 승인'})

    return rows

def generate_cleansing_csv():
    with open('full_realdata.json', 'r', encoding='utf-8') as f:
        hr_modules = json.load(f)

    output_rows = []
    
    for module in hr_modules:
        l3 = module['l3']
        for l4_item in module['l4_list']:
            l4 = l4_item['l4']
            for task in l4_item['tasks']:
                l5 = task['l5']
                l6_activities = task['l6_activities']
                
                if not l6_activities:
                    # L6가 아예 없는 L5 전용 항목도 최소 2단계로 강제 해체
                    output_rows.append({
                        "[AS-IS] L3": l3, "[AS-IS] L4": l4, "[AS-IS] L5": l5, "[AS-IS] L6": "(데이터 없음)",
                        "[TO-BE] L3": l3, "[TO-BE] L4": l4, "[TO-BE] L5": l5, "[TO-BE] L6": f"[{l5}] 기초 현황표 시스템 추출",
                        "추천 주체": "Digital Worker", "전략 사유": "신규 데이터 생성을 위한 과거 이력 및 기초값 수합 자동화"
                    })
                    
                    # 총무 도메인이거나 물리적 키워드인 경우 SSC 배정 로직 추가
                    final_strategy = "HR"
                    final_reason = "취합된 데이터를 바탕으로 한 관리자/HR의 최종 판단 및 컨펌"
                    if l3 == '총무' or any(k in l5 for k in ['비품', '시설', '환경', '차량', '배송', '세팅']):
                        final_strategy = "SSC"
                        final_reason = "물리적 현장 조치 및 관리 패키지 이관 (SSC)"
                        
                    output_rows.append({
                        "[AS-IS] L3": l3, "[AS-IS] L4": l4, "[AS-IS] L5": l5, "[AS-IS] L6": "(데이터 없음)",
                        "[TO-BE] L3": l3, "[TO-BE] L4": l4, "[TO-BE] L5": l5, "[TO-BE] L6": f"[{l5}] 최종 의사결정 및 현장 조치 확정",
                        "추천 주체": final_strategy, "전략 사유": final_reason
                    })
                else:
                    for l6_as_is in l6_activities:
                        split_results = advanced_smart_split(l3, l4, l5, l6_as_is)
                        for res in split_results:
                            output_rows.append({
                                "[AS-IS] L3": l3, "[AS-IS] L4": l4, "[AS-IS] L5": l5, "[AS-IS] L6": l6_as_is,
                                "[TO-BE] L3": l3, "[TO-BE] L4": l4, "[TO-BE] L5": res['l5_to_be'], "[TO-BE] L6": res['l6'],
                                "추천 주체": res['strategy'], "전략 사유": res['reason']
                            })

    headers = ["[AS-IS] L3", "[AS-IS] L4", "[AS-IS] L5", "[AS-IS] L6", 
               "[TO-BE] L3", "[TO-BE] L4", "[TO-BE] L5", "[TO-BE] L6", 
               "추천 주체", "전략 사유"]
               
    with open('FINAL/Process_cleansing_V1.0.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)
    return output_rows

if __name__ == "__main__":
    generate_cleansing_csv()
