"""Chat-first Streamlit UI for the saju self-reflection chatbot.

Run with: streamlit run app.py
"""
from __future__ import annotations

import json
from datetime import date, time

import streamlit as st
from dotenv import load_dotenv

from src import config, prompts
from src.ui import copy as ui_copy
from src.ui import state as ui_state
from src.ui.view_models import pending_tools_text, profile_summary

try:
    from src.chat_intent import ConversationState, route_intent
except Exception:  # pragma: no cover - supports partial parallel implementation
    ConversationState = None  # type: ignore[assignment]
    route_intent = None  # type: ignore[assignment]


st.set_page_config(page_title=ui_copy.APP_TITLE, page_icon="*", layout="centered")
load_dotenv()


def hide_streamlit_input_instructions() -> None:
    st.markdown(
        """
        <style>
        [data-testid="InputInstructions"] {
            display: none;
        }

        input:focus::placeholder {
            color: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


class FallbackOrchestrator:
    """UI-only guard used when the backend module is temporarily unavailable."""

    def build_profile(self, user_info_json: str) -> dict:
        try:
            user = json.loads(user_info_json)
        except json.JSONDecodeError:
            return config.failure(config.ErrorCode.INVALID_JSON, "프로필 JSON 형식이 올바르지 않습니다.")
        if not (user.get("name") or "").strip():
            return config.failure(config.ErrorCode.INVALID_INPUT, "이름을 입력해 주세요.")
        return config.success(
            {
                "user": {
                    "name": user.get("name"),
                    "gender": user.get("gender"),
                    "birth_date": user.get("birth_date"),
                    "birth_time": user.get("birth_time"),
                    "calendar_type": user.get("calendar_type"),
                },
                "saju_chart": {
                    "year_pillar": "준비 중",
                    "month_pillar": "준비 중",
                    "day_pillar": "준비 중",
                    "hour_pillar": None if user.get("birth_time_unknown") else "준비 중",
                    "time_precision": "unknown" if user.get("birth_time_unknown") else "known",
                },
                "five_elements": None,
                "pending_tools": [
                    config.TOOL_SAJU_CHART,
                    config.TOOL_FIVE_ELEMENTS,
                    config.TOOL_TODAY_LUCK,
                    config.TOOL_LUCKY_FACTORS,
                ],
            }
        )

    def answer(self, intent: str, profile: dict, follow_up: str | None = None) -> dict:
        if not profile.get("ok"):
            return config.failure(config.ErrorCode.INVALID_PROFILE, "먼저 유효한 프로필을 저장해 주세요.")
        package = prompts.build_llm_package(
            intent,
            profile["data"],
            {},
            user_message=follow_up,
            conversation_history=st.session_state.get(ui_state.MESSAGES_KEY, []),
            last_intent=st.session_state.get(ui_state.LAST_INTENT_KEY),
        )
        return config.success(
            {
                "intent": intent,
                "tool_results": {},
                "llm_package": package,
                "tools_run": [],
                "pending_tools": profile["data"].get("pending_tools", []),
                "follow_up": follow_up,
            }
        )


def get_orchestrator():
    try:
        from src.orchestrator import Orchestrator

        return Orchestrator()
    except (ImportError, SyntaxError, UnicodeError):
        return FallbackOrchestrator()


def _profile_payload_from_widgets() -> dict:
    birth_date = st.session_state.get("profile_birth_date", date(1998, 3, 12))
    birth_time_unknown = bool(st.session_state.get("profile_birth_time_unknown", False))
    birth_time_value = st.session_state.get("profile_birth_time", time(9, 0))
    return {
        "name": st.session_state.get("profile_name", "").strip(),
        "gender": st.session_state.get("profile_gender", "unknown"),
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "birth_time": None if birth_time_unknown else birth_time_value.strftime("%H:%M"),
        "calendar_type": st.session_state.get("profile_calendar_type", "solar"),
        "birth_time_unknown": birth_time_unknown,
        "is_leap_month": bool(st.session_state.get("profile_is_leap_month", False)),
    }


def save_profile() -> None:
    payload = _profile_payload_from_widgets()
    if not payload["name"]:
        st.session_state["profile_error"] = "이름을 입력해 주세요."
        st.session_state.pop(ui_state.PROFILE_KEY, None)
        return

    result = get_orchestrator().build_profile(json.dumps(payload, ensure_ascii=False))
    if not result.get("ok"):
        message = result.get("error", {}).get("message", "알 수 없는 프로필 오류가 발생했습니다.")
        st.session_state["profile_error"] = f"{ui_copy.PROFILE_ERROR_PREFIX}: {message}"
        st.session_state.pop(ui_state.PROFILE_KEY, None)
        return

    st.session_state.pop("profile_error", None)
    ui_state.sync_profile(st.session_state, result)
    if not st.session_state.get(ui_state.PROFILE_READY_FLAG):
        ui_state.append_message(st.session_state, "assistant", ui_copy.PROFILE_READY_MESSAGE)
        st.session_state[ui_state.PROFILE_READY_FLAG] = True


def _route_message(message: str):
    if route_intent is None:
        return None
    raw_state = st.session_state.get(ui_state.CONVERSATION_STATE_KEY)
    state = ConversationState.from_dict(raw_state) if ConversationState is not None else raw_state
    return route_intent(message, state)


def _resolve_intent(message: str, forced_intent: str | None = None) -> tuple[str | None, str | None, str]:
    if forced_intent:
        return forced_intent, None, "intent"
    routed = _route_message(message)
    if routed is None:
        return "saju_reading", None, "intent"
    if routed.kind == "blocked":
        return None, None, "blocked"
    if routed.kind == "clarify":
        return None, None, "clarify"
    return routed.intent, routed.follow_up, routed.kind


def _append_display_message(role: str, content: str) -> None:
    """Append only to the rendered chat list.

    ``Orchestrator.handle_message`` owns conversation-state history for user
    turns, so the Streamlit layer should not write the same user turn there
    before calling it.
    """
    st.session_state[ui_state.MESSAGES_KEY].append({"role": role, "content": content})


def _sync_projection_from_conversation_state(state: dict | None) -> None:
    if not isinstance(state, dict):
        return
    profile = state.get("profile")
    if isinstance(profile, dict) and profile.get("ok"):
        st.session_state[ui_state.PROFILE_KEY] = profile
    if state.get("last_intent"):
        st.session_state[ui_state.LAST_INTENT_KEY] = state["last_intent"]
    if state.get("last_tool_results") is not None:
        st.session_state[ui_state.LAST_TOOL_RESULTS_KEY] = state.get("last_tool_results", {})


def process_chat_message(message: str, forced_intent: str | None = None) -> None:
    message = (message or "").strip()
    if not message:
        return

    orch = get_orchestrator()
    if forced_intent is None and hasattr(orch, "handle_message"):
        _append_display_message("user", message)
        answer_from_handle_message(orch, message)
        return

    ui_state.append_message(st.session_state, "user", message)

    profile = st.session_state.get(ui_state.PROFILE_KEY)
    if not profile:
        ui_state.append_message(st.session_state, "assistant", ui_copy.PROFILE_NEEDED_MESSAGE)
        return

    intent, follow_up, kind = _resolve_intent(message, forced_intent)
    if kind == "blocked":
        ui_state.append_message(st.session_state, "assistant", ui_copy.SAFETY_REDIRECT)
        return
    if kind == "clarify" or not intent:
        ui_state.append_message(st.session_state, "assistant", ui_copy.CLARIFY_MESSAGE)
        return

    result = orch.answer(intent, profile, follow_up=follow_up)
    if not result.get("ok"):
        ui_state.append_message(st.session_state, "assistant", result["error"]["message"])
        return

    data = result["data"]
    answer = prompts.generate_answer(
        data["llm_package"],
        follow_up=follow_up,
        history=st.session_state.get(ui_state.MESSAGES_KEY, []),
    )
    text = answer["text"]
    pending = pending_tools_text(data.get("pending_tools"))
    if pending:
        text = f"{text}\n\n{pending}"
    ui_state.append_message(st.session_state, "assistant", text)
    ui_state.sync_answer_state(st.session_state, intent, data.get("tool_results", {}))


def answer_from_handle_message(orch, message: str) -> None:
    raw_state = st.session_state.get(ui_state.CONVERSATION_STATE_KEY)
    state = ConversationState.from_dict(raw_state) if ConversationState is not None else raw_state
    result = orch.handle_message(message, state)
    if not result.get("ok"):
        ui_state.append_message(st.session_state, "assistant", result["error"]["message"])
        return
    data = result["data"]
    if data.get("state"):
        st.session_state[ui_state.CONVERSATION_STATE_KEY] = data["state"]
        _sync_projection_from_conversation_state(data["state"])

    reply_kind = data.get("reply_kind")
    package = data.get("llm_package")
    if package:
        answer = prompts.generate_answer(
            package,
            follow_up=data.get("follow_up"),
            history=st.session_state.get(ui_state.MESSAGES_KEY, []),
        )
        text = answer["text"]
        pending = pending_tools_text(data.get("pending_tools"))
        if pending:
            text = f"{text}\n\n{pending}"
        ui_state.append_message(st.session_state, "assistant", text)
    elif reply_kind == "blocked":
        ui_state.append_message(st.session_state, "assistant", ui_copy.SAFETY_REDIRECT)
    elif reply_kind == "need_profile":
        ui_state.append_message(st.session_state, "assistant", ui_copy.PROFILE_NEEDED_MESSAGE)
    elif reply_kind == "profile_ready":
        ui_state.append_message(st.session_state, "assistant", ui_copy.PROFILE_READY_MESSAGE)
    elif reply_kind == "profile_error":
        profile = (st.session_state.get(ui_state.CONVERSATION_STATE_KEY) or {}).get("profile") or {}
        message = profile.get("error", {}).get("message", ui_copy.PROFILE_ERROR_PREFIX)
        st.session_state["profile_error"] = message
        ui_state.append_message(st.session_state, "assistant", f"{ui_copy.PROFILE_ERROR_PREFIX}: {message}")
    else:
        ui_state.append_message(st.session_state, "assistant", ui_copy.CLARIFY_MESSAGE)


def quick_action(message: str, intent: str) -> None:
    process_chat_message(message, forced_intent=intent)


def reset_conversation() -> None:
    ui_state.reset_session_state(st.session_state, ui_copy.WELCOME_MESSAGE)


def render_sidebar() -> None:
    with st.sidebar:
        st.header(ui_copy.PROFILE_PANEL_TITLE)
        st.text_input(
            ui_copy.PROFILE_FIELD_LABELS["name"],
            value="",
            placeholder="홍길동",
            key="profile_name",
        )
        st.selectbox(
            ui_copy.PROFILE_FIELD_LABELS["gender"],
            options=["female", "male", "other", "unknown"],
            index=0,
            format_func=lambda value: {
                "female": "여성",
                "male": "남성",
                "other": "기타",
                "unknown": "선택 안 함",
            }[value],
            key="profile_gender",
        )
        st.radio(
            ui_copy.PROFILE_FIELD_LABELS["calendar_type"],
            options=["solar", "lunar"],
            format_func=lambda value: {"solar": "양력", "lunar": "음력"}[value],
            horizontal=True,
            key="profile_calendar_type",
        )
        st.date_input(
            ui_copy.PROFILE_FIELD_LABELS["birth_date"],
            value=date(1998, 3, 12),
            min_value=date(config.SUPPORTED_YEAR_MIN, 1, 1),
            max_value=date(config.SUPPORTED_YEAR_MAX, 12, 31),
            key="profile_birth_date",
        )
        st.checkbox(
            ui_copy.PROFILE_FIELD_LABELS["birth_time_unknown"],
            value=False,
            help=ui_copy.PROFILE_HELP_TEXT["birth_time_unknown"],
            key="profile_birth_time_unknown",
        )
        st.time_input(
            ui_copy.PROFILE_FIELD_LABELS["birth_time"],
            value=time(9, 0),
            disabled=st.session_state.get("profile_birth_time_unknown", False),
            key="profile_birth_time",
        )
        st.checkbox(
            ui_copy.PROFILE_FIELD_LABELS["is_leap_month"],
            value=False,
            help=ui_copy.PROFILE_HELP_TEXT["is_leap_month"],
            key="profile_is_leap_month",
        )
        st.button(
            ui_copy.SAVE_PROFILE_LABEL,
            key="save_profile",
            use_container_width=True,
            on_click=save_profile,
        )

        if st.session_state.get("profile_error"):
            st.error(st.session_state["profile_error"])

        summary = profile_summary(st.session_state.get(ui_state.PROFILE_KEY))
        if summary["ready"]:
            st.success(f"{summary['name']} 님의 프로필이 준비됐어요")
            for label, value in summary["pillars"]:
                st.caption(f"{label}: {value}")
            if summary["elements"]:
                st.caption(f"오행: {summary['elements']}")
            pending = pending_tools_text(summary["pending_tools"])
            if pending:
                st.info(pending)

        st.button(ui_copy.RESET_LABEL, key="reset_conversation", on_click=reset_conversation)


def render_header() -> None:
    st.title(ui_copy.APP_TITLE)
    st.markdown(f"**채팅 중심 사주 풀이**: {ui_copy.APP_SUBTITLE}")


def render_quick_actions() -> None:
    cols = st.columns(4)
    for index, (intent, label, prompt) in enumerate(ui_copy.QUICK_ACTIONS):
        cols[index % 4].button(
            label,
            key=f"quick_{intent}",
            use_container_width=True,
            on_click=quick_action,
            args=(prompt, intent),
        )


def render_chat_history() -> None:
    for item in st.session_state.get(ui_state.MESSAGES_KEY, []):
        with st.chat_message(item["role"]):
            st.markdown(item["content"])


def main() -> None:
    hide_streamlit_input_instructions()
    ui_state.ensure_session_state(st.session_state, ui_copy.WELCOME_MESSAGE)
    render_sidebar()
    render_header()
    render_quick_actions()
    render_chat_history()

    submitted = st.chat_input(ui_copy.CHAT_PLACEHOLDER)
    if submitted:
        process_chat_message(submitted)
        st.rerun()


if __name__ == "__main__":
    main()
