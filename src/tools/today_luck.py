"""Today luck score tool.

This module implements Choi Hotaek's assigned LangChain tool. It consumes the
five-elements analysis produced by ``analyze_five_elements`` and returns a
structured JSON payload that the LLM can explain in natural Korean.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

try:
    from langchain.tools import tool
except ImportError:  # pragma: no cover - keeps tests runnable before deps install.
    try:
        from langchain_core.tools import tool
    except ImportError:  # pragma: no cover
        def tool(func):
            func.invoke = lambda tool_input: func(tool_input)
            return func


ELEMENTS = ("wood", "fire", "earth", "metal", "water")
ELEMENT_LABELS = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}

BASE_SCORE = 70
RECOMMENDED_MATCH_BONUS = 10
WEAK_MATCH_BONUS = 8
BALANCE_BONUS = 3
STRONG_MATCH_PENALTY = 5
LIMITED_INTERPRETATION_PENALTY = 5


def _success(data: dict[str, Any]) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _error(code: str, message: str) -> str:
    return json.dumps(
        {"ok": False, "error": {"code": code, "message": message}},
        ensure_ascii=False,
    )


def _clamp_score(score: int) -> int:
    return max(0, min(100, score))


def _today_element_for_date(target_date: date) -> str:
    """Return a deterministic per-date MVP element.

    The offset keeps the architecture document's example date, 2026-06-24,
    aligned with ``metal``. This guarantees the same result for the same date,
    but does not guarantee smooth or evenly distributed day-by-day cycling.
    """
    numeric_date = int(target_date.strftime("%Y%m%d"))
    return ELEMENTS[(numeric_date + 4) % len(ELEMENTS)]


def _parse_date(value: Any) -> date:
    if not value:
        return date.today()
    if not isinstance(value, str):
        raise ValueError("date must be a YYYY-MM-DD string.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("date는 YYYY-MM-DD 형식이어야 합니다.") from exc


def _extract_date_value(payload: dict[str, Any]) -> Any:
    if payload.get("date") not in (None, ""):
        return payload.get("date")

    data = payload.get("data")
    if isinstance(data, dict):
        return data.get("date")

    return None


def _extract_five_elements(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Accept either full profile JSON or direct analyze_five_elements output."""
    if payload.get("ok") is True and isinstance(payload.get("data"), dict):
        payload = payload["data"]

    five_elements = payload.get("five_elements")
    if isinstance(five_elements, dict):
        return five_elements

    if any(key in payload for key in ("recommended_element", "weak_element", "strong_element")):
        return payload

    return None


def _validate_element(value: Any, field_name: str, required: bool = True) -> tuple[str | None, str | None]:
    if value is None:
        if required:
            return None, f"five_elements.{field_name}가 필요합니다."
        return None, None
    normalized = str(value).strip().lower()
    if normalized == "":
        if required:
            return _validate_element(None, field_name, required=True)
        return None, None

    if normalized not in ELEMENTS:
        allowed = ", ".join(ELEMENTS)
        return None, f"five_elements.{field_name}는 {allowed} 중 하나여야 합니다."
    return normalized, None


def _build_signals(
    today_element: str,
    recommended_element: str,
    weak_element: str | None,
    strong_element: str | None,
) -> list[str]:
    today_label = ELEMENT_LABELS[today_element]
    recommended_label = ELEMENT_LABELS[recommended_element]
    signals = []

    if today_element == recommended_element:
        signals.append(
            f"오늘의 {today_label} 기운이 보완 오행과 잘 맞아 균형감을 높이는 흐름입니다."
        )
    elif weak_element and today_element == weak_element:
        signals.append(
            f"오늘의 {today_label} 기운이 약한 오행을 보완해 차분히 정리하기 좋은 흐름입니다."
        )
    elif strong_element and today_element != strong_element:
        signals.append(
            f"오늘의 {today_label} 기운이 이미 강한 기운과 달라 새로운 균형점을 찾는 데 도움이 됩니다."
        )
    else:
        signals.append(
            f"오늘은 보완 오행인 {recommended_label} 기운을 의식하며 균형을 맞추기 좋은 날로 해석됩니다."
        )

    signals.append("점수는 사주 프로필의 오행 균형과 오늘 날짜의 오행을 코드 규칙으로 비교해 계산했습니다.")
    return signals


def _build_cautions(today_element: str, strong_element: str | None, limited: bool) -> list[str]:
    cautions = ["좋은 흐름이 있어도 중요한 결정은 한 번 더 확인하는 편이 좋습니다."]

    if strong_element and today_element == strong_element:
        strong_label = ELEMENT_LABELS[strong_element]
        cautions.append(
            f"오늘은 이미 강한 {strong_label} 기운이 더 두드러질 수 있어 한쪽으로 치우치지 않게 조절해보세요."
        )

    if limited:
        cautions.append("일부 오행 정보가 부족해 제한적인 기준으로 해석했습니다.")

    return cautions


def calculate_today_luck_payload(profile_json: str, target_date: date | None = None) -> dict[str, Any]:
    """Pure helper for tests and orchestration code."""
    try:
        payload = json.loads(profile_json)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"code": "INVALID_JSON", "message": "올바른 JSON 문자열이 아닙니다."}}

    if not isinstance(payload, dict):
        return {"ok": False, "error": {"code": "INVALID_PROFILE", "message": "프로필 JSON은 객체여야 합니다."}}

    try:
        score_date = _parse_date(_extract_date_value(payload)) if target_date is None else target_date
    except ValueError as exc:
        return {"ok": False, "error": {"code": "INVALID_DATE", "message": str(exc)}}

    five_elements = _extract_five_elements(payload)
    if five_elements is None:
        return {
            "ok": False,
            "error": {
                "code": "INVALID_PROFILE",
                "message": "five_elements 또는 analyze_five_elements 결과가 필요합니다.",
            },
        }

    recommended_element, validation_error = _validate_element(
        five_elements.get("recommended_element"),
        "recommended_element",
        required=True,
    )
    if validation_error:
        return {"ok": False, "error": {"code": "INVALID_PROFILE", "message": validation_error}}

    weak_element, validation_error = _validate_element(
        five_elements.get("weak_element"),
        "weak_element",
        required=False,
    )
    if validation_error:
        return {"ok": False, "error": {"code": "INVALID_PROFILE", "message": validation_error}}

    strong_element, validation_error = _validate_element(
        five_elements.get("strong_element"),
        "strong_element",
        required=False,
    )
    if validation_error:
        return {"ok": False, "error": {"code": "INVALID_PROFILE", "message": validation_error}}

    today_element = _today_element_for_date(score_date)
    score = BASE_SCORE
    limited = weak_element is None or strong_element is None

    if today_element == recommended_element:
        score += RECOMMENDED_MATCH_BONUS
    elif weak_element and today_element == weak_element:
        score += WEAK_MATCH_BONUS

    if strong_element and today_element == strong_element:
        score -= STRONG_MATCH_PENALTY
    elif strong_element:
        score += BALANCE_BONUS

    if limited:
        score -= LIMITED_INTERPRETATION_PENALTY

    return {
        "ok": True,
        "data": {
            "date": score_date.isoformat(),
            "score": _clamp_score(score),
            "score_range": "0-100",
            "today_element": today_element,
            "recommended_element": recommended_element,
            "signals": _build_signals(today_element, recommended_element, weak_element, strong_element),
            "cautions": _build_cautions(today_element, strong_element, limited),
        },
    }


@tool
def calculate_today_luck(profile_json: str) -> str:
    """사용자 사주 프로필과 오늘 날짜의 기운을 비교해 오늘의 행운 점수를 계산한다."""
    result = calculate_today_luck_payload(profile_json)
    if result.get("ok") is True:
        return _success(result["data"])
    return json.dumps(result, ensure_ascii=False)
