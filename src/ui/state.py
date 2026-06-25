"""Streamlit session-state conventions for the chat UI.

The functions here keep Streamlit mutations in one place. They operate on a
mapping-like object so tests and future UI layers can pass a plain dict.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

try:
    from src.chat_intent import ConversationState
except Exception:  # pragma: no cover - defensive for partial parallel work
    ConversationState = None  # type: ignore[assignment]

MESSAGES_KEY = "messages"
PROFILE_KEY = "profile"
CONVERSATION_STATE_KEY = "conversation_state"
LAST_INTENT_KEY = "last_intent"
LAST_TOOL_RESULTS_KEY = "last_tool_results"
PROFILE_READY_FLAG = "profile_ready_message_added"

PROFILE_WIDGET_KEYS = (
    "profile_name",
    "profile_gender",
    "profile_calendar_type",
    "profile_birth_date",
    "profile_birth_time",
    "profile_birth_time_unknown",
    "profile_is_leap_month",
)

SESSION_KEYS = (
    MESSAGES_KEY,
    PROFILE_KEY,
    CONVERSATION_STATE_KEY,
    LAST_INTENT_KEY,
    LAST_TOOL_RESULTS_KEY,
    PROFILE_READY_FLAG,
)


def default_messages(welcome: str) -> list[dict[str, str]]:
    return [{"role": "assistant", "content": welcome}]


def new_conversation_state() -> dict[str, Any]:
    if ConversationState is None:
        return {
            "profile": None,
            "user_slots": {},
            "message_history": [],
            "last_intent": None,
            "last_tool_results": {},
            "pending_slots": [],
            "pending_tools": [],
            "history_limit": 12,
        }
    return ConversationState().to_dict()


def ensure_session_state(session_state: MutableMapping[str, Any], welcome: str) -> None:
    if MESSAGES_KEY not in session_state:
        session_state[MESSAGES_KEY] = default_messages(welcome)
    if CONVERSATION_STATE_KEY not in session_state:
        session_state[CONVERSATION_STATE_KEY] = new_conversation_state()
    if LAST_TOOL_RESULTS_KEY not in session_state:
        session_state[LAST_TOOL_RESULTS_KEY] = {}


def reset_session_state(session_state: MutableMapping[str, Any], welcome: str) -> None:
    for key in (
        MESSAGES_KEY,
        PROFILE_KEY,
        CONVERSATION_STATE_KEY,
        LAST_INTENT_KEY,
        LAST_TOOL_RESULTS_KEY,
        PROFILE_READY_FLAG,
    ):
        session_state.pop(key, None)
    ensure_session_state(session_state, welcome)


def append_message(session_state: MutableMapping[str, Any], role: str, content: str) -> None:
    messages = session_state.setdefault(MESSAGES_KEY, [])
    messages.append({"role": role, "content": content})
    state = _conversation_state_dict(session_state.get(CONVERSATION_STATE_KEY))
    if isinstance(state, dict):
        history = list(state.get("message_history") or [])
        history.append({"role": role, "content": content})
        limit = int(state.get("history_limit") or 12)
        state["message_history"] = history[-limit:]
        session_state[CONVERSATION_STATE_KEY] = state


def sync_profile(session_state: MutableMapping[str, Any], profile: dict) -> None:
    session_state[PROFILE_KEY] = profile
    state = _conversation_state_dict(session_state.get(CONVERSATION_STATE_KEY))
    state["profile"] = profile
    session_state[CONVERSATION_STATE_KEY] = state


def sync_answer_state(
    session_state: MutableMapping[str, Any],
    intent: str | None,
    tool_results: dict | None,
) -> None:
    if intent:
        session_state[LAST_INTENT_KEY] = intent
    if tool_results is not None:
        session_state[LAST_TOOL_RESULTS_KEY] = tool_results
    state = _conversation_state_dict(session_state.get(CONVERSATION_STATE_KEY))
    state["last_intent"] = session_state.get(LAST_INTENT_KEY)
    state["last_tool_results"] = session_state.get(LAST_TOOL_RESULTS_KEY, {})
    session_state[CONVERSATION_STATE_KEY] = state


def sync_conversation_state(session_state: MutableMapping[str, Any], state: Any) -> None:
    """Store a serialized conversation state and mirror common top-level keys."""
    serialized = _conversation_state_dict(state)
    session_state[CONVERSATION_STATE_KEY] = serialized
    if serialized.get("profile") is not None:
        session_state[PROFILE_KEY] = serialized["profile"]
    if serialized.get("last_intent") is not None:
        session_state[LAST_INTENT_KEY] = serialized["last_intent"]
    session_state[LAST_TOOL_RESULTS_KEY] = serialized.get("last_tool_results", {})


def get_conversation_state(session_state: MutableMapping[str, Any]) -> dict[str, Any]:
    """Return a normalized serialized conversation state."""
    state = _conversation_state_dict(session_state.get(CONVERSATION_STATE_KEY))
    session_state[CONVERSATION_STATE_KEY] = state
    return state


def _conversation_state_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        state = dict(value)
    else:
        state = new_conversation_state()

    state.setdefault("profile", None)
    state.setdefault("user_slots", {})
    state.setdefault("message_history", [])
    state.setdefault("last_intent", None)
    state.setdefault("last_tool_results", {})
    state.setdefault("pending_slots", [])
    state.setdefault("pending_tools", [])
    state.setdefault("history_limit", 12)
    return state


__all__ = [
    "CONVERSATION_STATE_KEY",
    "LAST_INTENT_KEY",
    "LAST_TOOL_RESULTS_KEY",
    "MESSAGES_KEY",
    "PROFILE_KEY",
    "PROFILE_READY_FLAG",
    "PROFILE_WIDGET_KEYS",
    "SESSION_KEYS",
    "append_message",
    "default_messages",
    "ensure_session_state",
    "get_conversation_state",
    "new_conversation_state",
    "reset_session_state",
    "sync_answer_state",
    "sync_conversation_state",
    "sync_profile",
]
