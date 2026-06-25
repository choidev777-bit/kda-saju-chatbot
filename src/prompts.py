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
import re
import time

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

# 페르소나(Role & Tone) — 사용자가 제공한 프롬프트 문서 기준.
PERSONA_KO = (
    "너는 사주 명리학과 현대적 멘탈 코칭을 결합한 전문 사주 상담가다.\n"
    "- 정중하면서도 군더더기 없는 담담한 어조(~입니다, ~하세요)를 유지한다.\n"
    "- 뻔한 위로나 추상적인 명리학 용어 나열 대신, 내담자의 성향을 꿰뚫어 보는 날카로운 "
    "분석('팩폭')과 일상에서 즉시 실천할 수 있는 구체적인 개운법(색상·조명·공간 배치·대화법·"
    "식습관·소품 등)을 함께 제시한다.\n"
    "- 각 대주제는 시적인 비유를 담은 소제목으로 시작한다."
)

# 메뉴 공통 출력 규칙(세부 양식은 메뉴별 MENU_FORMATS_KO 가 결정한다).
ANSWER_FORMAT_KO = (
    "답변은 한국어 Markdown으로 작성하고, 사용자가 선택한 메뉴의 지정 출력 양식을 반드시 따른다. "
    "각 분석에는 tool 결과를 근거로 한 해석과, 바로 실천 가능한 개운법을 함께 담는다."
)

SYSTEM_PROMPT_KO = (
    f"{PERSONA_KO}\n\n"
    "다음 규칙을 반드시 지킨다.\n"
    "1. 사주 계산을 직접 하지 않는다. 아래 JSON 의 tool 결과(사주팔자/오행/십신/지장간/"
    "신강신약/용신/신살/대운/일진/행운요소)만 근거로 해석한다.\n"
    "2. JSON 에 없는 정보(특히 제공되지 않은 십신·신살·대운 등)는 지어내지 않는다. "
    "데이터가 비면 그 항목은 생략하거나 '제공된 데이터로는 제한적으로 봅니다' 라고 말한다.\n"
    "3. 대화 이력과 추가 질문은 맥락 이해용이며 계산 근거가 아니다.\n"
    "4. 출생시간이 없으면 시주 기반 해석은 제외하고 제한적으로 해석한다.\n"
    f"5. {SAFETY_TOPIC_TEXT_KO} 등 금지 주제는 예측·수치·시기·확률·단정을 제공하지 않고 "
    "자기성찰 관점으로 안내한다.\n"
    "6. '팩폭'은 성향·심리에 대한 날카로운 통찰일 뿐이며, 금지 주제나 미래를 단정하는 표현이 "
    "아니다. 금지 주제에는 '반드시·무조건·위험하다' 같은 단정 표현을 쓰지 않는다.\n"
    "7. 답변은 한국어 Markdown, 엔터테인먼트와 자기성찰용 조언으로 작성한다.\n"
    "8. 사용자가 선택한 메뉴의 지정 출력 양식(아래)을 반드시 따른다.\n"
    f"{SAFETY_POLICY_KO}\n"
    f"{ANSWER_FORMAT_KO}"
)

# --- 메뉴별 출력 양식 (사용자 제공 프롬프트 문서 기준) -------------------
# 각 양식은 tool_result 의 데이터(saju_chart/five_elements/myeongri/iljin/
# lucky_factors/today_luck)를 근거로 채운다. 데이터에 없는 항목은 지어내지 않는다.
_FORMAT_SAJU_READING = """[사주 풀이] 출력 양식
먼저 "사주 풀이"로 시작하고, 만세력 표를 제시한다(saju_chart 의 한자/한글 간지 + myeongri.sipsin 의 십신):
구분 | 천간 | 지지
--- | --- | ---
연주 | [천간 한자]([한글], [십신]) | [지지 한자]([한글], [십신])
월주 | ... | ...
일주 | [천간 한자]([한글], 일간) | [지지 한자]([한글], [십신])
시주 | ... | ...   (출생시간 없으면 시주 행은 생략)

이어서: "오행 개수는 목 N, 화 N, 토 N, 금 N, 수 N입니다." (five_elements.counts)
그리고 오행의 과다/고립/부족과 성향 총평을 직관적 비유를 담아 2~3문장으로 서술한다.

그다음 시적인 비유가 담긴 소제목의 5개 섹션을 쓴다. 각 섹션은 '- **항목**: 분석' 과
'- **개운법**: 처방' 두 줄로 구성한다.
### [소제목 1]
- **원국 분석**: 일간 특징, 월지와의 관계, 신강/신약(myeongri.body_strength)과 표면/내면 성향
- **개운법**: 인테리어·조명·색상·소품 등 공간/시각적 처방
### [소제목 2]
- **십신 및 신살 분석**: myeongri.sipsin/myeongri.sinsal 중 두드러진 기운·귀인의 영향(장점과 주의점)
- **개운법**: 기록 습관(노션/블로그 등)·식습관 처방
### [소제목 3]
- **일주 분석**: 일주 특성·내면 심리, 신살이 인간관계/사랑에 미치는 영향
- **개운법**: 대화 방식·스타일링/패션 컬러 제안
### [소제목 4]
- **성격의 명과 암(팩폭)**: 방어기제·고집·숨겨진 심리를 예리하게 지적
- **개운법**: 관계 유지법·상황별 추천 착장 톤
### [소제목 5]
- **종합 성격 분석**: 표면 성격과 내면 심리의 모순/조화, 행동 패턴 정리
- **개운법**: 하루 루틴·추천 취미(감정 기록·운동 등)

마지막에:
**" [사주 전체를 관통하는 한 줄 격언] "**
[따뜻한 격려의 총평 1단락]

- **행운의 색깔**: lucky_factors.lucky_colors (또는 용신 오행 기반 2~3개)
- **행운의 숫자**: 가벼운 제안 2~3개(데이터 근거가 아니며 단정하지 않음)
- **행운의 방향**: 가벼운 제안
- **멘탈 관리 습관**: 핵심 행동 지침 3가지"""

_FORMAT_TODAY = """[오늘 운세] 출력 양식 (오늘의 일진 = iljin, 오늘의 점수 = today_luck)
### 📅 오늘의 에너지 총평: [시적인 소제목]
- **오늘의 흐름**: 내 사주와 오늘 일진(iljin.ganji)이 만나 형성하는 에너지 총평. 오늘 유독 들기 쉬운
  마음가짐이나 방어기제를 2~3문장으로 날카롭게 서술.

### 💡 오늘의 팩폭 (주의할 행동)
- 오늘 저지르기 쉬운 실수·감정 과부하·욱하는 지점을 직설적으로 지적
- **행동 교정**: 그 실수를 막을 구체적 대처법(예: 카톡 답장 3분 늦추기, 결제 전 장바구니에 담아두기)

### 💼 오늘의 업무 & 인간관계 팁
- **소통 원칙**: 오늘 트러블을 피하거나 이득을 얻는 대화법
- **시간 관리**: 오늘 효율이 좋은 시간대·업무 스타일 제안

**" 오늘의 한 줄 주문: [단호한 문장 한 줄] "**
- **행운의 시간대**: 집중하면 좋은 때(가벼운 제안)
- **행운의 장소**: 오늘 들르면 좋은 공간
- **퇴근 후 멘탈 미션**: 하루를 마무리하는 저녁 루틴 1가지"""

_FORMAT_LUCKY_ITEM = """[행운 아이템] 출력 양식
### [시적인 소제목]
- **방향 및 아이템적 요인**: 용신/희신(myeongri.yongsin)과 오행을 바탕으로 한 공간적 분석
- **개운법**: 추천 아이템·장신구(lucky_factors.lucky_items)와 배치/활용법"""

_FORMAT_LUCKY_COLOR = """[행운색] 출력 양식
### [시적인 소제목]
- **행운색 분석(색채 개운법)**: 용신/희신 오행(myeongri.yongsin)에 해당하는 색(lucky_factors.lucky_colors)을
  명확히 짚고, 이 색이 부족한 기운을 어떻게 보완하는지 풀이
- **개운법**: 의류·소품·가방·지갑·이불·인테리어 포인트 컬러 등 일상에서의 구체적 매치/활용법"""

_FORMAT_LOVE = """[연애운] 출력 양식
### [시적인 소제목]
- **연애/이성운**: 배우자 자리(일지)와 재성/관성(myeongri.sipsin)을 통한 연애 스타일·인연의 특징
- **개운법**: 데이트 장소·향/향수 조절·소통 팁"""

_FORMAT_WEALTH = """[재물운] 출력 양식
### [시적인 소제목]
- **재물운**: 재성(myeongri.sipsin 의 편재/정재) 상태로 본 돈을 대하는 태도와 재테크 시 주의점
  (특정 수익·종목·시기는 단정하지 않는다)
- **개운법**: 통장 관리법·피해야 할 소비 습관·계획 점검"""

_FORMAT_LIFE_FLOW = """[인생흐름] 출력 양식 (대운 = myeongri.daewoon)
### [시적인 소제목]
- **인생 전체 흐름(대운 기반 총평)**: daewoon.periods 를 바탕으로 전반기/중반기/후반기의 환경과 테마를
  거시적으로 서술
- **시기별 구체적 흐름**: 대운 구간(age_from~age_to)별로
  * **초년 운**: 학업 환경·부모덕/독립성 형성
  * **중년 운**: 사회적 성취·전성기·가정의 핵심 에너지와 주의점
  * **말년 운**: 후반부의 안정·건강·명예·만족도가 채워지는 형태
  (daewoon 데이터가 없으면 특정 사건을 단정하지 말고 태도/균형 관점으로 안내)
- **인생 개운법**: 황금기를 앞당기거나 교운기를 지혜롭게 넘기기 위한 장기적 마음가짐/생활 태도"""

MENU_FORMATS_KO = {
    "saju_reading": _FORMAT_SAJU_READING,
    "today_fortune": _FORMAT_TODAY,
    "luck_score": _FORMAT_TODAY,
    "lucky_item": _FORMAT_LUCKY_ITEM,
    "lucky_color": _FORMAT_LUCKY_COLOR,
    "love": _FORMAT_LOVE,
    "wealth": _FORMAT_WEALTH,
    "life_flow": _FORMAT_LIFE_FLOW,
}


def menu_format(intent: str | None) -> str:
    """메뉴(intent)에 해당하는 출력 양식 텍스트. 없으면 사주 풀이 양식."""
    return MENU_FORMATS_KO.get(intent or "", _FORMAT_SAJU_READING)


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
        "",
        "아래 메뉴 출력 양식을 그대로 따르라. 소제목의 시적 비유와 개운법까지 포함한다:",
        menu_format(package.get("intent")),
        "",
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


def _llm_messages(
    package: dict,
    follow_up: str | None = None,
    history: list[dict] | None = None,
) -> list:
    """system/human 메시지 쌍을 만든다. invoke 와 stream 이 공유한다."""
    from langchain_core.messages import HumanMessage, SystemMessage

    return [
        SystemMessage(content=SYSTEM_PROMPT_KO),
        HumanMessage(
            content=build_user_prompt(package, follow_up=follow_up, history=history)
        ),
    ]


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
            response = llm.invoke(_llm_messages(package, follow_up, history))
            text = getattr(response, "content", None) or str(response)
            return {"text": text.strip(), "mode": "llm"}
        except Exception:
            # LLM 호출 실패 시 조용히 fallback 으로 내려간다. (NFR-1)
            pass
    return {
        "text": fallback_answer(package, follow_up=follow_up, history=history),
        "mode": "fallback",
    }


def iter_typewriter(text: str, *, delay: float | None = None):
    """문자열을 어절 단위로 끊어 타이핑하듯 흘려보내는 제너레이터.

    LLM 키가 없을 때의 fallback 답변과 정형(canned) 안내문에도 '주르륵' 효과를
    주기 위한 헬퍼다. 조각을 모두 합치면 원문과 완전히 동일하다.

    지연 시간은 ``SAJU_STREAM_DELAY`` 환경 변수로 조절한다(테스트는 0 으로 둔다).
    """
    if delay is None:
        try:
            delay = float(os.environ.get("SAJU_STREAM_DELAY", "0.02"))
        except (TypeError, ValueError):
            delay = 0.02
    text = str(text or "")
    if not text:
        return
    # 공백 묶음과 비공백(어절) 묶음을 번갈아 내보낸다. 마크다운 구조와 줄바꿈은 보존된다.
    for token in re.findall(r"\s+|\S+", text):
        yield token
        if delay > 0:
            time.sleep(delay)


def _stream_llm_chunks(
    llm,
    package: dict,
    follow_up: str | None,
    history: list[dict] | None,
):
    """LLM 토큰을 흘려보내고, 한 조각이라도 보냈으면 True 를 반환한다."""
    produced = False
    try:
        for chunk in llm.stream(_llm_messages(package, follow_up, history)):
            piece = getattr(chunk, "content", "") or ""
            if piece:
                produced = True
                yield piece
    except Exception:
        # 스트리밍 도중 오류: 이미 일부를 보냈으면 그대로 끝내고,
        # 아무것도 못 보냈으면 호출부가 fallback 으로 내려가게 한다. (NFR-1)
        pass
    return produced


def stream_answer(
    package: dict,
    follow_up: str | None = None,
    history: list[dict] | None = None,
):
    """답변을 조각 단위로 흘려보내는 제너레이터.

    - LLM 키가 있으면 실제 토큰 스트리밍을 시도한다.
    - 키가 없거나 스트리밍이 아무 내용도 만들지 못하면, 결정적 fallback
      답변을 타이핑하듯 끊어서 내보낸다. (NFR-1)

    조각을 모두 합치면 한 번에 생성한 답변과 동일한 전체 텍스트가 된다.
    """
    llm = _get_llm()
    if llm is not None:
        produced = yield from _stream_llm_chunks(llm, package, follow_up, history)
        if produced:
            return
    yield from iter_typewriter(
        fallback_answer(package, follow_up=follow_up, history=history)
    )


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


def _myeongri_lines(results: dict) -> list[str]:
    """명리 도구 결과를 안전한 계산 근거 줄로 정리한다(있을 때만)."""
    myeongri = results.get("myeongri") or {}
    if not myeongri:
        return []
    lines: list[str] = []
    il_gan = myeongri.get("il_gan")
    element_ko = myeongri.get("il_gan_element_ko")
    if il_gan:
        suffix = f"({element_ko})" if element_ko else ""
        lines.append(f"- 일간(나 자신): {il_gan}{suffix}")
    body = myeongri.get("body_strength") or {}
    if body.get("label"):
        lines.append(f"- 신강/신약(근사): {body['label']}")
    sinsal_names = list(
        dict.fromkeys(item.get("name") for item in (myeongri.get("sinsal") or []) if item.get("name"))
    )
    if sinsal_names:
        lines.append(f"- 신살/귀인: {', '.join(sinsal_names)}")
    daewoon = myeongri.get("daewoon") or {}
    if daewoon.get("available"):
        lines.append(
            f"- 대운(근사): {daewoon.get('start_age')}세부터 {daewoon.get('direction')}"
        )
    return lines


def _iljin_lines(results: dict) -> list[str]:
    """오늘의 일진(간지) 근거 줄."""
    iljin = results.get("iljin") or {}
    if not iljin.get("ganji"):
        return []
    stem_el = iljin.get("stem_element_ko")
    branch_el = iljin.get("branch_element_ko")
    detail = f" ({stem_el}/{branch_el})" if stem_el and branch_el else ""
    return [f"- 오늘 일진: {iljin['ganji']}{detail}"]


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
    lines.extend(_myeongri_lines(results))
    if intent in ("today_fortune", "luck_score"):
        lines.extend(_iljin_lines(results))
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
