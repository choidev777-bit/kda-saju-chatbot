from src import config, prompts


def sample_package(intent="today_fortune", tool_result=None):
    return {
        "intent": intent,
        "menu_label": config.MENU_LABELS_KO.get(intent, intent),
        "profile": {
            "name": "민지",
            "saju_chart": {
                "year_pillar": "무인",
                "month_pillar": "계묘",
                "day_pillar": "병진",
                "hour_pillar": "정사",
                "time_precision": "known",
            },
            "five_elements": {
                "counts": {"wood": 3, "fire": 2, "earth": 2, "metal": 0, "water": 1},
                "strong_element": "wood",
                "weak_element": "metal",
                "recommended_element": "metal",
                "summary": "목 기운이 강하고 금 기운이 보완 대상입니다.",
            },
        },
        "tool_result": tool_result
        or {
            "today_luck": {
                "score": 82,
                "score_range": "0-100",
                "signals": ["정리와 집중에 어울리는 흐름입니다."],
                "cautions": ["중요한 선택은 한 번 더 확인해 보세요."],
            }
        },
        "answer_policy": config.ANSWER_POLICY,
    }


def test_build_user_prompt_includes_follow_up_and_history():
    package = sample_package()
    history = [
        {"role": "user", "content": "오늘 운세 봐줘"},
        {"role": "assistant", "content": "오늘의 흐름을 정리해 드릴게요."},
    ]

    prompt = prompts.build_user_prompt(
        package,
        follow_up="왜 그렇게 해석해?",
        history=history,
    )

    assert "왜 그렇게 해석해?" in prompt
    assert "최근 대화" in prompt
    assert "오늘 운세 봐줘" in prompt
    assert "계산 근거로 사용하지 말고" in prompt


def test_build_user_prompt_requires_tool_json_only_and_safety_rules():
    prompt = prompts.build_user_prompt(sample_package())

    assert "tool JSON만" in prompt
    assert "JSON에 없는 정보" in prompt
    for word in (
        "건강",
        "질병",
        "수명",
        "사고",
        "투자 수익",
        "입학",
        "합격",
        "복권",
        "로또",
        "당첨",
    ):
        assert word in prompt


def test_generate_answer_sends_follow_up_and_history_to_human_message(monkeypatch):
    captured = {}

    class FakeResponse:
        content = "ok"

    class FakeLLM:
        def invoke(self, messages):
            captured["messages"] = messages
            return FakeResponse()

    monkeypatch.setattr(prompts, "_get_llm", lambda: FakeLLM())
    answer = prompts.generate_answer(
        sample_package(),
        follow_up="이유만 짧게",
        history=[{"role": "user", "content": "오늘 어때?"}],
    )

    assert answer == {"text": "ok", "mode": "llm"}
    human_content = captured["messages"][1].content
    assert "이유만 짧게" in human_content
    assert "오늘 어때?" in human_content


def test_generate_answer_falls_back_when_api_key_is_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    answer = prompts.generate_answer(sample_package())

    assert answer["mode"] == "fallback"
    assert config.DISCLAIMER_KO in answer["text"]


def test_fallback_today_fortune_uses_consistent_markdown_format():
    text = prompts.fallback_answer(sample_package())

    assert text.startswith("[오늘의 운세] 민지 님을 위한 해석입니다.")
    for heading in ("## 한 줄 요약", "## 계산 근거", "## 메뉴별 해석", "## 오늘의 작은 제안", "## 안내"):
        assert heading in text
    assert "해석 유형: 오늘의 운세 해석" in text
    assert "82점" in text
    assert config.DISCLAIMER_KO in text


def test_fallback_luck_score_uses_score_specific_template():
    text = prompts.fallback_answer(sample_package("luck_score"))

    assert "[오늘의 행운 점수]" in text
    assert "해석 유형: 행운 점수 해석" in text
    assert "82점" in text
    assert "0-100" in text
    assert "신호:" not in text
    assert "주의:" not in text


def test_fallback_filters_unsafe_today_luck_tool_text():
    package = sample_package(
        "today_fortune",
        {
            "today_luck": {
                "score": 55,
                "score_range": "0-100",
                "signals": ["오늘 로또 당첨 번호가 보입니다.", "정리하기 좋은 흐름입니다."],
                "cautions": ["사고가 반드시 납니다.", "중요한 선택은 한 번 더 확인해 보세요."],
            }
        },
    )

    text = prompts.fallback_answer(package)

    assert "정리하기 좋은 흐름입니다." in text
    assert "중요한 선택은 한 번 더 확인해 보세요." in text
    for word in ("로또", "당첨", "사고", "반드시"):
        assert word not in text


def test_fallback_includes_recent_safe_history_as_context_only():
    package = sample_package()
    package["conversation_history"] = [
        {"role": "user", "content": "오늘 운세 봐줘"},
        {"role": "assistant", "content": "오늘의 흐름을 정리했어요."},
        {"role": "user", "content": "로또 당첨도 알려줘"},
    ]

    text = prompts.fallback_answer(package)

    assert "최근 대화 맥락" in text
    assert "오늘 운세 봐줘" in text
    assert "계산 근거가 아닙니다" in text
    assert "로또" not in text
    assert "당첨" not in text


def test_fallback_blocked_follow_up_is_not_echoed_or_predicted():
    text = prompts.fallback_answer(
        sample_package(),
        follow_up="로또 당첨 번호와 투자 수익을 알려줘",
    )

    for word in ("로또", "당첨", "투자 수익"):
        assert word not in text
    assert "안전 정책" in text
    assert "자기성찰" in text


def test_fallback_lucky_color_is_menu_specific():
    package = sample_package(
        "lucky_color",
        {
            "lucky_factors": {
                "lucky_colors": ["흰색", "금색"],
                "lucky_items": ["시계"],
                "reason": "금 기운을 보완하기 위한 추천입니다.",
            }
        },
    )

    text = prompts.fallback_answer(package)

    assert "[행운 색깔]" in text
    assert "흰색, 금색" in text
    assert "행운 아이템" not in text


def test_fallback_lucky_item_is_menu_specific():
    package = sample_package(
        "lucky_item",
        {
            "lucky_factors": {
                "lucky_colors": ["흰색"],
                "lucky_items": ["시계", "금속 액세서리"],
                "reason": "금 기운을 보완하기 위한 추천입니다.",
            }
        },
    )

    text = prompts.fallback_answer(package)

    assert "[행운 아이템]" in text
    assert "시계, 금속 액세서리" in text
    assert "행운 색깔" not in text


def test_fallback_wealth_is_safe_not_investment_prediction():
    text = prompts.fallback_answer(sample_package("wealth", {}))

    assert "투자 수익" not in text
    assert "오릅니다" not in text
    assert "소비" in text or "계획" in text
    assert config.DISCLAIMER_KO in text


def test_fallback_life_flow_avoids_lifespan_claims():
    text = prompts.fallback_answer(sample_package("life_flow", {}))

    assert "수명" not in text
    assert "몇 살" not in text
    assert "흐름" in text


def test_fallback_avoids_admission_and_lottery_claims():
    text = prompts.fallback_answer(sample_package("today_fortune"))

    for word in ("입학", "입시", "합격", "복권", "로또", "당첨"):
        assert word not in text
    assert "자기성찰" in text or config.DISCLAIMER_KO in text


def test_build_llm_package_accepts_conversation_context():
    package = prompts.build_llm_package(
        "saju_reading",
        sample_package()["profile"],
        {},
        user_message="사주 풀이해줘",
        conversation_history=[{"role": "user", "content": "안녕"}],
        last_intent="today_fortune",
    )

    assert package["user_message"] == "사주 풀이해줘"
    assert package["conversation_history"][0]["content"] == "안녕"
    assert package["last_intent"] == "today_fortune"


def test_build_llm_package_includes_explicit_safety_policy():
    package = prompts.build_llm_package(
        "today_fortune",
        sample_package()["profile"],
        sample_package()["tool_result"],
    )

    policy = package["safety_policy"]
    assert policy["purpose"] == "entertainment_and_self_reflection"
    assert "tool_result" in policy["grounding"]
    for word in ("질병", "수명", "사고", "입학", "합격", "복권", "로또", "당첨"):
        assert word in policy["blocked_topics"]
