import json
from datetime import date

from src.tools.today_luck import (
    BASE_SCORE,
    RECOMMENDED_MATCH_BONUS,
    STRONG_MATCH_PENALTY,
    calculate_today_luck,
    calculate_today_luck_payload,
)


def _profile(recommended="metal", weak="water", strong="wood"):
    return json.dumps(
        {
            "ok": True,
            "data": {
                "user": {"name": "민지", "birth_date": "1998-03-12"},
                "five_elements": {
                    "counts": {
                        "wood": 3,
                        "fire": 2,
                        "earth": 2,
                        "metal": 0,
                        "water": 1,
                    },
                    "strong_element": strong,
                    "weak_element": weak,
                    "recommended_element": recommended,
                },
            },
        },
        ensure_ascii=False,
    )


def test_normal_profile_returns_ok_true_and_required_fields():
    result = calculate_today_luck_payload(_profile(), target_date=date(2026, 6, 24))

    assert result["ok"] is True
    data = result["data"]
    assert data["date"] == "2026-06-24"
    assert 0 <= data["score"] <= 100
    assert data["score_range"] == "0-100"
    assert data["today_element"] in {"wood", "fire", "earth", "metal", "water"}
    assert data["signals"]
    assert data["cautions"]


def test_direct_analyze_five_elements_result_is_accepted():
    direct_result = json.dumps(
        {
            "recommended_element": "metal",
            "weak_element": "water",
            "strong_element": "wood",
        }
    )

    result = calculate_today_luck_payload(direct_result, target_date=date(2026, 6, 24))

    assert result["ok"] is True
    assert result["data"]["recommended_element"] == "metal"


def test_recommended_element_match_adds_bonus():
    # 2026-06-24 maps to metal with the MVP date rule.
    result = calculate_today_luck_payload(
        _profile(recommended="metal", weak="water", strong="wood"),
        target_date=date(2026, 6, 24),
    )

    assert result["ok"] is True
    assert result["data"]["today_element"] == "metal"
    assert result["data"]["score"] >= BASE_SCORE + RECOMMENDED_MATCH_BONUS


def test_recommended_equals_weak_no_double_bonus():
    profile = _profile(recommended="metal", weak="metal", strong="wood")

    result = calculate_today_luck_payload(profile, target_date=date(2026, 6, 24))

    assert result["ok"] is True
    assert result["data"]["today_element"] == "metal"
    assert result["data"]["score"] == 83


def test_strong_element_match_applies_penalty():
    # 2026-06-21 maps to wood with the MVP date rule.
    result = calculate_today_luck_payload(
        _profile(recommended="metal", weak="water", strong="wood"),
        target_date=date(2026, 6, 21),
    )

    assert result["ok"] is True
    assert result["data"]["today_element"] == "wood"
    assert result["data"]["score"] == BASE_SCORE - STRONG_MATCH_PENALTY


def test_non_string_date_returns_invalid_date():
    payload = json.loads(_profile())
    payload["date"] = 20260624

    result = calculate_today_luck_payload(json.dumps(payload, ensure_ascii=False))

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_DATE"


def test_profile_data_date_is_used_for_score_date():
    payload = json.loads(_profile(recommended="metal", weak="metal", strong="wood"))
    payload["data"]["date"] = "2026-06-24"

    result = calculate_today_luck_payload(json.dumps(payload, ensure_ascii=False))

    assert result["ok"] is True
    assert result["data"]["date"] == "2026-06-24"
    assert result["data"]["today_element"] == "metal"
    assert result["data"]["score"] == 83


def test_element_values_are_normalized_before_validation():
    profile = _profile(recommended="Metal", weak=" water ", strong="WOOD")

    result = calculate_today_luck_payload(profile, target_date=date(2026, 6, 24))

    assert result["ok"] is True
    assert result["data"]["recommended_element"] == "metal"
    assert result["data"]["today_element"] == "metal"


def test_invalid_json_returns_error_json():
    result = calculate_today_luck_payload("{not json")

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_JSON"


def test_missing_recommended_element_returns_error_json():
    result = calculate_today_luck_payload(
        json.dumps({"five_elements": {"weak_element": "water", "strong_element": "wood"}})
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_PROFILE"
    assert "recommended_element" in result["error"]["message"]


def test_langchain_tool_returns_json_string():
    result = json.loads(calculate_today_luck.invoke(_profile()))

    assert result["ok"] is True
    assert "score" in result["data"]
