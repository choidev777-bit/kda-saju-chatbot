"""만세력 계산 tool — 담당: 최연준.

LangChain `@tool` 함수 `calculate_saju_chart`.
사용자 입력 JSON 을 받아 사주팔자(년주/월주/일주/시주) JSON 을 반환한다.

핵심 설계:
- 사주 계산은 LLM 이 직접 하지 않는다. manseryeok-js(@fullstackfamily/manseryeok)
  가 계산을 담당한다. (deterministic)
- Python 은 JS 패키지를 직접 import 할 수 없으므로 Node helper 스크립트를
  subprocess 로 호출한다:  Python -> scripts/calculate_saju.mjs -> 라이브러리.
- 입력 JSON 은 Windows 인자 따옴표 문제를 피하기 위해 stdin 으로 전달한다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .. import config
from ..input_utils import InputValidationError, validate_and_normalize

try:  # 최신 경로 우선, 구버전 호환
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover - 환경별 import 경로 차이
    from langchain.tools import tool

# 프로젝트 루트 기준 Node helper 경로 (src/tools/saju_chart.py -> 루트)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NODE_SCRIPT = _PROJECT_ROOT / "scripts" / "calculate_saju.mjs"
_NODE_TIMEOUT_SEC = 20

# Node helper 의 에러 코드를 우리 계약의 표준 에러 코드로 변환한다.
_NODE_ERROR_MAP = {
    "NODE_OUT_OF_RANGE": config.ErrorCode.OUT_OF_RANGE,
    "NODE_INVALID_DATE": config.ErrorCode.INVALID_DATE,
    "NODE_INVALID_TIME": config.ErrorCode.INVALID_TIME,
    "NODE_INVALID_JSON": config.ErrorCode.INVALID_INPUT,
    "NODE_NO_INPUT": config.ErrorCode.MANSERYEOK_ERROR,
    "NODE_CALC_ERROR": config.ErrorCode.MANSERYEOK_ERROR,
    "NODE_UNEXPECTED": config.ErrorCode.MANSERYEOK_ERROR,
}


def _node_binary() -> str | None:
    """실행 가능한 node 경로를 찾는다. 없으면 None."""
    candidate = os.environ.get("SAJU_NODE_BIN", "node")
    return shutil.which(candidate)


def _call_node_helper(normalized: dict) -> dict:
    """Node helper 를 호출해 만세력 계산 결과 dict 를 돌려준다.

    어떤 실패도 예외로 던지지 않고 {"ok": false, ...} dict 로 변환한다.
    """
    node = _node_binary()
    if node is None:
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR,
            "Node.js 를 찾을 수 없습니다. Node.js 설치 후 다시 시도하세요.",
        )
    if not _NODE_SCRIPT.exists():
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR,
            f"만세력 계산 스크립트를 찾을 수 없습니다: {_NODE_SCRIPT}",
        )

    payload = json.dumps(normalized, ensure_ascii=False)
    try:
        completed = subprocess.run(
            [node, str(_NODE_SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_NODE_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR, "만세력 계산 시간이 초과되었습니다."
        )
    except OSError as exc:
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR, f"Node helper 실행 실패: {exc}"
        )

    stdout = (completed.stdout or "").strip()
    if not stdout:
        # 원시 stderr(스택트레이스·절대경로 등)는 사용자에게 노출하지 않는다. (ARCHITECTURE 11)
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR,
            "만세력 계산에 실패했습니다. 입력을 확인하고 다시 시도해 주세요.",
        )

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR, "만세력 계산 결과를 해석할 수 없습니다."
        )


def _translate_node_error(result: dict) -> dict:
    """Node helper 의 에러 응답을 우리 계약 에러로 변환한다."""
    error = result.get("error") or {}
    node_code = error.get("code", "")
    message = error.get("message", "만세력 계산에 실패했습니다.")
    mapped = _NODE_ERROR_MAP.get(node_code, config.ErrorCode.MANSERYEOK_ERROR)
    return config.failure(mapped, message)


def calculate_saju_chart_impl(user_info_json: str) -> str:
    """`calculate_saju_chart` 의 순수 함수 본체 (테스트/오케스트레이터에서 직접 호출).

    JSON 문자열을 입력받아 JSON 문자열을 반환한다.
    """
    # 1) 입력 JSON 파싱
    try:
        info = json.loads(user_info_json)
    except (json.JSONDecodeError, TypeError):
        return config.failure_json(
            config.ErrorCode.INVALID_JSON,
            "user_info_json 이 올바른 JSON 문자열이 아닙니다.",
        )

    # 2) 입력 검증/정규화
    try:
        normalized = validate_and_normalize(info)
    except InputValidationError as exc:
        return config.failure_json(exc.code, exc.message)

    # 3) Node helper 로 만세력 계산
    result = _call_node_helper(normalized)
    if not result.get("ok"):
        return config.to_json(_translate_node_error(result))

    # 4) 성공 결과를 계약 형식으로 반환
    return config.success_json(result["data"])


@tool
def calculate_saju_chart(user_info_json: str) -> str:
    """사용자의 생년월일, 출생시간, 양력/음력 정보를 바탕으로 사주팔자를 계산한다.

    입력(JSON 문자열): {name, gender, birth_date(YYYY-MM-DD),
        birth_time(HH:MM 또는 null), calendar_type(solar|lunar),
        birth_time_unknown(bool), is_leap_month(bool, 음력일 때만 선택)}.
    출력(JSON 문자열): 성공 시
        {"ok": true, "data": {year_pillar, month_pillar, day_pillar,
        hour_pillar, time_precision, calendar_type, source, ...}},
        실패 시 {"ok": false, "error": {code, message}}.
    출생시간 미상이면 hour_pillar 는 null, time_precision 은 "unknown" 이다.
    """
    return calculate_saju_chart_impl(user_info_json)
