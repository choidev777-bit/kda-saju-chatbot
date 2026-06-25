import json

from src import config
from src.chat_intent import (
    ConversationState,
    append_message,
    extract_slots_from_message,
    merge_slots,
    missing_slots,
)
from src.orchestrator import Orchestrator
from tests.test_orchestrator import (
    USER_JSON,
    fake_five_elements,
    fake_lucky_factors,
    fake_today_luck,
)


def test_initial_state_has_no_profile_and_empty_history():
    state = ConversationState()
    assert state.profile is None
    assert state.message_history == []
    assert state.pending_slots == []


def test_state_round_trip_preserves_conversation_fields():
    state = ConversationState(
        user_slots={"name": "Mina"},
        last_intent="today_fortune",
        last_tool_results={"today_luck": {"score": 82}},
    )
    restored = ConversationState.from_dict(state.to_dict())
    assert restored.user_slots["name"] == "Mina"
    assert restored.last_intent == "today_fortune"
    assert restored.last_tool_results["today_luck"]["score"] == 82


def test_append_message_caps_history():
    state = ConversationState(history_limit=3)
    for idx in range(5):
        append_message(state, "user", f"message {idx}")
    assert [item["content"] for item in state.message_history] == [
        "message 2",
        "message 3",
        "message 4",
    ]


def test_slot_helpers_extract_merge_and_find_missing_required_slots():
    slots = extract_slots_from_message("Mina, 1998-03-12, 09:00, solar")
    merged = merge_slots({"gender": "female"}, slots)
    assert merged["name"] == "Mina"
    assert merged["birth_date"] == "1998-03-12"
    assert merged["birth_time"] == "09:00"
    assert merged["calendar_type"] == "solar"
    assert missing_slots(merged) == []


def test_handle_message_asks_for_profile_slots_before_tools():
    orch = Orchestrator(registry={})
    result = orch.handle_message("오늘 운세 봐줘", ConversationState())
    assert result["ok"] is True
    data = result["data"]
    assert data["reply_kind"] == "need_profile"
    assert "birth_date" in data["pending_slots"]
    assert data["llm_package"] is None


def test_handle_message_builds_profile_from_completed_slots_and_reuses_it():
    calls = {"saju": 0}

    def fake_saju(_json_str: str) -> str:
        calls["saju"] += 1
        return config.to_json(
            config.success(
                {
                    "year_pillar": "甲子",
                    "month_pillar": "乙丑",
                    "day_pillar": "丙寅",
                    "hour_pillar": "丁卯",
                    "time_precision": "known",
                }
            )
        )

    registry = {
        config.TOOL_SAJU_CHART: fake_saju,
        config.TOOL_FIVE_ELEMENTS: fake_five_elements,
        config.TOOL_TODAY_LUCK: fake_today_luck,
        config.TOOL_LUCKY_FACTORS: fake_lucky_factors,
    }
    orch = Orchestrator(registry=registry)

    first = orch.handle_message("Mina, 1998-03-12, 09:00, solar")
    state = ConversationState.from_dict(first["data"]["state"])
    assert first["data"]["reply_kind"] == "profile_ready"
    assert calls["saju"] == 1

    second = orch.handle_message("lucky color please", state)
    assert second["data"]["reply_kind"] == "answer"
    assert second["data"]["llm_package"]["intent"] == "lucky_color"
    assert calls["saju"] == 1


def test_follow_up_uses_last_intent_and_last_tool_results():
    profile = Orchestrator(
        registry={
            config.TOOL_SAJU_CHART: lambda _: json.dumps(
                {
                    "ok": True,
                    "data": {
                        "year_pillar": "甲子",
                        "month_pillar": "乙丑",
                        "day_pillar": "丙寅",
                        "hour_pillar": "丁卯",
                        "time_precision": "known",
                    },
                },
                ensure_ascii=False,
            ),
            config.TOOL_FIVE_ELEMENTS: fake_five_elements,
        }
    ).build_profile(USER_JSON)
    state = ConversationState(
        profile=profile,
        last_intent="today_fortune",
        last_tool_results={"today_luck": {"score": 82}},
    )
    orch = Orchestrator(registry={})
    result = orch.handle_message("why?", state)
    assert result["data"]["reply_kind"] == "follow_up"
    assert result["data"]["llm_package"]["intent"] == "today_fortune"
    assert result["data"]["llm_package"]["tool_result"]["today_luck"]["score"] == 82


def test_contextual_follow_up_uses_previous_saju_result_without_rerunning_tools():
    profile = Orchestrator(
        registry={
            config.TOOL_SAJU_CHART: lambda _: json.dumps(
                {
                    "ok": True,
                    "data": {
                        "year_pillar": "甲子",
                        "month_pillar": "乙丑",
                        "day_pillar": "丙寅",
                        "hour_pillar": "丁卯",
                        "time_precision": "known",
                    },
                },
                ensure_ascii=False,
            ),
            config.TOOL_FIVE_ELEMENTS: fake_five_elements,
        }
    ).build_profile(USER_JSON)
    previous_results = {
        "saju_chart": {"day_pillar": "丙寅"},
        "five_elements": {"strongest": "토", "weakest": "금"},
    }
    state = ConversationState(
        profile=profile,
        last_intent="saju_reading",
        last_tool_results=previous_results,
    )
    orch = Orchestrator(registry={})
    message = "토가 강하고 금의 기운이 적다는 것은 어떤 성격의 사람이라는 의미야?"

    result = orch.handle_message(message, state)

    assert result["data"]["reply_kind"] == "follow_up"
    assert result["data"]["llm_package"]["intent"] == "saju_reading"
    assert result["data"]["llm_package"]["tool_result"] == previous_results
    assert result["data"]["tools_run"] == []
    assert result["data"]["follow_up"] == message
