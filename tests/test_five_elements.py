import json

from src.tools.five_elements import (
    EARTHLY_BRANCH_ELEMENTS,
    HEAVENLY_STEM_ELEMENTS,
    analyze_five_elements,
)


def run_tool(payload):
    if not isinstance(payload, str):
        payload = json.dumps(payload, ensure_ascii=False)

    if hasattr(analyze_five_elements, "invoke"):
        result = analyze_five_elements.invoke(payload)
    else:
        result = analyze_five_elements(payload)

    return json.loads(result)


def test_heavenly_stem_element_mapping():
    assert HEAVENLY_STEM_ELEMENTS["갑"] == "wood"
    assert HEAVENLY_STEM_ELEMENTS["을"] == "wood"
    assert HEAVENLY_STEM_ELEMENTS["병"] == "fire"
    assert HEAVENLY_STEM_ELEMENTS["정"] == "fire"
    assert HEAVENLY_STEM_ELEMENTS["무"] == "earth"
    assert HEAVENLY_STEM_ELEMENTS["기"] == "earth"
    assert HEAVENLY_STEM_ELEMENTS["경"] == "metal"
    assert HEAVENLY_STEM_ELEMENTS["신"] == "metal"
    assert HEAVENLY_STEM_ELEMENTS["임"] == "water"
    assert HEAVENLY_STEM_ELEMENTS["계"] == "water"


def test_earthly_branch_element_mapping():
    assert EARTHLY_BRANCH_ELEMENTS["인"] == "wood"
    assert EARTHLY_BRANCH_ELEMENTS["묘"] == "wood"
    assert EARTHLY_BRANCH_ELEMENTS["사"] == "fire"
    assert EARTHLY_BRANCH_ELEMENTS["오"] == "fire"
    assert EARTHLY_BRANCH_ELEMENTS["진"] == "earth"
    assert EARTHLY_BRANCH_ELEMENTS["술"] == "earth"
    assert EARTHLY_BRANCH_ELEMENTS["축"] == "earth"
    assert EARTHLY_BRANCH_ELEMENTS["미"] == "earth"
    assert EARTHLY_BRANCH_ELEMENTS["신"] == "metal"
    assert EARTHLY_BRANCH_ELEMENTS["유"] == "metal"
    assert EARTHLY_BRANCH_ELEMENTS["해"] == "water"
    assert EARTHLY_BRANCH_ELEMENTS["자"] == "water"


def test_counts_elements_and_uses_priority_for_ties():
    result = run_tool(
        {
            "ok": True,
            "data": {
                "year_pillar": "무인",
                "month_pillar": "을묘",
                "day_pillar": "병진",
                "hour_pillar": "정사",
                "time_precision": "known",
            },
        }
    )

    assert result["ok"] is True
    data = result["data"]
    assert data["counts"] == {
        "wood": 3,
        "fire": 3,
        "earth": 2,
        "metal": 0,
        "water": 0,
    }
    assert data["strong_element"] == "wood"
    assert data["weak_element"] == "metal"
    assert data["recommended_element"] == "metal"
    assert data["missing_elements"] == ["metal", "water"]
    assert "목" in data["summary"]
    assert "금" in data["summary"]


def test_hour_pillar_can_be_null():
    result = run_tool(
        {
            "ok": True,
            "data": {
                "year_pillar": "무인",
                "month_pillar": "을묘",
                "day_pillar": "계해",
                "hour_pillar": None,
                "time_precision": "unknown",
            },
        }
    )

    assert result["ok"] is True
    data = result["data"]
    assert data["counts"] == {
        "wood": 3,
        "fire": 0,
        "earth": 1,
        "metal": 0,
        "water": 2,
    }
    assert data["strong_element"] == "wood"
    assert data["weak_element"] == "fire"
    assert data["recommended_element"] == "fire"
    assert data["missing_elements"] == ["fire", "metal"]


def test_raw_chart_data_is_supported_for_local_integration():
    result = run_tool(
        {
            "year_pillar": "무인",
            "month_pillar": "을묘",
            "day_pillar": "병진",
            "hour_pillar": None,
        }
    )

    assert result["ok"] is True
    assert result["data"]["counts"]["wood"] == 3


def test_invalid_json_returns_error_json():
    result = run_tool("{not-json")

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_JSON"


def test_missing_required_pillar_returns_error_json():
    result = run_tool(
        {
            "ok": True,
            "data": {
                "year_pillar": "무인",
                "month_pillar": "을묘",
                "hour_pillar": "정사",
            },
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_SAJU_CHART"


def test_unknown_ganji_returns_error_json():
    result = run_tool(
        {
            "ok": True,
            "data": {
                "year_pillar": "X인",
                "month_pillar": "을묘",
                "day_pillar": "병진",
                "hour_pillar": "정사",
            },
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_SAJU_CHART"


def test_upstream_error_is_preserved_as_tool_error():
    result = run_tool(
        {
            "ok": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "birth_date가 누락되었습니다.",
            },
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "UPSTREAM_TOOL_ERROR"
    assert result["error"]["message"] == "birth_date가 누락되었습니다."
