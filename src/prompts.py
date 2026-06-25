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

SYSTEM_PROMPT_KO = (
    "너는 사주 기반 자기성찰 챗봇의 해설가다.\n"
    "다음 규칙을 반드시 지킨다.\n"
    "1. 너는 사주 계산을 직접 하지 않는다. 아래 JSON 에 있는 tool 결과만 근거로 해석한다.\n"
    "2. JSON 에 없는 정보는 추측하거나 지어내지 않는다.\n"
    "3. 계산 결과가 비어 있거나 불확실하면 '계산되지 않음' 또는 "
    "'출생시간 정보가 부족해 제한적으로 해석합니다' 라고 말한다.\n"
    "4. 건강, 질병, 수명, 사고, 투자 수익, 합격, 당첨 등은 단정하지 않는다.\n"
    "5. '반드시', '무조건', '위험하다' 같은 단정 표현 대신 "
    "'이런 흐름으로 해석할 수 있습니다' 같은 완화 표현을 쓴다.\n"
    "6. 답변은 한국어로, 엔터테인먼트와 자기성찰용 조언으로 작성한다.\n"
    "7. 계산 근거(사주팔자, 오행)를 짧게 곁들인다."
)


def build_llm_package(intent: str, profile_data: dict, tool_results: dict) -> dict:
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
    }


def build_user_prompt(package: dict, follow_up: str | None = None) -> str:
    """LLM user 메시지 문자열을 만든다."""
    label = package.get("menu_label", package.get("intent"))
    lines = [
        f"사용자가 '{label}' 을(를) 요청했다.",
        "아래는 tool 이 계산한 결과 JSON 이다. 이 데이터만 근거로 해석하라.",
        "```json",
        json.dumps(package, ensure_ascii=False, indent=2),
        "```",
    ]
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


def generate_answer(package: dict, follow_up: str | None = None) -> dict:
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
                    HumanMessage(content=build_user_prompt(package, follow_up)),
                ]
            )
            text = getattr(response, "content", None) or str(response)
            return {"text": text.strip(), "mode": "llm"}
        except Exception:
            # LLM 호출 실패 시 조용히 fallback 으로 내려간다. (NFR-1)
            pass
    return {"text": fallback_answer(package), "mode": "fallback"}


def fallback_answer(package: dict) -> str:
    """LLM 없이 tool 결과만으로 만든 결정적 답변. (API 키 없을 때/실패 시)"""
    profile = package.get("profile", {})
    name = profile.get("name") or "당신"
    saju = profile.get("saju_chart", {})
    fe = profile.get("five_elements")
    results = package.get("tool_result", {})
    label = package.get("menu_label", package.get("intent"))

    lines = [f"[{label}] {name} 님을 위한 해석입니다.", ""]

    pillars = [
        ("년주", saju.get("year_pillar")),
        ("월주", saju.get("month_pillar")),
        ("일주", saju.get("day_pillar")),
        ("시주", saju.get("hour_pillar")),
    ]
    shown = [f"{k} {v}" for k, v in pillars if v]
    if shown:
        lines.append("사주팔자: " + ", ".join(shown))
    if saju.get("time_precision") == "unknown":
        lines.append("출생시간 정보가 없어 시주는 제외하고 제한적으로 해석합니다.")

    if fe:
        strong = config.ELEMENT_KO.get(fe.get("strong_element"), fe.get("strong_element"))
        weak = config.ELEMENT_KO.get(fe.get("weak_element"), fe.get("weak_element"))
        if fe.get("summary"):
            lines.append("오행 분석: " + fe["summary"])
        elif strong and weak:
            lines.append(f"오행 분석: {strong} 기운이 강하고 {weak} 기운이 보완 대상입니다.")

    today = results.get("today_luck")
    if today:
        lines.append("")
        lines.append(f"오늘의 행운 점수: {today.get('score')}점")
        for signal in today.get("signals", []) or []:
            lines.append(f"- {signal}")
        for caution in today.get("cautions", []) or []:
            lines.append(f"※ {caution}")

    lucky = results.get("lucky_factors")
    if lucky:
        lines.append("")
        colors = ", ".join(lucky.get("lucky_colors", []) or [])
        items = ", ".join(lucky.get("lucky_items", []) or [])
        if colors:
            lines.append(f"행운 색깔: {colors}")
        if items:
            lines.append(f"행운 아이템: {items}")
        if lucky.get("reason"):
            lines.append(lucky["reason"])

    lines.append("")
    lines.append("(LLM API 키가 없어 tool 결과 기반 기본 답변으로 표시했습니다.)")
    lines.append(config.DISCLAIMER_KO)
    return "\n".join(lines)
