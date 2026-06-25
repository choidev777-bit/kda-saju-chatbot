"""공통 상수, 응답 형식 유틸, 데이터 계약 정의.

이 프로젝트의 모든 tool 은 JSON 문자열을 입출력하며,
성공/실패 응답 형식을 여기서 한 곳으로 통일한다.

설계 메모(통합 리드):
- 오행 결과는 nested `counts` 형태로 표준화한다. (문서 간 flat/nested 불일치 해소)
- 모든 tool 의 성공 응답은 {"ok": true, "data": ...},
  실패 응답은 {"ok": false, "error": {"code", "message"}} 형식을 따른다.
"""
from __future__ import annotations

import json
from typing import Any

# --- 오행 (five elements) ------------------------------------------------
# 고정 우선순위. 동률일 때 strong/weak/recommended 오행 선택 기준이 된다.
ELEMENTS = ("wood", "fire", "earth", "metal", "water")
ELEMENT_KO = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}


# --- 에러 코드 -----------------------------------------------------------
class ErrorCode:
    """tool 실패 시 사용하는 표준 에러 코드."""

    INVALID_JSON = "INVALID_JSON"
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_DATE = "INVALID_DATE"
    INVALID_TIME = "INVALID_TIME"
    UNSUPPORTED_CALENDAR = "UNSUPPORTED_CALENDAR"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    MANSERYEOK_ERROR = "MANSERYEOK_ERROR"
    INVALID_SAJU_CHART = "INVALID_SAJU_CHART"
    INVALID_PROFILE = "INVALID_PROFILE"
    INVALID_ELEMENT_ANALYSIS = "INVALID_ELEMENT_ANALYSIS"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


# --- 응답 형식 유틸 ------------------------------------------------------
def success(data: Any) -> dict:
    """성공 응답 dict 를 만든다."""
    return {"ok": True, "data": data}


def failure(code: str, message: str) -> dict:
    """실패 응답 dict 를 만든다."""
    return {"ok": False, "error": {"code": code, "message": message}}


def to_json(payload: dict) -> str:
    """한글이 깨지지 않게 JSON 문자열로 직렬화한다."""
    return json.dumps(payload, ensure_ascii=False)


def success_json(data: Any) -> str:
    return to_json(success(data))


def failure_json(code: str, message: str) -> str:
    return to_json(failure(code, message))


# --- 캘린더 / 만세력 범위 ------------------------------------------------
CALENDAR_TYPES = ("solar", "lunar")

# manseryeok-js (@fullstackfamily/manseryeok) 가 지원하는 연도 범위
SUPPORTED_YEAR_MIN = 1900
SUPPORTED_YEAR_MAX = 2050


# --- 메뉴 / 의도 ---------------------------------------------------------
# tool 이름 상수
TOOL_SAJU_CHART = "calculate_saju_chart"
TOOL_FIVE_ELEMENTS = "analyze_five_elements"
TOOL_TODAY_LUCK = "calculate_today_luck"
TOOL_LUCKY_FACTORS = "recommend_lucky_factors"

# 각 메뉴가 필요로 하는 tool 목록.
# orchestrator 는 이 표를 보고 "필요한 tool 만" 실행한다. (PLAN 10. 메뉴별 실행 흐름)
MENU_REQUIRED_TOOLS = {
    "saju_reading": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS],
    "today_fortune": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS, TOOL_TODAY_LUCK],
    "luck_score": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS, TOOL_TODAY_LUCK],
    "lucky_color": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS, TOOL_LUCKY_FACTORS],
    "lucky_item": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS, TOOL_LUCKY_FACTORS],
    "love": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS],
    "wealth": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS],
    "life_flow": [TOOL_SAJU_CHART, TOOL_FIVE_ELEMENTS],
}

MENU_LABELS_KO = {
    "saju_reading": "사주풀이",
    "today_fortune": "오늘의 운세",
    "luck_score": "오늘의 행운 점수",
    "lucky_color": "행운 색깔",
    "lucky_item": "행운 아이템",
    "love": "연애운",
    "wealth": "재물운",
    "life_flow": "인생흐름",
}

# --- 안전 정책 -----------------------------------------------------------
# 제외(금지) 주제 — 의료/투자/단정 예측 등
EXCLUDED_TOPICS_KO = ["건강운", "질병", "수명", "사고", "투자 수익", "합격", "당첨"]

ANSWER_POLICY = {
    "purpose": "entertainment_and_self_reflection",
    "avoid": ["medical_advice", "investment_advice", "absolute_prediction"],
}

DISCLAIMER_KO = (
    "본 서비스는 전통 명리학 요소를 활용한 엔터테인먼트 및 자기성찰용 챗봇입니다. "
    "의학, 법률, 금융 등 중요한 의사결정의 근거로 사용하지 마세요."
)
