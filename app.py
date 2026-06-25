"""사주 기반 자기성찰 챗봇 — Streamlit UI (통합).

실행: streamlit run app.py
"""
from __future__ import annotations

import json
from datetime import date, time

import streamlit as st
from dotenv import load_dotenv

from src import config, prompts
from src.orchestrator import Orchestrator

load_dotenv()

# 팀원 도구 이름 -> 담당자 (pending 안내용)
TOOL_OWNER_KO = {
    config.TOOL_FIVE_ELEMENTS: "이윤서(오행 분석)",
    config.TOOL_TODAY_LUCK: "최호택(오늘 운세 점수)",
    config.TOOL_LUCKY_FACTORS: "전원정(행운 색깔/아이템)",
}

st.set_page_config(page_title="사주 자기성찰 챗봇", page_icon="🔮", layout="centered")


def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def render_header() -> None:
    st.title("🔮 사주 기반 자기성찰 챗봇")
    st.caption(config.DISCLAIMER_KO)


def render_input_form() -> dict | None:
    """사용자 입력 폼. 제출되면 user_info dict 를 돌려준다."""
    with st.form("user_info_form"):
        st.subheader("기본 정보 입력")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", value="민지")
            calendar_type = st.radio(
                "양력/음력", options=["solar", "lunar"],
                format_func=lambda x: "양력" if x == "solar" else "음력",
                horizontal=True,
            )
        with col2:
            gender = st.selectbox(
                "성별", options=["female", "male", "other", "unknown"],
                format_func=lambda x: {"female": "여성", "male": "남성",
                                       "other": "기타", "unknown": "선택안함"}[x],
            )
            is_leap_month = st.checkbox("윤달 (음력일 때만)", value=False)

        birth_date = st.date_input(
            "생년월일",
            value=date(1998, 3, 12),
            min_value=date(config.SUPPORTED_YEAR_MIN, 1, 1),
            max_value=date(config.SUPPORTED_YEAR_MAX, 12, 31),
        )
        time_unknown = st.checkbox("출생시간 모름", value=False)
        birth_time_value = st.time_input("출생시간", value=time(9, 0), disabled=time_unknown)

        submitted = st.form_submit_button("분석 시작", use_container_width=True)

    if not submitted:
        return None

    return {
        "name": name,
        "gender": gender,
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "birth_time": None if time_unknown else birth_time_value.strftime("%H:%M"),
        "calendar_type": calendar_type,
        "birth_time_unknown": bool(time_unknown),
        "is_leap_month": bool(is_leap_month),
    }


def render_pending_notice(pending: list[str]) -> None:
    if not pending:
        return
    owners = [TOOL_OWNER_KO.get(name, name) for name in pending]
    st.info(
        "다음 기능은 팀원 도구가 연결되면 활성화됩니다: " + ", ".join(owners)
    )


def render_profile(profile_data: dict) -> None:
    saju = profile_data.get("saju_chart", {})
    st.subheader("사주 프로필")
    cols = st.columns(4)
    labels = [("년주", "year_pillar"), ("월주", "month_pillar"),
              ("일주", "day_pillar"), ("시주", "hour_pillar")]
    for col, (label, key) in zip(cols, labels):
        col.metric(label, saju.get(key) or "—")
    if saju.get("time_precision") == "unknown":
        st.caption("출생시간 미상 → 시주는 제외하고 해석합니다.")

    fe = profile_data.get("five_elements")
    if fe:
        counts = fe.get("counts", {})
        readable = "  ".join(
            f"{config.ELEMENT_KO.get(k, k)} {counts.get(k, 0)}" for k in config.ELEMENTS
        )
        st.write("**오행 분석**:", readable)
        if fe.get("summary"):
            st.caption(fe["summary"])

    render_pending_notice(profile_data.get("pending_tools", []))


def render_menu_and_answer(orch: Orchestrator, profile: dict) -> None:
    st.subheader("무엇이 궁금하세요?")
    intents = list(config.MENU_REQUIRED_TOOLS.keys())
    intent = st.selectbox(
        "메뉴 선택",
        options=intents,
        format_func=lambda x: config.MENU_LABELS_KO.get(x, x),
    )

    if st.button("해석 보기", use_container_width=True):
        result = orch.answer(intent, profile)
        if not result.get("ok"):
            st.error(result["error"]["message"])
            return
        data = result["data"]
        with st.spinner("해석을 생성하는 중..."):
            answer = prompts.generate_answer(data["llm_package"])
        st.markdown(answer["text"])
        if answer["mode"] == "fallback":
            st.caption("ℹ️ LLM API 키가 없어 tool 결과 기반 기본 답변으로 표시되었습니다.")
        render_pending_notice(data.get("pending_tools", []))
        with st.expander("계산 결과(JSON) 보기"):
            st.json(data["tool_results"])


def main() -> None:
    render_header()
    orch = get_orchestrator()

    user_info = render_input_form()
    if user_info is not None:
        profile = orch.build_profile(json.dumps(user_info, ensure_ascii=False))
        if not profile.get("ok"):
            st.error(f"사주 계산 실패: {profile['error']['message']}")
            st.session_state.pop("profile", None)
        else:
            st.session_state["profile"] = profile

    profile = st.session_state.get("profile")
    if profile:
        render_profile(profile["data"])
        st.divider()
        render_menu_and_answer(orch, profile)

    st.divider()
    st.caption(config.DISCLAIMER_KO)


if __name__ == "__main__":
    main()
