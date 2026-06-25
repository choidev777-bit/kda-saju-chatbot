import json

from src.tools.lucky_factors import LUCKY_FACTOR_PRESETS, recommend_lucky_factors


def _call_recommend_lucky_factors(payload: str) -> dict:
    """Call the tool in both plain-function and LangChain BaseTool environments."""

    if hasattr(recommend_lucky_factors, "invoke"):
        result = recommend_lucky_factors.invoke(payload)
    else:
        result = recommend_lucky_factors(payload)
    return json.loads(result)


def _analysis_payload(recommended_element: str) -> str:
    return json.dumps(
        {
            "ok": True,
            "data": {
                "counts": {
                    "wood": 3,
                    "fire": 2,
                    "earth": 2,
                    "metal": 0,
                    "water": 1,
                },
                "strong_element": "wood",
                "weak_element": recommended_element,
                "recommended_element": recommended_element,
                "missing_elements": [recommended_element],
                "summary": "보완 오행 추천 테스트용 데이터입니다.",
            },
        },
        ensure_ascii=False,
    )


def test_wood_returns_green_and_mint_colors():
    result = _call_recommend_lucky_factors(_analysis_payload("wood"))

    assert result["ok"] is True
    assert result["data"]["recommended_element"] == "wood"
    assert "초록색" in result["data"]["lucky_colors"]
    assert "민트색" in result["data"]["lucky_colors"]


def test_fire_returns_red_pink_purple_colors():
    result = _call_recommend_lucky_factors(_analysis_payload("fire"))

    assert result["ok"] is True
    assert result["data"]["lucky_colors"] == ["빨간색", "분홍색", "보라색"]


def test_earth_returns_yellow_beige_brown_colors():
    result = _call_recommend_lucky_factors(_analysis_payload("earth"))

    assert result["ok"] is True
    assert result["data"]["lucky_colors"] == ["노란색", "베이지색", "갈색"]


def test_metal_returns_white_gold_silver_colors():
    result = _call_recommend_lucky_factors(_analysis_payload("metal"))

    assert result["ok"] is True
    assert result["data"]["lucky_colors"] == ["흰색", "금색", "은색"]


def test_water_returns_black_navy_blue_colors():
    result = _call_recommend_lucky_factors(_analysis_payload("water"))

    assert result["ok"] is True
    assert result["data"]["lucky_colors"] == ["검정색", "남색", "파란색"]


def test_all_elements_return_at_least_three_items():
    for element in LUCKY_FACTOR_PRESETS:
        result = _call_recommend_lucky_factors(_analysis_payload(element))

        assert result["ok"] is True
        assert len(result["data"]["lucky_items"]) >= 3


def test_all_elements_return_reason():
    for element in LUCKY_FACTOR_PRESETS:
        result = _call_recommend_lucky_factors(_analysis_payload(element))

        assert result["ok"] is True
        assert result["data"]["reason"]
        assert "상징" in result["data"]["reason"]
        assert "추천합니다" in result["data"]["reason"]


def test_invalid_json_returns_error_json():
    result = _call_recommend_lucky_factors("not-json")

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ELEMENT_ANALYSIS"


def test_missing_recommended_element_returns_error_json():
    result = _call_recommend_lucky_factors(
        json.dumps({"ok": True, "data": {}}, ensure_ascii=False)
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ELEMENT_ANALYSIS"
    assert "recommended_element" in result["error"]["message"]


def test_unknown_element_returns_error_json():
    result = _call_recommend_lucky_factors(_analysis_payload("lightning"))

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ELEMENT_ANALYSIS"
    assert "wood, fire, earth, metal, water" in result["error"]["message"]
