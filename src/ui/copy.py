"""Stable UI copy for the chat-first Streamlit app.

This module is intentionally framework-free. Streamlit can import these values
today, and a later UI can reuse the same labels and prompts without scraping
strings from `app.py`.
"""

from __future__ import annotations

from typing import Final

QuickAction = tuple[str, str, str]

APP_TITLE: Final = "사주풀이 챗봇"
APP_SUBTITLE: Final = "프로필을 한 번 저장하고, 궁금한 운세를 대화로 이어가 보세요."

WELCOME_MESSAGE: Final = (
    "안녕하세요. 왼쪽 사이드바에서 생년월일과 출생시간을 저장하면 "
    "사주 풀이, 오늘 운세, 행운 아이템, 행운색, 연애운, 재물운, 인생흐름을 "
    "채팅으로 편하게 물어볼 수 있어요."
)

PROFILE_PANEL_TITLE: Final = "내 사주 프로필"
PROFILE_READY_MESSAGE: Final = (
    "프로필이 준비됐어요. 이제 궁금한 내용을 채팅으로 물어보거나 빠른 질문을 눌러보세요."
)
PROFILE_NEEDED_MESSAGE: Final = (
    "먼저 왼쪽 사이드바에서 이름, 생년월일, 양력/음력, 출생시간을 저장해 주세요."
)
PROFILE_ERROR_PREFIX: Final = "프로필을 만들 수 없어요"
PROFILE_SUMMARY_READY_SUFFIX: Final = "프로필 준비 완료"

PROFILE_FIELD_LABELS: Final = {
    "name": "이름",
    "gender": "성별",
    "calendar_type": "양력/음력",
    "birth_date": "생년월일",
    "birth_time": "출생시간",
    "birth_time_unknown": "출생시간을 몰라요",
    "is_leap_month": "윤달입니다",
}

PROFILE_HELP_TEXT: Final = {
    "birth_time_unknown": "정확한 출생시간을 모를 때 선택하세요.",
    "is_leap_month": "음력 날짜일 때만 해당됩니다.",
}

CHAT_PLACEHOLDER: Final = "예: 오늘 운세 어때? / 행운색 알려줘 / 왜 그렇게 나와?"
RESET_LABEL: Final = "대화 초기화"
SAVE_PROFILE_LABEL: Final = "프로필 저장"

SAFETY_REDIRECT: Final = (
    "건강, 수명, 사고, 투자 수익, 합격, 복권, 도박처럼 중요한 결정을 단정하는 질문에는 답할 수 없어요. "
    "대신 부담 없는 자기성찰 관점으로 바꿔서 도와드릴게요."
)

CLARIFY_MESSAGE: Final = (
    "사주 풀이, 오늘 운세, 행운 아이템, 행운색, 연애운, 재물운, 인생흐름 중에서 물어봐 주세요. "
    "위의 빠른 질문을 눌러도 좋아요."
)

PENDING_TOOLS_PREFIX: Final = "아직 준비 중인 기능"

QUICK_ACTIONS: Final[tuple[QuickAction, ...]] = (
    ("saju_reading", "사주 풀이", "내 사주를 풀이해줘."),
    ("today_fortune", "오늘 운세", "오늘 운세 어때?"),
    ("lucky_item", "행운 아이템", "오늘 나에게 맞는 행운 아이템은?"),
    ("lucky_color", "행운색", "오늘 나에게 맞는 행운색은?"),
    ("love", "연애운", "연애운에서 돌아볼 점을 알려줘."),
    ("wealth", "재물운", "재물운에서 참고할 점을 알려줘."),
    ("life_flow", "인생흐름", "요즘 인생흐름을 어떻게 보면 좋을까?"),
)

QUICK_ACTION_BY_INTENT: Final = {intent: (label, prompt) for intent, label, prompt in QUICK_ACTIONS}


def quick_action_prompt(intent: str) -> str | None:
    """Return the canned prompt for a quick action intent."""
    action = QUICK_ACTION_BY_INTENT.get(intent)
    return action[1] if action else None


def quick_action_label(intent: str) -> str | None:
    """Return the display label for a quick action intent."""
    action = QUICK_ACTION_BY_INTENT.get(intent)
    return action[0] if action else None


__all__ = [
    "APP_SUBTITLE",
    "APP_TITLE",
    "CHAT_PLACEHOLDER",
    "CLARIFY_MESSAGE",
    "PENDING_TOOLS_PREFIX",
    "PROFILE_ERROR_PREFIX",
    "PROFILE_FIELD_LABELS",
    "PROFILE_HELP_TEXT",
    "PROFILE_NEEDED_MESSAGE",
    "PROFILE_PANEL_TITLE",
    "PROFILE_READY_MESSAGE",
    "PROFILE_SUMMARY_READY_SUFFIX",
    "QUICK_ACTIONS",
    "QUICK_ACTION_BY_INTENT",
    "RESET_LABEL",
    "SAFETY_REDIRECT",
    "SAVE_PROFILE_LABEL",
    "WELCOME_MESSAGE",
    "quick_action_label",
    "quick_action_prompt",
]
