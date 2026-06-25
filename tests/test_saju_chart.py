"""calculate_saju_chart tool 테스트 — 담당: 최연준.

실제 Node helper(manseryeok-js)를 호출하는 통합 테스트다.
실행 전제: Node.js 설치 + `npm install` 완료.
"""
import json

import pytest

from src.config import ErrorCode
from src.tools.saju_chart import calculate_saju_chart, calculate_saju_chart_impl


def run(payload: dict) -> dict:
    """dict 입력을 JSON 문자열로 만들어 tool 본체를 호출하고 결과 dict 를 돌려준다."""
    return json.loads(calculate_saju_chart_impl(json.dumps(payload, ensure_ascii=False)))


# --- 정상 케이스 --------------------------------------------------------
def test_solar_known_time_returns_ok():
    result = run(
        {
            "name": "민지",
            "gender": "female",
            "birth_date": "1998-03-12",
            "birth_time": "09:00",
            "calendar_type": "solar",
            "birth_time_unknown": False,
        }
    )
    assert result["ok"] is True
    data = result["data"]
    for key in ("year_pillar", "month_pillar", "day_pillar", "hour_pillar",
                "time_precision", "calendar_type", "source"):
        assert key in data
    assert data["time_precision"] == "known"
    assert data["source"]


def test_solar_known_time_matches_verified_values():
    """검증된 기준값 고정: 1998-03-12 09:00 양력."""
    result = run(
        {
            "name": "민지",
            "birth_date": "1998-03-12",
            "birth_time": "09:00",
            "calendar_type": "solar",
        }
    )
    data = result["data"]
    assert data["year_pillar"] == "무인"
    assert data["month_pillar"] == "을묘"
    assert data["day_pillar"] == "무오"
    assert data["hour_pillar"] == "병진"


def test_birth_time_unknown_sets_null_hour_pillar():
    result = run(
        {
            "name": "민지",
            "birth_date": "1998-03-12",
            "birth_time": None,
            "calendar_type": "solar",
            "birth_time_unknown": True,
        }
    )
    assert result["ok"] is True
    data = result["data"]
    assert data["hour_pillar"] is None
    assert data["time_precision"] == "unknown"
    # 시간과 무관한 3개 기둥은 여전히 채워진다.
    assert data["year_pillar"] and data["month_pillar"] and data["day_pillar"]


def test_lunar_input_returns_ok():
    result = run(
        {
            "name": "민지",
            "birth_date": "1998-02-14",
            "birth_time": "09:00",
            "calendar_type": "lunar",
        }
    )
    assert result["ok"] is True
    assert result["data"]["calendar_type"] == "lunar"


def test_same_input_is_deterministic():
    payload = {
        "name": "민지",
        "birth_date": "2000-01-01",
        "birth_time": "12:30",
        "calendar_type": "solar",
    }
    first = run(payload)
    second = run(payload)
    assert first == second


# --- 실패 케이스 --------------------------------------------------------
def test_invalid_json_returns_error():
    result = json.loads(calculate_saju_chart_impl("이건 JSON 이 아님"))
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.INVALID_JSON


def test_missing_required_field_returns_error():
    result = run({"birth_date": "1998-03-12", "calendar_type": "solar"})  # name 누락
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.INVALID_INPUT


def test_invalid_date_format_returns_error():
    result = run(
        {"name": "민지", "birth_date": "1998/03/12", "calendar_type": "solar"}
    )
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.INVALID_DATE


def test_impossible_date_returns_error():
    result = run(
        {"name": "민지", "birth_date": "1998-13-40", "calendar_type": "solar"}
    )
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.INVALID_DATE


def test_invalid_time_format_returns_error():
    result = run(
        {
            "name": "민지",
            "birth_date": "1998-03-12",
            "birth_time": "9시",
            "calendar_type": "solar",
        }
    )
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.INVALID_TIME


def test_unsupported_calendar_returns_error():
    result = run(
        {"name": "민지", "birth_date": "1998-03-12", "calendar_type": "gregorian"}
    )
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.UNSUPPORTED_CALENDAR


def test_out_of_range_year_returns_error():
    result = run(
        {
            "name": "민지",
            "birth_date": "1850-01-01",
            "birth_time": "09:00",
            "calendar_type": "solar",
        }
    )
    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.OUT_OF_RANGE


# --- @tool 등록 확인 ----------------------------------------------------
def test_calculate_saju_chart_is_registered_tool():
    assert calculate_saju_chart.name == "calculate_saju_chart"
    assert calculate_saju_chart.description  # docstring 기반 설명 존재


def test_tool_invoke_interface_works():
    raw = calculate_saju_chart.invoke(
        {
            "user_info_json": json.dumps(
                {
                    "name": "민지",
                    "birth_date": "1998-03-12",
                    "birth_time": "09:00",
                    "calendar_type": "solar",
                },
                ensure_ascii=False,
            )
        }
    )
    result = json.loads(raw)
    assert result["ok"] is True


def test_lunar_leap_month_returns_ok():
    # 2020년에는 음력 윤4월이 존재한다. 윤달 경로(is_leap_month=True)를 검증한다.
    result = run(
        {
            "name": "민지",
            "birth_date": "2020-04-01",
            "birth_time": "09:00",
            "calendar_type": "lunar",
            "is_leap_month": True,
        }
    )
    assert result["ok"] is True
    assert result["data"]["lunar_input"]["is_leap_month"] is True
