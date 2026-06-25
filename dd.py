[사용자] → 사이드바에서 프로필 저장
        → calculate_saju_chart (만세력 계산)
        → analyze_five_elements (오행 분석)
        → 프로필 완성 & 세션에 저장

[사용자] → 채팅 메시지 또는 빠른 질문 클릭
        → 의도(intent) 라우팅
        → 필요한 Tool만 실행
        → LLM 또는 폴백 답변 생성
        → 채팅 화면에 표시


============================================


┌──────────────────────────────────────────────────────────────────┐
│  Python (saju_chart.py)                                         │
│                                                                  │
│  사용자 입력 JSON을 stdin으로 넘김                                 │
│           │                                                      │
│           ▼  subprocess.run()                                    │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  Node.js 헬퍼 (scripts/calculate_saju.mjs)           │        │
│  │                                                      │        │
│  │  stdin으로 JSON 받음                                  │        │
│  │           │                                          │        │
│  │           ▼  라이브러리 함수 호출                       │        │
│  │  ┌──────────────────────────────────────────┐        │        │
│  │  │  @fullstackfamily/manseryeok              │        │        │
│  │  │                                          │        │        │
│  │  │  calculateSaju(년, 월, 일, 시, 분)        │        │        │
│  │  │  lunarToSolar(년, 월, 일, 윤달여부)       │        │        │
│  │  │        → 사주팔자 계산 결과 반환            │        │        │
│  │  └──────────────────────────────────────────┘        │        │
│  │           │                                          │        │
│  │           ▼                                          │        │
│  │  stdout으로 결과 JSON 출력                            │        │
│  └──────────────────────────────────────────────────────┘        │
│           │                                                      │
│           ▼  stdout 읽어서 JSON 파싱                              │
│  Python이 결과를 받아서 다른 도구들에게 전달                        │
└──────────────────────────────────────────────────────────────────┘



============================================

#입력 (Python → Node.js로 보내는 JSON)


{
  "birth_date": "1998-03-12",
  "birth_time": "09:00",
  "calendar_type": "solar",
  "birth_time_unknown": false
}



#출력 (Node.js → Python으로 돌려주는 JSON)

{
  "ok": true,
  "data": {
    "year_pillar": "무인",
    "month_pillar": "을묘",
    "day_pillar": "병진",
    "hour_pillar": "계사",
    "year_pillar_hanja": "戊寅",
    "month_pillar_hanja": "乙卯",
    "day_pillar_hanja": "丙辰",
    "hour_pillar_hanja": "癸巳",
    "time_precision": "known",
    "calendar_type": "solar",
    "source": "manseryeok-js (@fullstackfamily/manseryeok)"
  }
}
