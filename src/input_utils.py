"""사용자 입력 검증 공통 유틸.

입력 검증은 모든 기능이 공유하는 전처리라서 별도 LangChain tool 로 만들지 않고
공통 유틸 함수로 둔다. (ARCHITECTURE 17.1)
"""
from __future__ import annotations

from datetime import datetime

from . import config


class InputValidationError(Exception):
    """입력 검증 실패. code 와 message 를 담아 tool 의 에러 JSON 으로 변환된다."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


REQUIRED_FIELDS = ("name", "birth_date", "calendar_type")

# birth_time 이 이 값들 중 하나면 "출생시간 미상" 으로 본다.
_TIME_UNKNOWN_SENTINELS = (None, "", "unknown", "모름", "미상")


def _validate_date(birth_date: object) -> str:
    if not isinstance(birth_date, str):
        raise InputValidationError(
            config.ErrorCode.INVALID_DATE, "birth_date 는 문자열이어야 합니다."
        )
    try:
        parsed = datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        raise InputValidationError(
            config.ErrorCode.INVALID_DATE,
            "birth_date 는 YYYY-MM-DD 형식의 실제 날짜여야 합니다. 예: 1998-03-12",
        )
    # 만세력 지원 범위를 Python 단에서 결정적으로 보장한다(불필요한 subprocess 호출 방지).
    # 음력은 변환 후 연도가 1년 달라질 수 있어 Node 의 OUT_OF_RANGE 가 2차 안전망이 된다.
    if not (config.SUPPORTED_YEAR_MIN <= parsed.year <= config.SUPPORTED_YEAR_MAX):
        raise InputValidationError(
            config.ErrorCode.OUT_OF_RANGE,
            f"지원 연도는 {config.SUPPORTED_YEAR_MIN}~{config.SUPPORTED_YEAR_MAX} 입니다. "
            f"(입력 연도: {parsed.year})",
        )
    return birth_date


def _validate_time(birth_time: object) -> str:
    if not isinstance(birth_time, str):
        raise InputValidationError(
            config.ErrorCode.INVALID_TIME, "birth_time 은 HH:MM 형식이어야 합니다. 예: 09:00"
        )
    try:
        parsed = datetime.strptime(birth_time, "%H:%M")
    except ValueError:
        raise InputValidationError(
            config.ErrorCode.INVALID_TIME,
            "birth_time 은 00:00~23:59 사이의 HH:MM 형식이어야 합니다. 예: 09:00",
        )
    # 항상 zero-pad 된 HH:MM 으로 정규화한다 ('9:5' -> '09:05').
    # Node helper 정규식이 분 2자리를 요구하므로 계층 간 형식을 일치시킨다.
    return parsed.strftime("%H:%M")


def validate_and_normalize(info: object) -> dict:
    """사용자 입력 dict 를 검증하고 계산기에 넘길 정규화 dict 로 변환한다.

    실패 시 InputValidationError 를 던진다.
    """
    if not isinstance(info, dict):
        raise InputValidationError(
            config.ErrorCode.INVALID_INPUT, "입력은 JSON 객체여야 합니다."
        )

    # 필수 필드 확인
    for field in REQUIRED_FIELDS:
        value = info.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise InputValidationError(
                config.ErrorCode.INVALID_INPUT,
                f"필수 항목 '{field}' 이(가) 누락되었습니다.",
            )

    # 캘린더 종류
    calendar_type = info.get("calendar_type")
    if calendar_type not in config.CALENDAR_TYPES:
        raise InputValidationError(
            config.ErrorCode.UNSUPPORTED_CALENDAR,
            "calendar_type 은 'solar'(양력) 또는 'lunar'(음력) 여야 합니다.",
        )

    # 날짜
    birth_date = _validate_date(info.get("birth_date"))

    # 시간 / 출생시간 미상
    time_unknown = bool(info.get("birth_time_unknown", False))
    birth_time = info.get("birth_time")
    if time_unknown or birth_time in _TIME_UNKNOWN_SENTINELS:
        time_unknown = True
        birth_time = None
    else:
        birth_time = _validate_time(birth_time)

    return {
        "name": str(info.get("name")).strip(),
        "gender": info.get("gender", "unknown"),
        "birth_date": birth_date,
        "birth_time": birth_time,
        "calendar_type": calendar_type,
        "birth_time_unknown": time_unknown,
        "is_leap_month": bool(info.get("is_leap_month", False)),
    }
