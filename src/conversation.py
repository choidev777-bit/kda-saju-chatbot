"""Conversation state and profile slot helpers.

This module is intentionally UI-free so Streamlit session state can store the
serialized dict while tests can exercise the conversation flow directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import config


DEFAULT_HISTORY_LIMIT = 12


@dataclass
class ConversationState:
    profile: dict | None = None
    user_slots: dict[str, Any] = field(default_factory=dict)
    message_history: list[dict[str, str]] = field(default_factory=list)
    last_intent: str | None = None
    last_tool_results: dict[str, Any] = field(default_factory=dict)
    pending_slots: list[str] = field(default_factory=list)
    pending_tools: list[str] = field(default_factory=list)
    history_limit: int = DEFAULT_HISTORY_LIMIT

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "user_slots": dict(self.user_slots),
            "message_history": list(self.message_history),
            "last_intent": self.last_intent,
            "last_tool_results": dict(self.last_tool_results),
            "pending_slots": list(self.pending_slots),
            "pending_tools": list(self.pending_tools),
            "history_limit": self.history_limit,
        }

    @classmethod
    def from_dict(cls, value: dict | "ConversationState" | None) -> "ConversationState":
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return cls()
        return cls(
            profile=value.get("profile"),
            user_slots=dict(value.get("user_slots") or {}),
            message_history=list(value.get("message_history") or []),
            last_intent=value.get("last_intent"),
            last_tool_results=dict(value.get("last_tool_results") or {}),
            pending_slots=list(value.get("pending_slots") or []),
            pending_tools=list(value.get("pending_tools") or []),
            history_limit=int(value.get("history_limit") or DEFAULT_HISTORY_LIMIT),
        )


def append_message(state: ConversationState, role: str, content: str) -> None:
    state.message_history.append({"role": role, "content": content})
    if len(state.message_history) > state.history_limit:
        del state.message_history[: len(state.message_history) - state.history_limit]


def extract_slots_from_message(message: str) -> dict[str, Any]:
    text = (message or "").strip()
    slots: dict[str, Any] = {}
    if not text:
        return slots

    date_match = re.search(r"\b(19\d{2}|20[0-4]\d|2050)-\d{2}-\d{2}\b", text)
    if date_match:
        slots["birth_date"] = date_match.group(0)

    time_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if time_match:
        slots["birth_time"] = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        slots["birth_time_unknown"] = False
    elif any(token in text.lower() for token in ("unknown", "no time", "모름", "미상")):
        slots["birth_time"] = None
        slots["birth_time_unknown"] = True

    lowered = text.lower()
    if "solar" in lowered or "양력" in text:
        slots["calendar_type"] = "solar"
    elif "lunar" in lowered or "음력" in text:
        slots["calendar_type"] = "lunar"

    if "female" in lowered or "woman" in lowered or "여성" in text or "여자" in text:
        slots["gender"] = "female"
    elif "male" in lowered or "man" in lowered or "남성" in text or "남자" in text:
        slots["gender"] = "male"

    name = _extract_name(text, slots)
    if name:
        slots["name"] = name
    return slots


def _extract_name(text: str, slots: dict[str, Any]) -> str | None:
    before_comma = re.split(r"[,，]", text, maxsplit=1)[0].strip()
    if before_comma and before_comma != text and not re.search(r"\d", before_comma):
        return before_comma

    match = re.search(r"(?:name is|i am|I'm)\s+([A-Za-z][A-Za-z .'-]{0,40})", text, re.I)
    if match:
        return match.group(1).strip(" .,")

    without_known = text
    for value in slots.values():
        if isinstance(value, str):
            without_known = without_known.replace(value, " ")
    tokens = [part.strip(" ,.") for part in without_known.split()]
    if len(tokens) == 1 and re.match(r"^[A-Za-z가-힣]{2,40}$", tokens[0]):
        return tokens[0]
    return None


def merge_slots(existing: dict[str, Any] | None, updates: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(existing or {})
    for key, value in (updates or {}).items():
        if value is not None or key == "birth_time":
            merged[key] = value
    return merged


def missing_slots(slots: dict[str, Any] | None) -> list[str]:
    current = slots or {}
    missing = [
        field
        for field in config.PROFILE_REQUIRED_SLOTS
        if current.get(field) is None or current.get(field) == ""
    ]
    if current.get("birth_time") in (None, "") and not current.get("birth_time_unknown"):
        missing.append("birth_time")
    return missing


def slots_to_user_info(slots: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": slots.get("name"),
        "gender": slots.get("gender", "unknown"),
        "birth_date": slots.get("birth_date"),
        "birth_time": slots.get("birth_time"),
        "calendar_type": slots.get("calendar_type"),
        "birth_time_unknown": bool(slots.get("birth_time_unknown", False)),
        "is_leap_month": bool(slots.get("is_leap_month", False)),
    }
