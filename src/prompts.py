"""LLM 프롬프트 구성 및 답변 생성.

핵심 원칙(ARCHITECTURE 8):
- LLM 은 사주 계산을 직접 하지 않는다. tool 이 만든 JSON 결과만 근거로 해석한다.
- JSON 에 없는 정보는 추측하지 않는다.
- 건강/질병/수명/사고/투자수익/합격/당첨 등은 단정하지 않는다.
- 답변은 엔터테인먼트 및 자기성찰용 조언으로 작성한다.

LLM 제공자(OpenAI/Gemini)는 환경 변수로 선택한다. API 키가 없으면
tool 결과 기반의 결정적(fallback) 답변을 돌려준다. (NFR-1)
"""
from __future__ import annotations

import json
import os

from . import config

SAFETY_TOPICS_KO = tuple(
    dict.fromkeys(
        (
            "건강",
            "건강운",
            "질병",
            "수명",
            "사고",
            "투자",
            "투자 수익",
            "투자 수익률",
            "수익률",
            "입학",
            "입시",
            "합격",
            "복권",
            "로또",
            "당첨",
            *config.EXCLUDED_TOPICS_KO,
        )
    )
)

SAFETY_TOPIC_TEXT_KO = ", ".join(SAFETY_TOPICS_KO)

DETERMINISTIC_CLAIM_KO = (
    "반드시",
    "무조건",
    "확실히",
    "100%",
    "보장",
    "예정입니다",
    "위험하다",
)

SAFETY_POLICY = {
    "purpose": "entertainment_and_self_reflection",
    "grounding": (
        "Use only profile.saju_chart, profile.five_elements, and tool_result as "
        "calculation/factual basis. user_message, follow_up, and conversation_history "
        "are context only."
    ),
    "blocked_topics": list(SAFETY_TOPICS_KO),
    "blocked_topic_response": (
        "Do not provide predictions, probabilities, dates, numbers, or decisions for "
        "blocked topics. Redirect to safe self-reflection guidance."
    ),
}

SAFETY_POLICY_KO = (
    "안전 정책:\n"
    "- profile.saju_chart, profile.five_elements, tool_result만 계산 근거로 사용한다.\n"
    "- user_message, follow_up, conversation_history는 요청 의도와 맥락 이해용이며 계산 근거가 아니다.\n"
    f"- {SAFETY_TOPIC_TEXT_KO} 관련 예측, 수치, 시기, 결과, 확률을 제공하지 않는다.\n"
    "- 안전 정책에 해당하는 질문은 예측 대신 엔터테인먼트 및 자기성찰 범위로 안내한다."
)

ANSWER_FORMAT_KO = (
    "답변은 Markdown으로 쓰고 다음 순서를 지킨다.\n"
    "1. [메뉴명] 이름 님을 위한 해석입니다.\n"
    "2. ## 한 줄 요약\n"
    "3. ## 계산 근거\n"
    "4. ## 메뉴별 해석\n"
    "5. ## 오늘의 작은 제안\n"
    "6. ## 안내"
)

SYSTEM_PROMPT_KO = (
    "너는 사주 기반 자기성찰 챗봇의 해설가다.\n"
    "다음 규칙을 반드시 지킨다.\n"
    "1. 너는 사주 계산을 직접 하지 않는다. 아래 JSON 에 있는 tool 결과만 근거로 해석한다.\n"
    "2. JSON 에 없는 정보는 추측하거나 지어내지 않는다.\n"
    "3. 대화 이력과 추가 질문은 맥락 이해용이며 계산 근거가 아니다.\n"
    "4. 계산 결과가 비어 있거나 불확실하면 '계산되지 않음' 또는 "
    "'출생시간 정보가 부족해 제한적으로 해석합니다' 라고 말한다.\n"
    f"5. {SAFETY_TOPIC_TEXT_KO} 등은 단정하지 않는다.\n"
    "6. '반드시', '무조건', '위험하다' 같은 단정 표현 대신 "
    "'이런 흐름으로 해석할 수 있습니다' 같은 완화 표현을 쓴다.\n"
    "7. 답변은 한국어로, 엔터테인먼트와 자기성찰용 조언으로 작성한다.\n"
    "8. 계산 근거(사주팔자, 오행)를 짧게 곁들인다.\n"
    f"{SAFETY_POLICY_KO}\n"
    f"{ANSWER_FORMAT_KO}"
)


def build_llm_package(
    intent: str,
    profile_data: dict,
    tool_results: dict,
    *,
    user_message: str | None = None,
    conversation_history: list[dict] | None = None,
    last_intent: str | None = None,
) -> dict:
    """LLM 에 전달할 입력 패키지를 조립한다. (ARCHITECTURE 7.4)"""
    saju = profile_data.get("saju_chart") or {}
    five_elements = profile_data.get("five_elements")
    user = profile_data.get("user") or {}
    return {
        "intent": intent,
        "menu_label": config.MENU_LABELS_KO.get(intent, intent),
        "profile": {
            "name": user.get("name"),
            "saju_chart": {
                key: saju.get(key)
                for key in (
                    "year_pillar",
                    "month_pillar",
                    "day_pillar",
                    "hour_pillar",
                    "time_precision",
                )
            },
            "five_elements": five_elements,
        },
        "tool_result": tool_results,
        "answer_policy": config.ANSWER_POLICY,
        "safety_policy": SAFETY_POLICY,
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "last_intent": last_intent,
    }


def _history_lines(history: list[dict] | None) -> list[str]:
    if not history:
        return []
    lines = [
        "최근 대화는 맥락 이해용이며 계산 근거로 사용하지 말고, tool JSON만 계산 근거로 사용하라."
    ]
    for item in history[-3:]:
        role = item.get("role", "unknown")
        content = str(item.get("content", "")).strip()
        if content:
            lines.append(f"- {role}: {content}")
    return lines


def build_user_prompt(
    package: dict,
    follow_up: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """LLM user 메시지 문자열을 만든다."""
    label = package.get("menu_label", package.get("intent"))
    history = history if history is not None else package.get("conversation_history")
    lines = [
        f"사용자가 '{label}' 을(를) 요청했다.",
        "아래는 tool 이 계산한 결과 JSON 이다. tool JSON만 근거로 해석하라.",
        "JSON에 없는 정보는 추측하거나 지어내지 마라.",
        f"{SAFETY_TOPIC_TEXT_KO}은 단정하지 마라.",
        SAFETY_POLICY_KO,
        ANSWER_FORMAT_KO,
        "```json",
        json.dumps(package, ensure_ascii=False, indent=2),
        "```",
    ]
    history_context = _history_lines(history)
    if history_context:
        lines.extend(["", "최근 대화", *history_context])
    if follow_up:
        lines.append(f"\n사용자의 추가 질문: {follow_up}")
    lines.append(
        "\n위 데이터를 바탕으로 따뜻하고 담백한 조언형 해석을 한국어로 작성하라. "
        "없는 정보는 지어내지 마라."
    )
    return "\n".join(lines)


# --- LLM 제공자 ----------------------------------------------------------
def _select_provider() -> str | None:
    """사용할 LLM 제공자를 정한다. 없으면 None(fallback)."""
    explicit = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if explicit in ("openai", "gemini"):
        # 명시했어도 키가 없으면 fallback
        if explicit == "openai" and os.environ.get("OPENAI_API_KEY"):
            return "openai"
        if explicit == "gemini" and os.environ.get("GOOGLE_API_KEY"):
            return "gemini"
        return None
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return None


def _get_llm():
    """선택된 제공자의 LangChain chat 모델을 만든다. 실패하면 None."""
    provider = _select_provider()
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI

            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            return ChatOpenAI(model=model, temperature=0.7)
        except Exception:
            return None
    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
            return ChatGoogleGenerativeAI(model=model, temperature=0.7)
        except Exception:
            return None
    return None


def generate_answer(
    package: dict,
    follow_up: str | None = None,
    history: list[dict] | None = None,
) -> dict:
    """LLM 해석을 생성한다. 키가 없거나 실패하면 fallback 답변을 쓴다.

    반환: {"text": str, "mode": "llm"|"fallback"}
    """
    llm = _get_llm()
    if llm is not None:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = llm.invoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT_KO),
                    HumanMessage(
                        content=build_user_prompt(
                            package,
                            follow_up=follow_up,
                            history=history,
                        )
                    ),
                ]
            )
            text = getattr(response, "content", None) or str(response)
            return {"text": text.strip(), "mode": "llm"}
        except Exception:
            # LLM 호출 실패 시 조용히 fallback 으로 내려간다. (NFR-1)
            pass
    return {
        "text": fallback_answer(package, follow_up=follow_up, history=history),
        "mode": "fallback",
    }


def _normalized_text(value: str | None) -> str:
    return str(value or "").replace(" ", "").lower()


def _has_safety_topic(value: str | None) -> bool:
    normalized = _normalized_text(value)
    if not normalized:
        return False
    return any(_normalized_text(topic) in normalized for topic in SAFETY_TOPICS_KO)


def _has_unsafe_claim(value: str | None) -> bool:
    normalized = _normalized_text(value)
    if not normalized:
        return False
    return _has_safety_topic(value) or any(
        _normalized_text(term) in normalized for term in DETERMINISTIC_CLAIM_KO
    )


def _safe_tool_text(value) -> str:
    text = str(value or "").strip()
    if not text or _has_unsafe_claim(text):
        return ""
    return text


def _comma(values) -> str:
    return ", ".join(
        safe_value
        for safe_value in (_safe_tool_text(value) for value in (values or []))
        if safe_value
    )


def _basis_lines(profile: dict) -> list[str]:
    saju = profile.get("saju_chart", {})
    fe = profile.get("five_elements")
    lines = []
    pillars = [
        ("년주", saju.get("year_pillar")),
        ("월주", saju.get("month_pillar")),
        ("일주", saju.get("day_pillar")),
        ("시주", saju.get("hour_pillar")),
    ]
    shown = [f"{key} {value}" for key, value in pillars if value]
    if shown:
        lines.append("- 사주팔자: " + ", ".join(shown))
    if saju.get("time_precision") == "unknown":
        lines.append("- 출생시간 정보가 없어 시주는 제외하고 제한적으로 해석합니다.")
    if fe:
        strong = config.ELEMENT_KO.get(fe.get("strong_element"), fe.get("strong_element"))
        weak = config.ELEMENT_KO.get(fe.get("weak_element"), fe.get("weak_element"))
        recommended = config.ELEMENT_KO.get(
            fe.get("recommended_element"), fe.get("recommended_element")
        )
        summary = _safe_tool_text(fe.get("summary"))
        if summary:
            lines.append("- 오행 분석: " + summary)
        elif strong and weak:
            lines.append(f"- 오행 분석: {strong} 기운이 강하고 {weak} 기운이 보완 대상입니다.")
        if recommended:
            lines.append(f"- 보완 기운: {recommended}")
    return lines or ["- 계산된 tool JSON에서 확인 가능한 근거가 부족합니다."]


def _today_lines(results: dict) -> list[str]:
    today = results.get("today_luck") or {}
    lines = []
    if today.get("score") is not None:
        score_range = today.get("score_range") or "0-100"
        lines.append(f"- 오늘의 행운 점수: {today.get('score')}점 ({score_range})")
    for signal in today.get("signals", []) or []:
        safe_signal = _safe_tool_text(signal)
        if safe_signal:
            lines.append(f"- 신호: {safe_signal}")
    for caution in today.get("cautions", []) or []:
        safe_caution = _safe_tool_text(caution)
        if safe_caution:
            lines.append(f"- 주의: {safe_caution}")
    return lines


def _luck_score_lines(results: dict) -> list[str]:
    today = results.get("today_luck") or {}
    lines = []
    if today.get("score") is not None:
        lines.append(f"- 행운 점수: {today.get('score')}점")
        lines.append(f"- 점수 범위: {today.get('score_range') or '0-100'}")
    return lines


def _menu_summary(intent: str, results: dict, profile: dict) -> str:
    if intent in ("today_fortune", "luck_score"):
        today = results.get("today_luck") or {}
        if today.get("score") is not None:
            return f"오늘은 {today.get('score')}점 흐름으로, 신호와 주의점을 함께 보는 날입니다."
        return "오늘의 흐름은 계산된 신호가 제한적이어서 가볍게 참고하는 정도가 좋습니다."
    if intent == "lucky_color":
        colors = _comma((results.get("lucky_factors") or {}).get("lucky_colors"))
        return f"오늘의 보완 색은 {colors} 쪽으로 정리됩니다." if colors else "행운 색깔 결과가 아직 충분하지 않습니다."
    if intent == "lucky_item":
        items = _comma((results.get("lucky_factors") or {}).get("lucky_items"))
        return f"오늘의 보완 아이템은 {items} 쪽으로 정리됩니다." if items else "행운 아이템 결과가 아직 충분하지 않습니다."
    if intent == "love":
        return "관계운은 상대를 단정하기보다 대화 방식과 감정의 균형을 돌아보는 흐름입니다."
    if intent == "wealth":
        return "재물운은 결과 예측보다 소비 리듬과 계획을 점검하는 자기성찰로 보는 편이 좋습니다."
    if intent == "life_flow":
        return "인생흐름은 특정 사건을 맞히기보다 시기별 태도와 균형을 넓게 살피는 해석입니다."
    return "사주와 오행의 균형을 바탕으로 성향과 보완점을 가볍게 살펴봅니다."


def _menu_detail(intent: str, results: dict, profile: dict) -> tuple[str, list[str]]:
    lucky = results.get("lucky_factors") or {}
    if intent == "saju_reading":
        return (
            "사주 풀이",
            [
                "- 강하게 드러난 기운은 장점으로 살리고, 부족한 기운은 일상의 리듬으로 보완해 보세요.",
                "- 이 해석은 성향을 단정하기보다 자기 점검용 힌트로 보는 것이 좋습니다.",
            ],
        )
    if intent == "luck_score":
        lines = _luck_score_lines(results)
        return ("행운 점수 해석", lines or ["- 행운 점수 결과가 충분히 계산되지 않았습니다."])
    if intent == "today_fortune":
        lines = _today_lines(results)
        return ("오늘의 운세 해석", lines or ["- 오늘의 세부 신호가 충분히 계산되지 않았습니다."])
    if intent == "lucky_color":
        lines = []
        colors = _comma(lucky.get("lucky_colors"))
        if colors:
            lines.append(f"- 행운 색깔: {colors}")
        reason = _safe_tool_text(lucky.get("reason"))
        if reason:
            lines.append(f"- 이유: {reason}")
        return ("행운 색깔 해석", lines or ["- 추천 색깔 결과가 충분하지 않습니다."])
    if intent == "lucky_item":
        lines = []
        items = _comma(lucky.get("lucky_items"))
        if items:
            lines.append(f"- 행운 아이템: {items}")
        reason = _safe_tool_text(lucky.get("reason"))
        if reason:
            lines.append(f"- 이유: {reason}")
        return ("행운 아이템 해석", lines or ["- 추천 아이템 결과가 충분하지 않습니다."])
    if intent == "love":
        return (
            "연애운 해석",
            [
                "- 관계에서는 속도를 정하기보다 말의 온도와 경청의 균형을 의식해 보세요.",
                "- 상대의 마음이나 결과를 확정하지 않고, 내가 조절할 수 있는 표현 방식에 집중합니다.",
            ],
        )
    if intent == "wealth":
        return (
            "재물운 해석",
            [
                "- 소비 기록을 가볍게 정리하고 충동적인 지출을 한 박자 늦춰 보는 데 도움이 됩니다.",
                "- 특정 자산이나 수익을 예측하지 않고, 계획과 습관을 점검하는 조언으로만 참고하세요.",
            ],
        )
    if intent == "life_flow":
        return (
            "인생흐름 해석",
            [
                "- 지금의 흐름은 장기적인 태도와 균형을 돌아보는 참고 신호로 볼 수 있습니다.",
                "- 특정 사건이나 절대적인 미래를 말하기보다, 선택의 방향을 차분히 점검하는 데 초점을 둡니다.",
            ],
        )
    return (
        "메뉴별 해석",
        ["- 계산된 사주와 오행 결과를 바탕으로 가벼운 자기성찰 힌트를 제공합니다."],
    )


def _recent_context_lines(history: list[dict] | None) -> list[str]:
    if not history:
        return []
    lines = []
    for item in history[-3:]:
        role = item.get("role", "unknown")
        content = _safe_tool_text(item.get("content"))
        if content:
            lines.append(f"- {role}: {content}")
    return lines


def fallback_answer(
    package: dict,
    follow_up: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """LLM 없이 tool 결과만으로 만든 결정적 답변. (API 키 없을 때/실패 시)"""
    profile = package.get("profile", {})
    name = profile.get("name") or "당신"
    results = package.get("tool_result", {})
    label = package.get("menu_label", package.get("intent"))
    intent = package.get("intent")
    section_title, detail_lines = _menu_detail(intent, results, profile)
    history = history if history is not None else package.get("conversation_history")

    lines = [f"[{label}] {name} 님을 위한 해석입니다.", ""]
    lines.extend(["## 한 줄 요약", _menu_summary(intent, results, profile), ""])
    lines.append("## 계산 근거")
    lines.extend(_basis_lines(profile))
    recent_context = _recent_context_lines(history)
    if recent_context:
        lines.extend(["", "- 최근 대화 맥락(계산 근거가 아닙니다):", *recent_context])
    if follow_up:
        if _has_unsafe_claim(follow_up):
            lines.extend(
                [
                    "",
                    "- 추가 질문은 안전 정책상 단정할 수 없는 주제라 예측하지 않고, 자기성찰 조언으로만 다룹니다.",
                ]
            )
        else:
            lines.extend(["", f"- 추가 질문 반영: {follow_up}"])
    lines.extend(["", "## 메뉴별 해석", f"- 해석 유형: {section_title}"])
    lines.extend(detail_lines)
    lines.extend(
        [
            "",
            "## 오늘의 작은 제안",
            "- 오늘 바로 확정적인 결론을 내리기보다, 계산된 신호 중 하나만 작게 실천해 보세요.",
            "",
            "## 안내",
            "(LLM API 키가 없어 tool 결과 기반 기본 답변으로 표시했습니다.)",
            config.DISCLAIMER_KO,
        ]
    )
    return "\n".join(lines)
