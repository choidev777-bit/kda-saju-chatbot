"""Deterministic chat intent routing for the conversation MVP."""
from __future__ import annotations

from dataclasses import dataclass

from . import config
from .conversation import (
    ConversationState,
    append_message,
    extract_slots_from_message,
    merge_slots,
    missing_slots,
    slots_to_user_info,
)


@dataclass(frozen=True)
class RoutedIntent:
    kind: str
    intent: str | None = None
    follow_up: str | None = None
    blocked_topic: str | None = None


def route_intent(message: str, state: ConversationState | None = None) -> RoutedIntent:
    current = ConversationState.from_dict(state)
    text = (message or "").strip()
    lowered = text.lower()

    blocked = _blocked_topic(text, lowered)
    if blocked:
        return RoutedIntent(kind="blocked", blocked_topic=blocked)

    intent = _match_intent(text, lowered)
    if intent and intent != current.last_intent:
        return RoutedIntent(kind="intent", intent=intent)

    if current.last_intent and (
        _looks_like_follow_up(text, lowered)
        or _looks_like_contextual_question(text, lowered)
    ):
        return RoutedIntent(
            kind="follow_up", intent=current.last_intent, follow_up=text
        )

    if intent:
        return RoutedIntent(kind="intent", intent=intent)

    if _has_answer_context(current):
        return RoutedIntent(
            kind="follow_up", intent=current.last_intent, follow_up=text
        )

    return RoutedIntent(kind="clarify")


def _blocked_topic(text: str, lowered: str) -> str | None:
    english_blocked_aliases = (
        (
            ("health", "medical", "doctor", "diagnosis", "disease", "illness", "sick", "cancer"),
            0,
        ),
        (("lifespan", "death", "die", "dying", "dead"), 2),
        (("accident", "crash", "injury"), 3),
        (("investment", "stock", "return", "profit", "financial advice"), 4),
        (("admission", "exam", "pass or fail"), 5),
        (("lottery", "gamble", "gambling", "bet", "betting", "casino"), 7),
        (("legal advice", "lawsuit", "court", "contract dispute"), 0),
    )
    for tokens, fallback_index in english_blocked_aliases:
        if any(token in lowered for token in tokens):
            return config.EXCLUDED_TOPICS_KO[fallback_index]

    blocked_aliases = (
        (("건강운", "건강", "health", "medical"), "건강운"),
        (("질병", "disease", "illness"), "질병"),
        (("수명", "죽음", "lifespan", "death"), "수명"),
        (("사고", "accident"), "사고"),
        (("투자 수익", "투자", "수익률", "investment", "stock"), "투자 수익"),
        (("합격", "입시", "시험", "admission", "exam"), "합격"),
        (("당첨", "복권", "lottery"), "복권"),
    )
    configured = set(config.EXCLUDED_TOPICS_KO)
    for topic in config.EXCLUDED_TOPICS_KO:
        if topic and topic in text:
            return topic
    for tokens, topic in blocked_aliases:
        if any(token in text or token in lowered for token in tokens):
            return topic if topic in configured else config.EXCLUDED_TOPICS_KO[0]
    return None


def _looks_like_follow_up(text: str, lowered: str) -> bool:
    compact = text.replace(" ", "")
    return any(
        token in lowered or token in compact
        for token in (
            "why",
            "reason",
            "explain",
            "more",
            "왜",
            "이유",
            "근거",
            "자세",
            "그렇게",
            "??",
        )
    )


def _looks_like_contextual_question(text: str, lowered: str) -> bool:
    compact = text.replace(" ", "")
    return any(
        token in lowered or token in compact
        for token in (
            "meaning",
            "means",
            "what does",
            "tell me about",
            "의미",
            "뜻",
            "무슨뜻",
            "어떤",
            "성격",
            "설명",
            "말이야",
            "라는건",
            "라는것",
            "이라는건",
            "이라는것",
        )
    )


def _has_answer_context(state: ConversationState) -> bool:
    return bool(state.last_intent and state.last_tool_results)


def _match_intent(text: str, lowered: str) -> str | None:
    compact = text.replace(" ", "")

    if any(token in lowered for token in ("lucky color", "color", "colour")):
        return "lucky_color"
    if any(token in compact for token in ("행운색", "행운의색", "색깔", "컬러")):
        return "lucky_color"

    if any(token in lowered for token in ("lucky item", "item")):
        return "lucky_item"
    if any(token in compact for token in ("행운아이템", "아이템", "소품")):
        return "lucky_item"

    if any(token in lowered for token in ("love", "relationship", "romance")):
        return "love"
    if any(token in compact for token in ("연애", "관계운", "사랑")):
        return "love"

    if any(token in lowered for token in ("money", "wealth", "finance")):
        return "wealth"
    if any(token in compact for token in ("재물", "돈", "소비", "기회")):
        return "wealth"

    if any(token in lowered for token in ("life flow", "life path")):
        return "life_flow"
    if any(token in compact for token in ("인생흐름", "흐름", "초년", "중년")):
        return "life_flow"

    if any(token in lowered for token in ("saju", "chart", "reading", "five elements")):
        return "saju_reading"
    if any(token in compact for token in ("사주", "오행", "팔자", "해석")):
        return "saju_reading"

    if any(token in lowered for token in ("score", "point", "number")):
        return "luck_score"
    if any(token in compact for token in ("점수", "운세점수", "행운점수")):
        return "luck_score"

    if any(token in lowered for token in ("today", "fortune", "luck")):
        return "today_fortune"
    if any(token in compact for token in ("오늘", "운세", "하루")):
        return "today_fortune"

    return None


__all__ = [
    "ConversationState",
    "RoutedIntent",
    "append_message",
    "extract_slots_from_message",
    "merge_slots",
    "missing_slots",
    "route_intent",
    "slots_to_user_info",
]
