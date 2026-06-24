"""Lucky color and item recommendation tool for the saju chatbot.

This module implements 전원정 담당 Tool 4:
`recommend_lucky_factors(element_analysis_json: str) -> str`.

The tool receives the successful JSON string returned by
`analyze_five_elements`, reads `data.recommended_element`, and returns a
structured JSON string that the LLM can use directly for a Korean response.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, TypedDict

try:  # Preferred import used in the project documents.
    from langchain.tools import tool
except ModuleNotFoundError:  # pragma: no cover - compatibility for newer LangChain.
    try:
        from langchain_core.tools import tool
    except ModuleNotFoundError:  # pragma: no cover - lets unit tests run before deps are installed.
        def tool(func):  # type: ignore[no-redef]
            """Fallback decorator for local tests when LangChain is not installed."""

            return func


class LuckyFactorPreset(TypedDict):
    """Recommendation preset for one five-element value."""

    colors: List[str]
    items: List[str]
    reason: str


ERROR_CODE = "INVALID_ELEMENT_ANALYSIS"
SUPPORTED_ELEMENTS = {"wood", "fire", "earth", "metal", "water"}

LUCKY_FACTOR_PRESETS: Mapping[str, LuckyFactorPreset] = {
    "wood": {
        "colors": ["초록색", "민트색", "연두색"],
        "items": ["식물", "노트", "나무 소재 소품"],
        "reason": "목 기운은 성장, 시작, 정리의 상징으로 해석되어 오늘의 보완 요소로 추천합니다.",
    },
    "fire": {
        "colors": ["빨간색", "분홍색", "보라색"],
        "items": ["조명", "향초", "따뜻한 음료"],
        "reason": "화 기운은 활력, 표현, 자신감의 상징으로 해석되어 오늘의 보완 요소로 추천합니다.",
    },
    "earth": {
        "colors": ["노란색", "베이지색", "갈색"],
        "items": ["다이어리", "머그컵", "쿠션"],
        "reason": "토 기운은 안정, 균형, 현실감의 상징으로 해석되어 오늘의 보완 요소로 추천합니다.",
    },
    "metal": {
        "colors": ["흰색", "금색", "은색"],
        "items": ["시계", "펜", "금속 액세서리"],
        "reason": "금 기운은 집중, 판단, 정돈의 상징으로 해석되어 오늘의 보완 요소로 추천합니다.",
    },
    "water": {
        "colors": ["검정색", "남색", "파란색"],
        "items": ["물병", "향수", "이어폰"],
        "reason": "수 기운은 차분함, 유연함, 회복의 상징으로 해석되어 오늘의 보완 요소로 추천합니다.",
    },
}


def _json_response(payload: Dict[str, Any]) -> str:
    """Serialize a response using Korean-friendly JSON output."""

    return json.dumps(payload, ensure_ascii=False)


def _error_response(message: str) -> str:
    """Return a structured error JSON string without raising an app-level error."""

    return _json_response(
        {
            "ok": False,
            "error": {
                "code": ERROR_CODE,
                "message": message,
            },
        }
    )


def _extract_recommended_element(payload: Mapping[str, Any]) -> str | None:
    """Read `data.recommended_element` from the five-elements analysis result."""

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None

    recommended_element = data.get("recommended_element")
    if not isinstance(recommended_element, str):
        return None

    recommended_element = recommended_element.strip().lower()
    return recommended_element or None


@tool
def recommend_lucky_factors(element_analysis_json: str) -> str:
    """보완 오행을 기준으로 행운 색깔과 행운 아이템을 추천한다."""

    try:
        payload = json.loads(element_analysis_json)
    except json.JSONDecodeError:
        return _error_response("입력값은 올바른 JSON 문자열이어야 합니다.")

    if not isinstance(payload, dict):
        return _error_response("입력 JSON은 객체 형식이어야 합니다.")

    if payload.get("ok") is False:
        return _error_response("오행 분석 결과가 성공 상태가 아닙니다.")

    recommended_element = _extract_recommended_element(payload)
    if recommended_element is None:
        return _error_response("recommended_element가 필요합니다.")

    if recommended_element not in SUPPORTED_ELEMENTS:
        return _error_response(
            "recommended_element는 wood, fire, earth, metal, water 중 하나여야 합니다."
        )

    preset = LUCKY_FACTOR_PRESETS[recommended_element]
    return _json_response(
        {
            "ok": True,
            "data": {
                "recommended_element": recommended_element,
                "lucky_colors": preset["colors"],
                "lucky_items": preset["items"],
                "reason": preset["reason"],
            },
        }
    )


__all__ = ["recommend_lucky_factors", "LUCKY_FACTOR_PRESETS"]
