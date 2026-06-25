"""입력 검증 공통 유틸 테스트."""
import pytest

from src.config import ErrorCode
from src.input_utils import InputValidationError, validate_and_normalize


def test_valid_input_is_normalized():
    out = validate_and_normalize(
        {
            "name": "  민지 ",
            "gender": "female",
            "birth_date": "1998-03-12",
            "birth_time": "09:00",
            "calendar_type": "solar",
            "birth_time_unknown": False,
        }
    )
    assert out["name"] == "민지"  # 공백 제거
    assert out["birth_time"] == "09:00"
    assert out["birth_time_unknown"] is False
    assert out["is_leap_month"] is False


def test_missing_name_raises():
    with pytest.raises(InputValidationError) as exc:
        validate_and_normalize({"birth_date": "1998-03-12", "calendar_type": "solar"})
    assert exc.value.code == ErrorCode.INVALID_INPUT


def test_bad_date_raises():
    with pytest.raises(InputValidationError) as exc:
        validate_and_normalize(
            {"name": "민지", "birth_date": "98-3-12", "calendar_type": "solar"}
        )
    assert exc.value.code == ErrorCode.INVALID_DATE


def test_bad_calendar_raises():
    with pytest.raises(InputValidationError) as exc:
        validate_and_normalize(
            {"name": "민지", "birth_date": "1998-03-12", "calendar_type": "음력"}
        )
    assert exc.value.code == ErrorCode.UNSUPPORTED_CALENDAR


def test_time_unknown_flag_nulls_time():
    out = validate_and_normalize(
        {
            "name": "민지",
            "birth_date": "1998-03-12",
            "birth_time": "09:00",
            "calendar_type": "solar",
            "birth_time_unknown": True,
        }
    )
    # 미상 플래그가 우선한다.
    assert out["birth_time"] is None
    assert out["birth_time_unknown"] is True


def test_empty_time_treated_as_unknown():
    out = validate_and_normalize(
        {
            "name": "민지",
            "birth_date": "1998-03-12",
            "birth_time": "",
            "calendar_type": "solar",
        }
    )
    assert out["birth_time"] is None
    assert out["birth_time_unknown"] is True


def test_bad_time_raises():
    with pytest.raises(InputValidationError) as exc:
        validate_and_normalize(
            {
                "name": "민지",
                "birth_date": "1998-03-12",
                "birth_time": "25:99",
                "calendar_type": "solar",
            }
        )
    assert exc.value.code == ErrorCode.INVALID_TIME


def test_out_of_range_year_raises():
    for bad in ("1850-06-15", "2100-01-01"):
        with pytest.raises(InputValidationError) as exc:
            validate_and_normalize(
                {"name": "민지", "birth_date": bad, "calendar_type": "solar"}
            )
        assert exc.value.code == ErrorCode.OUT_OF_RANGE


def test_gender_defaults_to_unknown_when_missing():
    out = validate_and_normalize(
        {"name": "민지", "birth_date": "1998-03-12", "calendar_type": "solar"}
    )
    assert out["gender"] == "unknown"


def test_single_digit_minute_is_normalized():
    # '9:5' 는 strptime 을 통과하므로 zero-pad 정규화로 Node 정규식과 형식을 맞춘다.
    out = validate_and_normalize(
        {
            "name": "민지",
            "birth_date": "1998-03-12",
            "birth_time": "9:5",
            "calendar_type": "solar",
        }
    )
    assert out["birth_time"] == "09:05"
