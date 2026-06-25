"""오케스트레이터 통합 테스트.

팀원 도구(②③④)는 아직 구현 전이므로, 계약 기반 '테스트 더블' 을 레지스트리에
주입해 통합 흐름을 검증한다. 실제 만세력 계산(①)은 진짜 Node helper 를 쓴다.
"""
import json

import pytest

from src import config, prompts
from src.orchestrator import Orchestrator, default_registry
from src.tools.saju_chart import calculate_saju_chart_impl

USER_JSON = json.dumps(
    {
        "name": "민지",
        "gender": "female",
        "birth_date": "1998-03-12",
        "birth_time": "09:00",
        "calendar_type": "solar",
    },
    ensure_ascii=False,
)


# --- 계약 기반 테스트 더블 (팀원 도구 대역) -----------------------------
def fake_five_elements(saju_chart_json: str) -> str:
    payload = json.loads(saju_chart_json)
    assert payload.get("ok") is True  # 이윤서 계약: 전체 성공 JSON 을 받는다
    return config.to_json(
        config.success(
            {
                "counts": {"wood": 3, "fire": 2, "earth": 2, "metal": 0, "water": 1},
                "strong_element": "wood",
                "weak_element": "metal",
                "recommended_element": "metal",
                "missing_elements": ["metal"],
                "summary": "목 기운이 강하고 금 기운이 부족한 구조입니다.",
            }
        )
    )


def fake_today_luck(profile_json: str) -> str:
    payload = json.loads(profile_json)
    fe = payload["data"]["five_elements"]
    assert fe["recommended_element"]  # 최호택 계약: profile 안 five_elements 사용
    return config.to_json(
        config.success(
            {
                "date": "2026-06-24",
                "score": 82,
                "score_range": "0-100",
                "today_element": "metal",
                "recommended_element": fe["recommended_element"],
                "signals": ["오늘의 기운이 보완 오행과 잘 맞습니다."],
                "cautions": ["중요한 결정은 한 번 더 확인하세요."],
            }
        )
    )


def fake_lucky_factors(element_analysis_json: str) -> str:
    payload = json.loads(element_analysis_json)
    rec = payload["data"]["recommended_element"]  # 전원정 계약
    return config.to_json(
        config.success(
            {
                "recommended_element": rec,
                "lucky_colors": ["흰색", "금색", "은색"],
                "lucky_items": ["시계", "펜", "금속 액세서리"],
                "reason": "금 기운은 집중과 정돈의 상징으로 보완 요소로 추천합니다.",
            }
        )
    )


def full_registry() -> dict:
    return {
        config.TOOL_SAJU_CHART: calculate_saju_chart_impl,
        config.TOOL_FIVE_ELEMENTS: fake_five_elements,
        config.TOOL_TODAY_LUCK: fake_today_luck,
        config.TOOL_LUCKY_FACTORS: fake_lucky_factors,
    }


# --- 프로필 생성 --------------------------------------------------------
def test_build_profile_assembles_all_parts():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    assert profile["ok"] is True
    data = profile["data"]
    assert data["user"]["name"] == "민지"
    assert data["saju_chart"]["year_pillar"] == "무인"
    assert data["five_elements"]["recommended_element"] == "metal"
    assert data["pending_tools"] == []


def test_build_profile_propagates_saju_error():
    orch = Orchestrator(registry=full_registry())
    bad = json.dumps({"birth_date": "nope", "calendar_type": "solar", "name": "x"})
    profile = orch.build_profile(bad)
    assert profile["ok"] is False
    assert profile["error"]["code"] == config.ErrorCode.INVALID_DATE


# --- 메뉴별 tool 실행 ---------------------------------------------------
def test_saju_reading_does_not_run_today_luck():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("saju_reading", profile)
    assert result["ok"] is True
    # 사주풀이는 오늘 운세(일진) 점수는 쓰지 않는다.
    assert config.TOOL_TODAY_LUCK not in result["data"]["tools_run"]
    assert "five_elements" in result["data"]["tool_results"]
    # 명리 해석(십신/신살/대운 등)과 행운 색깔은 사주풀이 양식에 포함된다.
    assert "myeongri" in result["data"]["tool_results"]
    assert config.TOOL_LUCKY_FACTORS in result["data"]["tools_run"]


def test_today_fortune_runs_today_luck():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("today_fortune", profile)
    assert result["ok"] is True
    assert config.TOOL_TODAY_LUCK in result["data"]["tools_run"]
    assert result["data"]["tool_results"]["today_luck"]["score"] == 82


def test_lucky_color_runs_lucky_factors():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("lucky_color", profile)
    assert result["ok"] is True
    assert config.TOOL_LUCKY_FACTORS in result["data"]["tools_run"]
    assert result["data"]["tool_results"]["lucky_factors"]["lucky_colors"]


def test_unknown_intent_returns_error():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("health", profile)
    assert result["ok"] is False
    assert result["error"]["code"] == config.ErrorCode.NOT_IMPLEMENTED


# --- graceful degradation (팀원 도구 미구현) ----------------------------
def test_graceful_when_teammate_tools_missing():
    # 내 도구만 있는 레지스트리
    orch = Orchestrator(registry={config.TOOL_SAJU_CHART: calculate_saju_chart_impl})
    profile = orch.build_profile(USER_JSON)
    assert profile["ok"] is True
    assert profile["data"]["five_elements"] is None
    assert config.TOOL_FIVE_ELEMENTS in profile["data"]["pending_tools"]

    result = orch.answer("today_fortune", profile)
    assert result["ok"] is True
    # 오행이 없으면 today_luck 도 실행하지 못하고 pending 으로 남는다.
    assert config.TOOL_TODAY_LUCK in result["data"]["pending_tools"]
    assert result["data"]["tools_run"] == []


def test_default_registry_contains_my_tool():
    registry = default_registry()
    assert config.TOOL_SAJU_CHART in registry


# --- LLM fallback -------------------------------------------------------
def test_fallback_answer_is_deterministic_text():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("today_fortune", profile)
    package = result["data"]["llm_package"]
    text = prompts.fallback_answer(package)
    assert "민지" in text
    assert "82" in text  # 오늘의 점수가 들어간다
    assert config.DISCLAIMER_KO in text


def test_generate_answer_falls_back_without_llm(monkeypatch):
    monkeypatch.setattr(prompts, "_get_llm", lambda: None)
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("saju_reading", profile)
    answer = prompts.generate_answer(result["data"]["llm_package"])
    assert answer["mode"] == "fallback"
    assert answer["text"]


# --- 방어 경로(예외/실패/비-JSON 반환) graceful 처리 ---------------------
def _raising_tool(_json_str: str) -> str:
    raise RuntimeError("boom")


def _failing_five_elements(_saju_chart_json: str) -> str:
    return config.to_json(
        config.failure(config.ErrorCode.INVALID_SAJU_CHART, "분석 실패")
    )


def _bad_return_tool(_json_str: str):
    return 12345  # dict 도 JSON 문자열도 아님


def test_raising_tool_stays_graceful():
    registry = full_registry()
    registry[config.TOOL_TODAY_LUCK] = _raising_tool
    orch = Orchestrator(registry=registry)
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("today_fortune", profile)
    # 도구가 예외를 던져도 앱은 죽지 않고 해당 도구만 pending 으로 남는다.
    assert result["ok"] is True
    assert config.TOOL_TODAY_LUCK in result["data"]["pending_tools"]
    assert "today_luck" not in result["data"]["tool_results"]


def test_five_elements_failure_marks_pending():
    registry = full_registry()
    registry[config.TOOL_FIVE_ELEMENTS] = _failing_five_elements
    orch = Orchestrator(registry=registry)
    profile = orch.build_profile(USER_JSON)
    assert profile["ok"] is True
    assert profile["data"]["five_elements"] is None
    assert config.TOOL_FIVE_ELEMENTS in profile["data"]["pending_tools"]


def test_bad_return_type_is_handled():
    registry = full_registry()
    registry[config.TOOL_LUCKY_FACTORS] = _bad_return_tool
    orch = Orchestrator(registry=registry)
    profile = orch.build_profile(USER_JSON)
    result = orch.answer("lucky_color", profile)
    # 비-JSON 반환도 graceful: 앱은 ok, lucky_factors 는 pending
    assert result["ok"] is True
    assert config.TOOL_LUCKY_FACTORS in result["data"]["pending_tools"]
    assert "lucky_factors" not in result["data"]["tool_results"]


# --- conversation entry point -------------------------------------------
def test_handle_message_routes_natural_language_with_existing_profile():
    orch = Orchestrator(registry=full_registry())
    profile = orch.build_profile(USER_JSON)
    result = orch.handle_message("오늘 운세 봐줘", {"profile": profile})
    assert result["ok"] is True
    assert result["data"]["reply_kind"] == "answer"
    assert result["data"]["intent"] == "today_fortune"
    assert config.TOOL_TODAY_LUCK in result["data"]["tools_run"]


def test_handle_message_follow_up_uses_previous_result_without_rerunning_tool():
    registry = full_registry()
    registry[config.TOOL_TODAY_LUCK] = _raising_tool
    orch = Orchestrator(registry=registry)
    profile = Orchestrator(registry=full_registry()).build_profile(USER_JSON)
    state = {
        "profile": profile,
        "last_intent": "today_fortune",
        "last_tool_results": {"today_luck": {"score": 82}},
    }
    result = orch.handle_message("왜 그렇게 나와?", state)
    assert result["ok"] is True
    assert result["data"]["reply_kind"] == "follow_up"
    assert result["data"]["llm_package"]["tool_result"]["today_luck"]["score"] == 82
    assert result["data"]["tools_run"] == []


def test_handle_message_tool_exception_becomes_pending_tool():
    registry = full_registry()
    registry[config.TOOL_LUCKY_FACTORS] = _raising_tool
    orch = Orchestrator(registry=registry)
    profile = orch.build_profile(USER_JSON)
    result = orch.handle_message("행운 색깔 알려줘", {"profile": profile})
    assert result["ok"] is True
    assert result["data"]["reply_kind"] == "answer"
    assert config.TOOL_LUCKY_FACTORS in result["data"]["pending_tools"]
