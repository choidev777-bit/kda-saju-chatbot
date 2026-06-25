# Implementation Plan: Contextual Follow-Up Conversation Flow

## Summary

Change the conversation router so the chatbot continues from prior context by default after a successful answer. The smallest safe implementation is to keep `ConversationState.last_intent` and `last_tool_results` as the deciding context, then reserve `clarify` for cases where no profile/answer context exists.

## Code Review Findings

### `src/chat_intent.py`

- `route_intent()` currently checks blocked topics, then narrow follow-up tokens, then intent matching, then `clarify`.
- `_looks_like_follow_up()` is too keyword-bound for Korean natural conversation.
- `_match_intent()` already recognizes explicit menu changes and should remain the source of truth for supported menu requests.

### `src/orchestrator.py`

- `handle_message()` already has the desired continuation path at lines 284-303: when `routed.kind == "follow_up"` and `conv.last_tool_results` exists, it builds a package from previous tool results and does not rerun tools.
- The bug happens before this path because routing returns `clarify`.
- No tool contract change is needed.

### `src/prompts.py`

- `build_llm_package()` already accepts `user_message`, `conversation_history`, and `last_intent`.
- `build_user_prompt()` already tells the LLM that recent history is context only and tool JSON is the factual basis.
- This supports contextual follow-ups without letting the LLM calculate saju directly.

### `app.py`

- Normal chat submissions use `Orchestrator.handle_message()`.
- Quick actions use a forced-intent compatibility path and then sync `last_intent`/`last_tool_results`, so subsequent chat submissions can use context.
- Clarify text appears because `answer_from_handle_message()` receives `reply_kind="clarify"` and no package.

### Tests

- Current follow-up tests only cover obvious phrases such as `why?` and `왜 그렇게 나와?`.
- There is no regression coverage for Korean contextual questions like `어떤 성격`, `무슨 뜻`, or `의미야`.

## Proposed Algorithm

Update `route_intent()` in `src/chat_intent.py`:

1. Normalize input as today.
2. Keep `_blocked_topic()` first.
3. Compute `matched_intent = _match_intent(text, lowered)`.
4. Add a helper such as `_has_answer_context(current)`:
   - true when `current.last_intent` is set and `current.last_tool_results` is non-empty.
5. Add a helper such as `_looks_like_contextual_question(text, lowered)`:
   - true for Korean/English meaning and elaboration phrases, e.g. `의미`, `뜻`, `무슨뜻`, `어떤`, `성격`, `설명`, `말이야`, `means`, `meaning`, `what does`.
6. Route as follow-up when answer context exists and:
   - `_looks_like_follow_up()` is true, or
   - `_looks_like_contextual_question()` is true, or
   - no explicit `matched_intent` exists.
7. Route as a new intent when `matched_intent` exists and it is not being treated as a contextual follow-up.
8. Return `clarify` only when there is no matched intent and no answer context.

Important ordering:

- Safety stays first.
- Explicit different menu requests should still switch menus.
- Ambiguous post-answer messages should continue the conversation instead of showing the menu prompt.

## Implementation Steps

1. Add regression tests in `tests/test_chat_intent.py`.
   - `test_contextual_korean_question_reuses_last_intent()`
   - Example: `토가 강하고 금의 기운이 적다는 것은 어떤 성격의 사람이라는 의미야?`
   - Assert `kind == "follow_up"` and `intent == "saju_reading"`.
   - Add a no-context assertion that the same kind of unsupported message does not become a follow-up without `last_intent`/`last_tool_results`.

2. Add orchestrator regression coverage.
   - Extend `tests/test_chat_flow.py` or `tests/test_orchestrator.py`.
   - Set state with `profile`, `last_intent="saju_reading"`, and previous `last_tool_results`.
   - Call `handle_message()` with the example follow-up.
   - Assert `reply_kind == "follow_up"`, `tools_run == []`, and the package contains the previous tool result.

3. Update `src/chat_intent.py`.
   - Add `_has_answer_context()`.
   - Add `_looks_like_contextual_question()`.
   - Reorder `route_intent()` so contextual fallback can happen after blocked-topic detection and explicit intent inspection.
   - Keep `_match_intent()` token tables unchanged unless a test reveals a menu-specific phrase gap.

4. Review `src/prompts.py` only if tests show the fallback answer is confusing.
   - Expected first pass: no prompt changes.
   - Optional follow-up polish: if `follow_up` exists, make fallback answer label it as "이전 답변에 대한 추가 질문" rather than a generic menu answer.

5. Update docs if behavior changes materially.
   - `README.md`: mention that follow-up questions reuse recent context and previous tool results.
   - `ARCHITECTURE.md`: update conversation routing notes if needed.

## Test Plan

Focused tests:

```powershell
pytest tests/test_chat_intent.py tests/test_chat_flow.py tests/test_orchestrator.py -q
```

Broader regression:

```powershell
pytest -q
```

Manual Streamlit smoke:

1. Start the app.
2. Save a profile.
3. Ask `내 사주를 풀이해줘.`
4. Ask `토가 강하고 금의 기운이 적다는 것은 어떤 성격의 사람이라는 의미야?`
5. Confirm the answer continues from the prior saju result and does not show the menu clarification prompt.
6. Ask `오늘 운세 알려줘`.
7. Confirm it switches to today's fortune.
8. Ask a blocked topic and confirm safety redirect still wins.

## Risks And Guardrails

- Too-broad follow-up fallback may answer casual unrelated messages as if they were saju questions. This is acceptable after a prior answer, but tests should keep no-context messages as `clarify`.
- Reordering intent and follow-up handling can accidentally prevent same-intent elaboration. Cover this with the Korean contextual test.
- Safety routing must remain first to avoid high-stakes answers being smuggled through as follow-ups.
- The deterministic fallback may still be less conversational than the LLM path. Do not weaken safety or invent facts to make fallback sound smarter.

## Definition Of Done

- Regression tests fail before the router change and pass after it.
- Existing safety and explicit menu routing tests still pass.
- No dependencies are added.
- No tool JSON contracts are changed.
- `HARNESS_PLAN.md` points to this plan while work is active.

