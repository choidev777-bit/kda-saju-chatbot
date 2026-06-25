from src import config
from src.chat_intent import ConversationState, route_intent


def test_routes_today_fortune_from_natural_language():
    routed = route_intent("오늘 운세 봐줘", ConversationState())
    assert routed.intent == "today_fortune"
    assert routed.kind == "intent"


def test_routes_lucky_color_and_item_separately():
    assert route_intent("lucky color please", ConversationState()).intent == "lucky_color"
    assert route_intent("행운 아이템 알려줘", ConversationState()).intent == "lucky_item"


def test_routes_love_wealth_life_flow_and_saju_reading():
    assert route_intent("연애운", ConversationState()).intent == "love"
    assert route_intent("money and wealth luck", ConversationState()).intent == "wealth"
    assert route_intent("인생 흐름이 궁금해", ConversationState()).intent == "life_flow"
    assert route_intent("사주 풀이랑 오행", ConversationState()).intent == "saju_reading"


def test_follow_up_reuses_last_intent():
    state = ConversationState(last_intent="today_fortune")
    routed = route_intent("왜 그렇게 나와?", state)
    assert routed.kind == "follow_up"
    assert routed.intent == "today_fortune"
    assert routed.follow_up == "왜 그렇게 나와?"


def test_contextual_korean_question_reuses_last_answer_context():
    state = ConversationState(
        last_intent="saju_reading",
        last_tool_results={"five_elements": {"strongest": "토", "weakest": "금"}},
    )
    message = "토가 강하고 금의 기운이 적다는 것은 어떤 성격의 사람이라는 의미야?"

    routed = route_intent(message, state)

    assert routed.kind == "follow_up"
    assert routed.intent == "saju_reading"
    assert routed.follow_up == message


def test_ambiguous_message_without_answer_context_still_requests_clarification():
    state = ConversationState(last_intent="saju_reading")

    routed = route_intent("음 뭐부터 보면 좋을까", state)

    assert routed.kind == "clarify"
    assert routed.intent is None


def test_explicit_new_menu_switches_intent_even_after_previous_answer():
    state = ConversationState(
        last_intent="saju_reading",
        last_tool_results={"five_elements": {"strongest": "토"}},
    )

    routed = route_intent("오늘 운세 알려줘", state)

    assert routed.kind == "intent"
    assert routed.intent == "today_fortune"
    assert routed.follow_up is None


def test_blocked_topic_is_detected_before_tool_routing():
    routed = route_intent("투자 수익이랑 건강운 알려줘", ConversationState())
    assert routed.kind == "blocked"
    assert routed.intent is None


def test_english_high_stakes_topics_are_blocked_before_luck_routing():
    for message in (
        "Should I gamble today?",
        "Will I die soon?",
        "Will I win the lottery?",
        "Give me legal advice for court.",
        "Should I buy this stock for profit?",
    ):
        routed = route_intent(message, ConversationState())
        assert routed.kind == "blocked", message
        assert routed.intent is None
        assert routed.blocked_topic in config.EXCLUDED_TOPICS_KO
    assert routed.blocked_topic in config.EXCLUDED_TOPICS_KO


def test_unknown_message_requests_clarification():
    routed = route_intent("음 뭐부터 보면 좋을까", ConversationState())
    assert routed.kind == "clarify"
    assert routed.intent is None
