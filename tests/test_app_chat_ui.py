from __future__ import annotations

from datetime import date, time
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.ui import copy as ui_copy


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def run_app() -> AppTest:
    assert APP_PATH.exists(), f"Expected Streamlit entrypoint at {APP_PATH}"
    app = AppTest.from_file(str(APP_PATH))
    app.run(timeout=15)
    assert not app.exception
    return app


def button_with_key(app: AppTest, key: str):
    for button in app.button:
        if button.key == key:
            return button
    raise AssertionError(f"Expected button with key {key!r}")


def test_app_renders_chat_first_shell_and_state_keys():
    app = run_app()

    assert len(app.chat_message) >= 1
    assert len(app.chat_input) == 1
    assert "messages" in app.session_state
    assert "conversation_state" in app.session_state
    assert isinstance(app.session_state["messages"], list)


def test_name_input_uses_empty_value_with_placeholder():
    app = run_app()

    assert app.text_input[0].key == "profile_name"
    assert app.text_input[0].value == ""
    assert app.text_input[0].placeholder == "홍길동"


def test_initial_rerun_does_not_duplicate_welcome_message():
    app = run_app()
    initial_messages = list(app.session_state["messages"])

    app.run(timeout=15)

    assert app.session_state["messages"] == initial_messages


def test_quick_action_menu_contains_only_requested_buttons():
    app = run_app()

    quick_buttons = [button for button in app.button if button.key and button.key.startswith("quick_")]
    expected_actions = [
        ("saju_reading", "사주 풀이"),
        ("today_fortune", "오늘 운세"),
        ("lucky_item", "행운 아이템"),
        ("lucky_color", "행운색"),
        ("love", "연애운"),
        ("wealth", "재물운"),
        ("life_flow", "인생흐름"),
    ]

    assert [(intent, label) for intent, label, _prompt in ui_copy.QUICK_ACTIONS] == expected_actions
    assert {button.label for button in quick_buttons} == {label for _intent, label in expected_actions}
    assert {button.key for button in quick_buttons} == {f"quick_{intent}" for intent, _label in expected_actions}


def test_sidebar_profile_submission_stores_profile_and_conversation_state():
    app = run_app()

    assert len(app.text_input) >= 1
    assert len(app.date_input) >= 1
    assert len(app.time_input) >= 1

    app.text_input[0].set_value("Mina")
    app.date_input[0].set_value(date(1998, 3, 12))
    app.time_input[0].set_value(time(9, 0))
    button_with_key(app, "save_profile").click()
    app.run(timeout=20)

    assert "profile" in app.session_state
    assert app.session_state["profile"]["ok"] is True
    assert app.session_state["conversation_state"]["profile"]["ok"] is True
    assert any(message["role"] == "assistant" for message in app.session_state["messages"])


def test_chat_submit_appends_user_and_assistant_turns():
    app = run_app()
    starting_count = len(app.session_state["messages"])

    app.chat_input[0].set_value("lucky color please")
    app.run(timeout=20)

    messages = app.session_state["messages"]
    assert len(messages) >= starting_count + 2
    assert messages[-2]["role"] == "user"
    assert messages[-2]["content"] == "lucky color please"
    assert messages[-1]["role"] == "assistant"
