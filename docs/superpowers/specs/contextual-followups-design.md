# Spec: Contextual Follow-Up Conversation Flow

## Problem

The chat UI presents itself as a continuous chatbot, but follow-up routing still behaves like a narrow menu classifier. After a valid saju answer, a user can ask a natural follow-up such as:

> 토가 강하고 금의 기운이 적다는 것은 어떤 성격의 사람이라는 의미야?

The current router returns `clarify`, so the UI responds with the menu prompt instead of continuing the conversation.

## Current Evidence

- `src/chat_intent.py:34` only routes a follow-up when `_looks_like_follow_up()` matches and `last_intent` exists.
- `src/chat_intent.py:81` recognizes a small token set: `why`, `reason`, `explain`, `more`, `왜`, `이유`, `근거`, `자세`, `그렇게`, `??`.
- The example question contains contextual Korean phrases such as `어떤 성격` and `의미야`, but no current follow-up token.
- Reproduction:
  - `route_intent("토가 강하고 ... 의미야?", ConversationState(last_intent="saju_reading", last_tool_results={...}))` returns `RoutedIntent(kind="clarify")`.
  - `Orchestrator.handle_message()` then returns `reply_kind="clarify"` with no `llm_package`.
- `app.py:257` renders `ui_copy.CLARIFY_MESSAGE` when no package is produced.

## Desired Behavior

Once a profile exists and the bot has a previous answer context, ordinary user messages should continue the conversation by default. The app should only show the menu clarification prompt when there is no usable conversation context.

The routing priority should be:

1. Block unsafe topics first.
2. If the user clearly asks for a different supported menu, route to that new intent.
3. If the user asks a contextual question about the current answer, reuse `last_intent` and `last_tool_results`.
4. If the message is ambiguous but prior context exists, treat it as a follow-up rather than a menu clarification.
5. If no profile or prior answer context exists, keep the current profile collection or clarification behavior.

## Scope

In scope:

- Make follow-up routing context-first after an answer exists.
- Preserve deterministic tool ownership: LLM interprets only existing tool JSON and must not calculate saju directly.
- Preserve high-stakes safety redirects.
- Preserve explicit menu changes such as "오늘 운세 알려줘" after a saju reading.
- Add regression tests for Korean contextual follow-up phrasing.

Out of scope:

- Adding dependencies.
- Replacing the deterministic router with an LLM router.
- Changing tool JSON contracts.
- Redesigning Streamlit UI layout.
- Changing model/provider configuration.

## Acceptance Criteria

- After a saju reading, the example question about strong earth and weak metal routes as `follow_up`.
- The follow-up package reuses the previous `saju_reading` tool results and does not rerun tools.
- Explicit new menu requests still route to the requested menu.
- Blocked topics still return `blocked` before any follow-up fallback.
- When no previous answer exists, unrelated messages still return `clarify` or profile collection.
- Existing tests continue to pass.

