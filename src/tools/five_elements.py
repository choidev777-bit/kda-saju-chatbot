"""Five-elements analysis tool for saju chart results."""

from __future__ import annotations

import json
from typing import Any

try:
    from langchain.tools import tool
except Exception:  # pragma: no cover - only used when LangChain is unavailable locally.
    try:
        from langchain_core.tools import tool
    except Exception:  # pragma: no cover

        def tool(func):
            def invoke(tool_input: str) -> str:
                return func(tool_input)

            func.invoke = invoke
            return func


ELEMENT_ORDER = ("wood", "fire", "earth", "metal", "water")

ELEMENT_LABELS_KO = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}

HEAVENLY_STEM_ELEMENTS = {
    "갑": "wood",
    "을": "wood",
    "병": "fire",
    "정": "fire",
    "무": "earth",
    "기": "earth",
    "경": "metal",
    "신": "metal",
    "임": "water",
    "계": "water",
}

EARTHLY_BRANCH_ELEMENTS = {
    "인": "wood",
    "묘": "wood",
    "사": "fire",
    "오": "fire",
    "진": "earth",
    "술": "earth",
    "축": "earth",
    "미": "earth",
    "신": "metal",
    "유": "metal",
    "해": "water",
    "자": "water",
}

PILLARS = (
    ("year_pillar", True),
    ("month_pillar", True),
    ("day_pillar", True),
    ("hour_pillar", False),
)


def _json_ok(data: dict[str, Any]) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _json_error(code: str, message: str) -> str:
    return json.dumps(
        {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
        ensure_ascii=False,
    )


def _load_payload(raw_json: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return None, _json_error("INVALID_JSON", "입력값은 JSON 문자열이어야 합니다.")

    if not isinstance(payload, dict):
        return None, _json_error("INVALID_INPUT", "입력 JSON은 객체 형식이어야 합니다.")

    if payload.get("ok") is False:
        upstream_error = payload.get("error")
        if isinstance(upstream_error, dict):
            message = upstream_error.get("message") or "이전 tool 결과가 실패 상태입니다."
        else:
            message = "이전 tool 결과가 실패 상태입니다."
        return None, _json_error("UPSTREAM_TOOL_ERROR", message)

    if payload.get("ok") is True:
        data = payload.get("data")
        if not isinstance(data, dict):
            return None, _json_error("INVALID_SAJU_CHART", "data 객체가 누락되었습니다.")
        return data, None

    if "ok" not in payload:
        return payload, None

    return None, _json_error("INVALID_SAJU_CHART", "ok value must be true or false.")


def _normalize_pillar(
    data: dict[str, Any], key: str, *, required: bool
) -> tuple[str | None, str | None]:
    value = data.get(key)

    if value in (None, "") and not required:
        return None, None

    if value in (None, "") and required:
        return None, _json_error(
            "INVALID_SAJU_CHART",
            "year_pillar, month_pillar, day_pillar 중 하나가 누락되었습니다.",
        )

    if not isinstance(value, str):
        return None, _json_error("INVALID_SAJU_CHART", f"{key}는 문자열이어야 합니다.")

    pillar = value.strip()
    if len(pillar) != 2:
        return None, _json_error(
            "INVALID_SAJU_CHART",
            f"{key}는 천간과 지지로 이루어진 두 글자 간지여야 합니다.",
        )

    stem, branch = pillar[0], pillar[1]
    if stem not in HEAVENLY_STEM_ELEMENTS:
        return None, _json_error("INVALID_SAJU_CHART", f"알 수 없는 천간입니다: {stem}")
    if branch not in EARTHLY_BRANCH_ELEMENTS:
        return None, _json_error("INVALID_SAJU_CHART", f"알 수 없는 지지입니다: {branch}")

    return pillar, None


def _pick_element_by_priority(counts: dict[str, int], target_count: int) -> str:
    for element in ELEMENT_ORDER:
        if counts[element] == target_count:
            return element
    raise ValueError("target_count does not exist in counts")


def _build_summary(strong_element: str, weak_element: str, missing_elements: list[str]) -> str:
    strong_label = ELEMENT_LABELS_KO[strong_element]
    weak_label = ELEMENT_LABELS_KO[weak_element]

    if missing_elements:
        return f"{strong_label} 기운이 강하고 {weak_label} 기운이 부족한 구조입니다."
    return f"{strong_label} 기운이 상대적으로 강하고 {weak_label} 기운을 보완하면 좋은 구조입니다."


@tool
def analyze_five_elements(saju_chart_json: str) -> str:
    """사주팔자 데이터를 바탕으로 목, 화, 토, 금, 수 오행의 강약을 분석한다."""

    data, error = _load_payload(saju_chart_json)
    if error:
        return error
    if data is None:
        return _json_error("INVALID_SAJU_CHART", "분석할 사주 데이터가 없습니다.")

    counts = {element: 0 for element in ELEMENT_ORDER}

    for key, required in PILLARS:
        pillar, error = _normalize_pillar(data, key, required=required)
        if error:
            return error
        if pillar is None:
            continue
        stem, branch = pillar[0], pillar[1]
        counts[HEAVENLY_STEM_ELEMENTS[stem]] += 1
        counts[EARTHLY_BRANCH_ELEMENTS[branch]] += 1

    max_count = max(counts.values())
    min_count = min(counts.values())
    strong_element = _pick_element_by_priority(counts, max_count)
    weak_element = _pick_element_by_priority(counts, min_count)
    missing_elements = [element for element in ELEMENT_ORDER if counts[element] == 0]

    result = {
        "counts": counts,
        "strong_element": strong_element,
        "weak_element": weak_element,
        "recommended_element": weak_element,
        "missing_elements": missing_elements,
        "summary": _build_summary(strong_element, weak_element, missing_elements),
    }
    return _json_ok(result)
