# Architecture

## Overview

KDA Chatbot is a Streamlit-first saju self-reflection chatbot. It is now organized around a conversation loop rather than a central form/menu report generator.

The core boundary is:

- deterministic tools calculate structured JSON
- orchestrator routes user intent and chooses which tools to run
- prompt layer turns tool JSON into LLM or fallback answer packages
- Streamlit renders chat state and profile onboarding

The LLM never calculates saju directly.

## Runtime Flow

```text
Sidebar profile form
  -> Orchestrator.build_profile()
  -> calculate_saju_chart tool
  -> analyze_five_elements tool
  -> profile stored in Streamlit session + ConversationState

Chat message or quick action
  -> Orchestrator.handle_message()
  -> route_intent()
  -> answer(intent, profile) for normal intents
  -> prompts.build_llm_package()
  -> prompts.generate_answer()
  -> LLM answer or deterministic fallback
  -> Streamlit chat history update
```

Follow-up messages reuse `ConversationState.last_intent` and `ConversationState.last_tool_results` so the app can answer "why?" without recalculating the profile.

## Main Modules

### `app.py`

Streamlit entrypoint. Responsibilities:

- set page config
- initialize session state
- render sidebar profile onboarding
- render profile summary and debug panel
- render chat history with `st.chat_message`
- render quick actions and `st.chat_input`
- call the orchestrator only from explicit user actions

The app avoids tool calls during pure render paths to reduce Streamlit rerun bugs.

### `src/conversation.py`

Pure conversation-state domain module. Responsibilities:

- `ConversationState`
- dict serialization/deserialization for Streamlit session state
- bounded message history
- simple profile slot extraction and merge helpers
- missing slot detection

This module has no Streamlit or LLM dependency.

### `src/chat_intent.py`

Deterministic keyword-first router. Responsibilities:

- route natural language to supported intents
- detect follow-up questions
- detect blocked/high-stakes topics before tool execution
- return clarification when confidence is too low

Supported intents map to the existing menu contract:

- `saju_reading`
- `today_fortune`
- `luck_score`
- `lucky_color`
- `lucky_item`
- `love`
- `wealth`
- `life_flow`

### `src/orchestrator.py`

Application coordinator. Responsibilities:

- load tool registry
- build the profile once from user data
- preserve existing `answer(intent, profile, follow_up=None)` behavior
- expose `handle_message(message, state=None)` for chat turns
- run only tools required for the routed intent
- store `last_intent`, `last_tool_results`, and pending tools in state
- gracefully degrade when optional teammate tools fail or are missing

`handle_message()` is layered on top of the existing menu-style `answer()` contract, so older tests and callers remain compatible.

### `src/prompts.py`

Prompt and answer layer. Responsibilities:

- central safety policy
- `build_llm_package()` with profile, tool results, user message, recent history, and last intent
- `build_user_prompt()` that states tool JSON is the only calculation source
- `generate_answer()` with provider selection and API-key-free fallback
- deterministic `fallback_answer()` with menu-specific sections

Fallback answers are intentionally structured and safety-filtered so the app remains useful without an LLM API key.

### `src/ui/*`

Design-ready UI helpers:

- `copy.py`: labels, quick-action text, warnings, safety redirects
- `state.py`: Streamlit session-state keys and safe mutations
- `view_models.py`: profile/tool display shaping

These files prepare for future visual redesign without introducing React or FastAPI.

## Tool Layer

All tools keep the shared JSON contract:

```json
{"ok": true, "data": {}}
```

or:

```json
{"ok": false, "error": {"code": "ERROR_CODE", "message": "Readable message"}}
```

Tools:

- `calculate_saju_chart`: Python LangChain tool calling `scripts/calculate_saju.mjs`
- `analyze_five_elements`: element counting and recommendation
- `calculate_today_luck`: deterministic today score/signals/cautions
- `recommend_lucky_factors`: lucky colors/items from recommended element

## State Model

Streamlit session stores:

- `messages`
- `profile`
- `conversation_state`
- `last_intent`
- `last_tool_results`
- debug visibility

`ConversationState` stores:

- profile
- user slots
- message history
- last intent
- last tool results
- pending slots
- pending tools
- bounded history limit

Profile calculation is not repeated on every chat turn. Once profile exists, normal questions reuse it.

## Safety Model

The app must not make deterministic claims about:

- health or disease
- lifespan
- accidents
- investment returns
- admissions or pass/fail outcomes
- lottery, gambling, or betting
- medical, legal, or financial decisions

Blocked topics are detected before calculation tools run. The assistant redirects to safer self-reflection copy.

## Verification Surface

Current regression coverage includes:

- tool contract tests
- orchestrator/menu compatibility tests
- conversation state and intent routing tests
- prompt/fallback safety tests
- Streamlit chat UI tests through `streamlit.testing.v1.AppTest`

Required final commands:

```powershell
pytest --collect-only -q
pytest -q
echo '{"birth_date":"1998-03-12","birth_time":"09:00","calendar_type":"solar"}' | node scripts/calculate_saju.mjs
streamlit run app.py
```

